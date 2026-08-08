"""Visualizaciones estáticas del panel (PNG vía Plotly + Kaleido).

Complemento visual al panel de Gold -- ningún dato nuevo se calcula aquí, solo se muestra lo
que ya existe en ``data/gold/panel_opa.duckdb``. Misma ética que el resto del pipeline: los
huecos y las degradaciones de cobertura se muestran, nunca se interpolan ni se esconden, y los
números que aparecen en anotaciones se calculan desde los datos, no se escriben a mano.

Tres capas por figura:

- ``_leer_*``: una query contra el duckdb real, regresa un DataFrame.
- ``construir_*``: función PURA ``DataFrame -> go.Figure`` -- sin I/O, es lo que testean los
  tests sin necesitar kaleido ni un duckdb real.
- ``exportar()``: orquesta ambas, valida insumos y escribe PNG + ``GALERIA.md``.

Regla de cobertura, verificada contra datos reales (2026-08-08): un corte "vivo" en
``dim_snapshot``/``int_snapshot_canonico`` no significa que tenga filas en
``fct_ppi_observacion`` -- los 3 snapshots de 2024 T1 están declarados en el manifiesto
(aparecen en ``int_snapshot_canonico``) pero ``dim_snapshot.estado='excluido_de_silver'`` los
marca como corruptos y ``fct_ppi_observacion`` tiene 0 filas para ese trimestre. Por eso la
matriz de cobertura cruza ambas tablas en vez de confiar en una sola.
"""

from __future__ import annotations

import textwrap
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd
import plotly.graph_objects as go

ANCHO_PX = 1200
ALTO_PX = 675
ESCALA = 2

_TABLAS_REQUERIDAS = (
    "dim_snapshot",
    "int_snapshot_canonico",
    "fct_ppi_observacion",
    "fct_ppi_ciclo_vida",
    "dim_ramo",
)

# Codificación visual compartida por TODAS las figuras que muestran huecos de cobertura --
# nunca redefinir estos colores/etiquetas por separado en una figura individual. Paleta
# tomada de la skill dataviz de este entorno (categórico slot 1/3 + status warning/critical,
# validados con scripts/validate_palette.js); COLOR_HUECO es gris de baja croma a propósito
# (lee como "vacío", mismo principio que el paso más claro de una rampa secuencial) -- el
# validador marca ese swatch como FAIL de croma/luminosidad por diseño, mitigado con las
# etiquetas de texto visibles que trae cada figura (regla de "relief" de la propia skill).
COLOR_DATO = "#2a78d6"  # categórico slot 1 (azul) -- corte vivo
COLOR_WAYBACK = "#1baf7a"  # categórico slot 3 (aqua) -- corte solo vía Wayback
COLOR_PARCIAL = "#fab219"  # status warning
COLOR_CORRUPTO = "#d03b3b"  # status critical
COLOR_HUECO = "#e8e7e3"  # neutro, cerca de la superficie -- "sin dato"


class ErrorFiguras(RuntimeError):
    """Falta una tabla requerida, una query no regresó filas, o Kaleido no puede exportar PNG."""


@dataclass(frozen=True)
class Figura:
    clave: str
    titulo: str
    interpretacion: str
    caveat: str
    leer: Callable[[duckdb.DuckDBPyConnection], object]
    construir: Callable[..., go.Figure]


def _verificar_tablas(con: duckdb.DuckDBPyConnection) -> None:
    existentes = {fila[0] for fila in con.execute("show tables").fetchall()}
    faltantes = sorted(set(_TABLAS_REQUERIDAS) - existentes)
    if faltantes:
        raise ErrorFiguras(
            f"Faltan {len(faltantes)} tabla(s) requerida(s) para generar figuras: "
            f"{', '.join(faltantes)}"
        )


def _verificar_kaleido() -> None:
    try:
        go.Figure().to_image(format="png")
    except Exception as exc:  # noqa: BLE001 -- cualquier fallo de Kaleido es el mismo problema
        raise ErrorFiguras(
            "Kaleido no pudo exportar un PNG de prueba -- probablemente falta Chrome. "
            "Corre: uv run plotly_get_chrome"
        ) from exc


def _forzar_anio_trimestre_int(df: pd.DataFrame) -> pd.DataFrame:
    """anio_corte/trimestre_corte llegan como DOUBLE de DuckDB (columnas nullable) -- sin este
    cast, un merge contra la rejilla entera produce columnas float y las etiquetas "2016T1"
    salen "2016.0T1.0", rompiendo cualquier ordenamiento/parseo posterior."""
    df = df.copy()
    df["anio"] = df["anio"].astype("Int64").astype(int)
    df["trimestre"] = df["trimestre"].astype("Int64").astype(int)
    return df


def _ajustar(texto: str, ancho: int = 95) -> str:
    """Inserta <br> cada ~ancho caracteres -- Plotly NO envuelve texto de título/anotación
    solo, así que un subtítulo largo se corta al ancho de la figura sin esto (visto en la
    primera corrida real: 3 de 6 figuras cortaban su texto explicativo a la mitad)."""
    return "<br>".join(textwrap.wrap(texto, width=ancho, break_long_words=False))


def _grid_trimestral(anio_min: int, anio_max: int) -> pd.DataFrame:
    """Rejilla completa año×trimestre entre anio_min y anio_max, ambos inclusive."""
    filas = [
        {"anio": anio, "trimestre": trimestre}
        for anio in range(anio_min, anio_max + 1)
        for trimestre in (1, 2, 3, 4)
    ]
    return pd.DataFrame(filas)


def _leer_cobertura(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    # OJO (hallazgo real, verificado 2026-08-08): int_snapshot_canonico.sql elige UN
    # snapshot_id "canónico" por (anio, trimestre) con row_number() ordenado por prioridad de
    # producto -- pero cuando dos snapshots empatan en prioridad (ej. 2016 T3 tiene dos
    # archivos con producto='otro', uno vivo y uno solo-Wayback, mismo contenido real), el
    # desempate no es determinista: qué snapshot_id gana cambia entre corridas de dbt (visto
    # directamente: 4 corridas seguidas de la misma query dieron 'ccbf1d23' 3 veces y
    # 'b33e65ed' una vez). Reportado aparte para corregir en el modelo dbt -- aquí NO se
    # confía en el ganador del empate: origen/estado se agregan sobre TODOS los snapshots
    # declarados de ese corte (stg_snapshots), no solo el elegido por int_snapshot_canonico.
    declarados = con.execute(
        "select s.anio as anio, s.trimestre as trimestre, "
        "bool_or(s.origen = 'vivo') as tiene_vivo, "
        "bool_or(s.origen = 'wayback') as tiene_wayback, "
        "bool_or(coalesce(ds.estado, '') = 'excluido_de_silver') as tiene_corrupto "
        "from stg_snapshots s "
        "left join dim_snapshot ds on ds.snapshot_id = s.snapshot_id "
        "where s.trimestre is not null "
        "group by 1, 2"
    ).df()
    parcial = con.execute(
        "select anio, trimestre, cobertura_parcial_del_universo from int_snapshot_canonico"
    ).df()
    # OJO (hallazgo real, verificado 2026-08-08): fct_ppi_observacion.anio_corte/
    # trimestre_corte vienen NULL para cortes completos (ej. 2020 T1/T2, 494 y 493 filas)
    # aunque el corte sí tiene datos -- son columnas por FILA, heredadas del ANIO/CICLO crudo
    # de la fuente, que no siempre viene poblado (ver contracts.py: ~20% nulo incluso en el
    # esquema moderno). int_ppi_observaciones_canonicas.anio/trimestre viene del snapshot
    # (int_snapshot_canonico), no de la fila -- completo para los 34 cortes canónicos.
    con_datos = con.execute(
        "select distinct anio, trimestre from int_ppi_observaciones_canonicas"
    ).df()
    con_datos = _forzar_anio_trimestre_int(con_datos)
    declarados = _forzar_anio_trimestre_int(declarados)
    parcial = _forzar_anio_trimestre_int(parcial)

    declarados = declarados.merge(parcial, on=["anio", "trimestre"], how="left")
    anio_min = int(declarados["anio"].min())
    anio_max = int(declarados["anio"].max())
    grid = _grid_trimestral(anio_min, anio_max)

    grid = grid.merge(declarados, on=["anio", "trimestre"], how="left")
    con_datos = con_datos.assign(tiene_datos=True)
    grid = grid.merge(con_datos, on=["anio", "trimestre"], how="left")
    # bool(NaN) es True en Python -- sin este fillna, un corte sin NINGÚN snapshot declarado
    # (hueco real) quedaría con tiene_corrupto=NaN tras el merge y _clasificar lo marcaría
    # como "corrupto" en vez de "hueco" (bug real, encontrado al inspeccionar la primera
    # corrida: infló "corrupto" a 11 cortes y dejó "hueco" en 0).
    for columna in ("tiene_datos", "tiene_vivo", "tiene_wayback", "tiene_corrupto"):
        grid[columna] = grid[columna].fillna(False)

    def _clasificar(fila: pd.Series) -> str:
        # "vivo"/"wayback" (de dónde vino el archivo) y "parcial" (si el universo de ese
        # corte es completo o no) son dimensiones DISTINTAS -- un corte puede ser vivo Y
        # parcial a la vez (de hecho la mayoría de 2016-2020 lo es). Colapsarlas en una sola
        # categoría (como en el primer intento) esconde que Wayback fue necesario para esos
        # cortes -- uno de los hallazgos centrales del proyecto. "parcial" se marca aparte
        # (ver construir_cobertura), no como color base.
        if fila["tiene_datos"]:
            return "vivo" if bool(fila.get("tiene_vivo")) else "wayback"
        if bool(fila.get("tiene_corrupto")):
            return "corrupto"
        return "hueco"

    grid["categoria"] = grid.apply(_clasificar, axis=1)
    grid["parcial"] = grid["tiene_datos"] & grid["cobertura_parcial_del_universo"].fillna(False)
    # La rejilla llega hasta el año más alto que discovery llegó a PROBAR (incluye
    # trimestres futuros que ni siquiera han sido publicados todavía) -- eso no es un "hueco
    # agotado por 4 vías" en el sentido del resto del repo, es simplemente que el tiempo no
    # ha llegado. Se relabeled a "futuro" (no se elimina la fila: el heatmap necesita una
    # rejilla rectangular completa, año x 4 trimestres).
    ultimo_real = int((con_datos["anio"] * 10 + con_datos["trimestre"]).max())
    es_futuro = grid["anio"] * 10 + grid["trimestre"] > ultimo_real
    grid.loc[es_futuro, "categoria"] = "futuro"
    grid.loc[es_futuro, "parcial"] = False
    return grid[["anio", "trimestre", "categoria", "parcial"]]


def construir_cobertura(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        raise ErrorFiguras("La matriz de cobertura no tiene datos que graficar.")

    orden_categorias = ["vivo", "wayback", "corrupto", "hueco", "futuro"]
    colores = {
        "vivo": COLOR_DATO,
        "wayback": COLOR_WAYBACK,
        "corrupto": COLOR_CORRUPTO,
        "hueco": COLOR_HUECO,
        "futuro": "#ffffff",  # sin marca visual -- no es un hueco metodológico, solo aún no llega
    }
    # Códigos cortos visibles en cada celda -- regla de "relief" de la skill dataviz: un
    # swatch de contraste bajo (hueco) no puede depender solo del color para leerse. "parcial"
    # ya no es una categoría de color (ver _leer_cobertura): se marca con un asterisco sobre
    # vivo/wayback, porque son dimensiones independientes.
    codigo_visible = {"vivo": "V", "wayback": "W", "corrupto": "X", "hueco": "", "futuro": ""}
    codigo = {cat: i for i, cat in enumerate(orden_categorias)}

    anios = sorted(df["anio"].unique())
    trimestres = [1, 2, 3, 4]

    def _celda(anio: int, t: int) -> pd.Series:
        return df[(df.anio == anio) & (df.trimestre == t)].iloc[0]

    z = [[codigo[_celda(anio, t)["categoria"]] for anio in anios] for t in trimestres]
    categorias_celda = [[_celda(anio, t)["categoria"] for anio in anios] for t in trimestres]
    texto_visible = [
        [codigo_visible[_celda(anio, t)["categoria"]] + ("*" if _celda(anio, t)["parcial"] else "") for anio in anios]
        for t in trimestres
    ]

    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=[str(a) for a in anios],
            y=[f"T{t}" for t in trimestres],
            text=texto_visible,
            texttemplate="%{text}",
            customdata=categorias_celda,
            textfont=dict(size=12, color="#0b0b0b"),
            colorscale=[[i / (len(orden_categorias) - 1), colores[c]] for i, c in enumerate(orden_categorias)],
            zmin=0,
            zmax=len(orden_categorias) - 1,
            showscale=False,
            xgap=2,
            ygap=2,
            hovertemplate="Año %{x}, %{y}: %{customdata}<extra></extra>",
        )
    )

    n_corruptos = int((df["categoria"] == "corrupto").sum())
    n_huecos = int((df["categoria"] == "hueco").sum())
    n_wayback = int((df["categoria"] == "wayback").sum())
    n_parciales = int(df["parcial"].sum())
    for cat in [c for c in orden_categorias if c != "futuro"]:
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(size=10, color=colores[cat]),
                name=cat,
                showlegend=True,
            )
        )
    fig.add_trace(
        go.Scatter(
            x=[None],
            y=[None],
            mode="markers",
            marker=dict(size=10, color="white", line=dict(color="#0b0b0b", width=1), symbol="asterisk"),
            name="* = cobertura parcial",
            showlegend=True,
        )
    )

    anio_min, anio_max = int(df["anio"].min()), int(df["anio"].max())
    subtitulo = (
        f"{n_huecos} trimestre(s) sin ninguna fuente conocida · "
        f"{n_corruptos} corte(s) corrupto(s) en la fuente misma · "
        f"{n_wayback} solo recuperable(s) vía Wayback Machine · "
        f"{n_parciales} con cobertura parcial del universo"
    )
    nota = (
        "'corrupto' = declarado por la fuente pero rechazado en Silver (2024 T1: el servidor "
        "sirve un binario truncado). 'hueco' = ninguna fuente conocida lo tiene, agotadas 4 "
        "vías de descubrimiento (celdas en blanco son trimestres futuros, aún no publicados "
        "por la fuente -- no cuentan como hueco). '*' = el producto disponible ese corte no es "
        "el universo completo (Consolidado), sino Seguimiento o Concluido."
    )
    fig.update_layout(
        title=(
            f"Cobertura del panel por corte trimestral, {anio_min}-{anio_max}<br>"
            f"<sup>{_ajustar(subtitulo, 110)}</sup>"
        ),
        width=ANCHO_PX,
        height=ALTO_PX,
        annotations=[
            dict(
                text=_ajustar(nota, 130),
                xref="paper",
                yref="paper",
                x=0,
                y=-0.28,
                showarrow=False,
                font=dict(size=11),
                align="left",
            )
        ],
        margin=dict(b=140),
    )
    return fig


def _leer_universo_por_corte(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    # Fuente: int_ppi_observaciones_canonicas, no fct_ppi_observacion -- ver la nota en
    # _leer_cobertura sobre por qué anio_corte/trimestre_corte por fila no sirven aquí.
    datos = con.execute(
        "select anio, trimestre, count(distinct cve_cartera) as n_ppi "
        "from int_ppi_observaciones_canonicas group by 1, 2"
    ).df()
    datos = _forzar_anio_trimestre_int(datos)
    cobertura = _leer_cobertura(con)
    anio_min, anio_max = int(cobertura["anio"].min()), int(cobertura["anio"].max())
    grid = _grid_trimestral(anio_min, anio_max)
    grid = grid.merge(datos, on=["anio", "trimestre"], how="left")
    grid = grid.merge(cobertura, on=["anio", "trimestre"], how="left")
    grid = grid.sort_values(["anio", "trimestre"]).reset_index(drop=True)
    grid["etiqueta"] = grid["anio"].astype(str) + "T" + grid["trimestre"].astype(str)
    return grid


def construir_universo_por_corte(df: pd.DataFrame) -> go.Figure:
    if df.empty or df["n_ppi"].notna().sum() == 0:
        raise ErrorFiguras("La serie de universo por corte no tiene ningún valor no nulo.")

    caidas_q1 = df[(df["trimestre"] == 1) & df["n_ppi"].notna()].copy()
    caidas_q1["anterior"] = caidas_q1["anio"].map(
        lambda a: df[(df["anio"] == a - 1) & (df["trimestre"] == 4)]["n_ppi"].iloc[0]
        if not df[(df["anio"] == a - 1) & (df["trimestre"] == 4)].empty
        else None
    )
    caidas_validas = caidas_q1.dropna(subset=["anterior"])
    caidas_validas = caidas_validas[caidas_validas["anterior"] > 0]
    if not caidas_validas.empty:
        pct = (caidas_validas["n_ppi"] - caidas_validas["anterior"]) / caidas_validas["anterior"] * 100
        rango_txt = f"{pct.min():.0f}% a {pct.max():.0f}%"
    else:
        rango_txt = "sin datos suficientes"

    # add_vrect con x0==x1 sobre un eje de categorías no pinta nada visible (ancho cero) --
    # se usa la posición ENTERA de cada corte como eje real y las etiquetas "2016T1" se
    # ponen como ticks manuales, así x0=i-0.5/x1=i+0.5 sí produce una franja de una celda.
    df = df.reset_index(drop=True)
    posiciones = list(range(len(df)))

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=posiciones,
            y=df["n_ppi"],
            mode="lines+markers",
            line=dict(color=COLOR_DATO),
            connectgaps=False,
            name="PPI únicos observados",
        )
    )

    for i, fila in df[df["categoria"].isin(["hueco", "corrupto"])].iterrows():
        color = {"hueco": COLOR_HUECO, "corrupto": COLOR_CORRUPTO}[fila["categoria"]]
        fig.add_vrect(x0=i - 0.5, x1=i + 0.5, fillcolor=color, opacity=0.35, line_width=0)
    for i, _fila in df[df["parcial"].fillna(False)].iterrows():
        fig.add_vrect(x0=i - 0.5, x1=i + 0.5, fillcolor=COLOR_PARCIAL, opacity=0.25, line_width=0)

    subtitulo = (
        f"Patrón estacional Q4→Q1: el universo cae {rango_txt} cada primer trimestre "
        "(re-registro presupuestal, no error de carga)"
    )
    nota = (
        "Franjas: gris = hueco real · rojo = corrupto en la fuente · ámbar = cobertura "
        "parcial (no es el universo Consolidado completo). Los huecos nunca se interpolan: "
        "la línea se corta."
    )
    fig.update_layout(
        title=f"Universo de PPI por corte trimestral<br><sup>{_ajustar(subtitulo, 110)}</sup>",
        xaxis_title="Corte",
        yaxis_title="PPI únicos",
        width=ANCHO_PX,
        height=ALTO_PX,
        showlegend=False,
        # El gris de fondo por defecto de Plotly (#e5ecf6) casi se traga COLOR_HUECO (un
        # gris similar) -- blanco puro para que la franja de "hueco" sea visible de verdad.
        plot_bgcolor="white",
        xaxis=dict(
            tickangle=-60,
            tickfont=dict(size=9),
            tickmode="array",
            tickvals=posiciones,
            ticktext=df["etiqueta"].tolist(),
            gridcolor="#eeeeee",
        ),
        yaxis=dict(gridcolor="#eeeeee"),
        annotations=[
            dict(
                text=_ajustar(nota, 130),
                xref="paper",
                yref="paper",
                x=0,
                y=-0.28,
                showarrow=False,
                font=dict(size=11),
                align="left",
            )
        ],
        margin=dict(b=140),
    )
    return fig


def _leer_inversion_por_ramo(con: duckdb.DuckDBPyConnection, top_n: int = 7) -> pd.DataFrame:
    # Misma fuente que _leer_universo_por_corte y por la misma razón: anio_corte/
    # trimestre_corte por fila de fct_ppi_observacion no cubren todos los cortes reales.
    top_ramos = con.execute(
        "select descripcion_ramo, sum(modificado) as total "
        "from int_ppi_observaciones_canonicas where descripcion_ramo is not null "
        "group by 1 order by 2 desc limit ?",
        [top_n],
    ).df()["descripcion_ramo"].tolist()

    datos = con.execute(
        "select anio, trimestre, descripcion_ramo, sum(modificado) as monto "
        "from int_ppi_observaciones_canonicas where descripcion_ramo is not null "
        "group by 1, 2, 3"
    ).df()
    datos = _forzar_anio_trimestre_int(datos)
    datos["serie"] = datos["descripcion_ramo"].where(datos["descripcion_ramo"].isin(top_ramos), "Resto de ramos")
    datos = datos.groupby(["anio", "trimestre", "serie"], as_index=False)["monto"].sum()
    datos["etiqueta"] = datos["anio"].astype(str) + "T" + datos["trimestre"].astype(str)
    return datos


def construir_inversion_por_ramo(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        raise ErrorFiguras("La serie de inversión por ramo no tiene filas.")

    orden_etiquetas = sorted(df["etiqueta"].unique(), key=lambda e: (int(e.split("T")[0]), int(e.split("T")[1])))
    series = sorted(df["serie"].unique(), key=lambda s: (s == "Resto de ramos", s))

    fig = go.Figure()
    for serie in series:
        sub = df[df["serie"] == serie].set_index("etiqueta").reindex(orden_etiquetas)
        fig.add_trace(
            go.Scatter(
                x=orden_etiquetas,
                y=sub["monto"],
                mode="lines",
                name=serie,
                connectgaps=False,
            )
        )

    subtitulo = (
        "Pesos corrientes, sin deflactar. Huecos de cobertura del panel dejan espacios "
        "sin conectar en las líneas."
    )
    fig.update_layout(
        title=(
            f"Presupuesto modificado por ramo, top {len(series) - 1} ramos<br>"
            f"<sup>{_ajustar(subtitulo, 110)}</sup>"
        ),
        xaxis_title="Corte",
        yaxis_title="Monto modificado (pesos corrientes)",
        width=ANCHO_PX,
        height=ALTO_PX,
        xaxis=dict(tickangle=-60, tickfont=dict(size=9)),
        legend=dict(font=dict(size=10)),
    )
    return fig


def _leer_mapa(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    total = con.execute("select count(distinct cve_cartera) as n from fct_ppi_observacion").fetchone()[0]
    df = con.execute(
        "with ultima as ("
        "  select cve_cartera, latitud, longitud, monto_total_inversion, descripcion_ramo, "
        "         row_number() over (partition by cve_cartera order by snapshot_id desc) as rn "
        "  from fct_ppi_observacion where latitud is not null and longitud is not null"
        ") "
        "select cve_cartera, latitud, longitud, monto_total_inversion, descripcion_ramo "
        "from ultima where rn = 1"
    ).df()
    df.attrs["total_universo"] = int(total)
    return df


def construir_mapa(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        raise ErrorFiguras("No hay PPI con coordenadas válidas para el mapa.")

    total = df.attrs.get("total_universo", len(df))
    pct = len(df) / total * 100 if total else 0.0
    montos = df["monto_total_inversion"].clip(lower=1).fillna(1)

    fig = go.Figure(
        go.Scattergeo(
            lon=df["longitud"],
            lat=df["latitud"],
            mode="markers",
            marker=dict(
                size=(montos.pow(1 / 3)) / (montos.pow(1 / 3).max()) * 28 + 3,
                color=COLOR_DATO,
                opacity=0.45,
                line=dict(width=0),
            ),
            text=df["descripcion_ramo"],
            hovertemplate="%{text}<extra></extra>",
        )
    )
    fig.update_geos(
        scope="north america",
        lonaxis_range=[-120, -85],
        lataxis_range=[13, 34],
        showland=True,
        landcolor="#f2f2f2",
        showcountries=True,
        countrycolor="#bbbbbb",
    )
    titulo = f"Proyectos de inversión georreferenciados ({len(df):,} de {total:,}, {pct:.1f}% del universo)"
    subtitulo = "Tamaño del punto ~ monto total de inversión (escala no lineal); pesos corrientes, sin deflactar."
    fig.update_layout(
        title=f"{_ajustar(titulo, 100)}<br><sup>{_ajustar(subtitulo, 110)}</sup>",
        width=ANCHO_PX,
        height=ALTO_PX,
    )
    return fig


def _leer_estatus_terminal(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return con.execute(
        "select estatus_terminal_inferido, count(*) as n from fct_ppi_ciclo_vida group by 1 order by 2 desc"
    ).df()


def construir_estatus_terminal(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        raise ErrorFiguras("No hay filas de estatus terminal que graficar.")

    total = int(df["n"].sum())
    colores = {
        "salida_no_explicada": "#b0a8d8",
        "terminado_probable": "#2c9e6b",
        "vigente_ultimo_corte_disponible": COLOR_DATO,
    }
    n_no_explicada = int(df.loc[df["estatus_terminal_inferido"] == "salida_no_explicada", "n"].sum())

    fig = go.Figure(
        go.Bar(
            x=df["estatus_terminal_inferido"],
            y=df["n"],
            marker_color=[colores.get(c, "#999999") for c in df["estatus_terminal_inferido"]],
            text=df["n"],
            texttemplate="%{text:,}",
        )
    )
    subtitulo = (
        f"'salida_no_explicada' ({n_no_explicada:,}) es INFERENCIA, no dato oficial: incluye "
        "proyectos que caen en un trimestre-hueco del panel, no solo cancelaciones reales -- "
        "los datos abiertos no permiten distinguir ambos casos."
    )
    fig.update_layout(
        title=f"Estatus terminal inferido, {total:,} proyectos<br><sup>{_ajustar(subtitulo, 110)}</sup>",
        xaxis_title="Estatus terminal inferido",
        yaxis_title="Proyectos",
        width=ANCHO_PX,
        height=ALTO_PX,
        showlegend=False,
    )
    return fig


def _leer_sobrecosto(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return con.execute(
        "select sobrecosto_pct from fct_ppi_ciclo_vida where sobrecosto_pct is not null"
    ).df()


def construir_sobrecosto(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        raise ErrorFiguras("No hay valores de sobrecosto_pct que graficar.")

    n_total = len(df)
    limite_inferior, limite_superior = -100.0, 300.0
    dentro = df[(df["sobrecosto_pct"] >= limite_inferior) & (df["sobrecosto_pct"] <= limite_superior)]
    n_fuera = n_total - len(dentro)

    fig = go.Figure(
        go.Histogram(
            x=dentro["sobrecosto_pct"],
            marker_color=COLOR_DATO,
            xbins=dict(start=limite_inferior, end=limite_superior, size=20),
        )
    )
    subtitulo = (
        "Pesos corrientes, sin deflactar -- sobreestima el sobrecosto real en proyectos "
        f"largos. Recortado a [{limite_inferior:.0f}%, {limite_superior:.0f}%]: {n_fuera:,} "
        "proyecto(s) fuera de ese rango no se muestran."
    )
    fig.update_layout(
        title=(
            f"Distribución de sobrecosto, {len(dentro):,} de {n_total:,} proyectos<br>"
            f"<sup>{_ajustar(subtitulo, 110)}</sup>"
        ),
        xaxis_title="Sobrecosto (%, monto final vs. inicial)",
        yaxis_title="Proyectos",
        width=ANCHO_PX,
        height=ALTO_PX,
        showlegend=False,
    )
    return fig


FIGURAS: tuple[Figura, ...] = (
    Figura(
        clave="cobertura_cortes",
        titulo="Cobertura del panel por corte trimestral",
        interpretacion=(
            "Cada celda es un trimestre desde el primer corte trimestral disponible hasta el "
            "más reciente. Azul son cortes con datos reales del servidor vivo (verde sería "
            "Wayback Machine, sin casos hoy -- ver NOTA-TECNICA.md); un asterisco marca "
            "cobertura parcial (no es el universo Consolidado completo); rojo son cortes que "
            "la fuente declara pero que llegan corruptos; gris son huecos reales, sin ninguna "
            "fuente conocida; celdas en blanco son trimestres aún no publicados."
        ),
        caveat=(
            "Esta figura es la credencial metodológica del proyecto: muestra exactamente qué "
            "tan completo es el panel, sin suavizar los huecos."
        ),
        leer=_leer_cobertura,
        construir=construir_cobertura,
    ),
    Figura(
        clave="universo_por_corte",
        titulo="Universo de PPI por corte",
        interpretacion=(
            "Conteo de proyectos únicos observados en cada corte trimestral. La caída "
            "recurrente cada enero-marzo es el patrón estacional Q4→Q1 (re-registro "
            "presupuestal de proyectos plurianuales), no un error de carga -- ver "
            "dbt/tests/assert_conteo_ppi_por_ramo_estable.sql para la investigación completa."
        ),
        caveat="Los huecos se muestran como franjas y como líneas cortadas, nunca interpolados.",
        leer=_leer_universo_por_corte,
        construir=construir_universo_por_corte,
    ),
    Figura(
        clave="inversion_por_ramo",
        titulo="Presupuesto modificado por ramo en el tiempo",
        interpretacion=(
            "Serie de presupuesto modificado (pesos corrientes) para los ramos con mayor "
            "inversión acumulada, con el resto de ramos agregado en una sola serie."
        ),
        caveat="Pesos corrientes -- la deflactación a precios constantes está pendiente (ver README).",
        leer=_leer_inversion_por_ramo,
        construir=construir_inversion_por_ramo,
    ),
    Figura(
        clave="mapa_ppi",
        titulo="Distribución geográfica de los proyectos",
        interpretacion=(
            "Última ubicación conocida de cada proyecto con coordenadas válidas. El tamaño "
            "del punto es proporcional (raíz cúbica, para que los megaproyectos no dominen "
            "visualmente) al monto total de inversión."
        ),
        caveat=(
            "Solo una fracción del universo trae coordenadas -- el porcentaje real aparece en "
            "el título de la figura, calculado contra el total, no estimado."
        ),
        leer=_leer_mapa,
        construir=construir_mapa,
    ),
    Figura(
        clave="estatus_terminal",
        titulo="Estatus terminal inferido de los proyectos",
        interpretacion=(
            "Clasificación de cada proyecto según su última observación: terminado probable "
            "(avance >= 95%), vigente en el último corte disponible, o salida no explicada."
        ),
        caveat=(
            "'salida_no_explicada' es una inferencia, no un dato oficial de la fuente: puede "
            "ser una cancelación real o un proyecto que cayó en un trimestre-hueco del panel."
        ),
        leer=_leer_estatus_terminal,
        construir=construir_estatus_terminal,
    ),
    Figura(
        clave="sobrecosto_distribucion",
        titulo="Distribución de sobrecosto por proyecto",
        interpretacion=(
            "Histograma de (monto final - monto inicial) / monto inicial, sobre los proyectos "
            "con monto inicial positivo."
        ),
        caveat=(
            "Pesos corrientes, sin deflactar -- parte del 'sobrecosto' en proyectos largos es "
            "inflación acumulada, no sobrecosto real. El rango mostrado se recorta y se declara "
            "cuántos proyectos quedan fuera."
        ),
        leer=_leer_sobrecosto,
        construir=construir_sobrecosto,
    ),
)


def _version_del_corte(con: duckdb.DuckDBPyConnection) -> str:
    fila = con.execute(
        "select anio, trimestre from dim_snapshot "
        "where trimestre is not null order by anio desc, trimestre desc limit 1"
    ).fetchone()
    if fila is None:
        return "sin_version"
    anio, trimestre = fila
    return f"{int(anio)}T{int(trimestre)}"


def generar_galeria(figuras: tuple[Figura, ...], version_corte: str) -> str:
    """Construye el texto de GALERIA.md. Función pura -- no toca disco."""
    lineas = [
        "# Galería de figuras",
        "",
        f"Generadas contra el corte más reciente del panel: **{version_corte}**. "
        "Regenerar con `uv run opa figuras`.",
        "",
        "Montos en pesos corrientes (sin deflactar) salvo que se indique lo contrario. "
        "Los PNG de Kaleido no son byte-idénticos entre versiones de Chrome -- solo "
        "re-commitear cuando cambian los datos o el diseño, no en cada corrida.",
        "",
    ]
    for fig in figuras:
        lineas.append(f"## {fig.titulo}")
        lineas.append("")
        lineas.append(f"![{fig.titulo}]({fig.clave}.png)")
        lineas.append("")
        lineas.append(fig.interpretacion)
        lineas.append("")
        lineas.append(f"**Nota metodológica:** {fig.caveat}")
        lineas.append("")
    return "\n".join(lineas)


def exportar(ruta_duckdb: Path, dir_salida: Path) -> list[Path]:
    """Genera todas las figuras registradas + GALERIA.md en dir_salida. Regresa las rutas escritas."""
    con = duckdb.connect(str(ruta_duckdb), read_only=True)
    try:
        _verificar_tablas(con)
        _verificar_kaleido()

        dir_salida.mkdir(parents=True, exist_ok=True)
        escritas: list[Path] = []

        for fig_def in FIGURAS:
            datos = fig_def.leer(con)
            if hasattr(datos, "empty") and datos.empty:
                raise ErrorFiguras(f"La figura '{fig_def.clave}' no tiene datos que graficar.")
            figura = fig_def.construir(datos)
            figura.update_layout(width=ANCHO_PX, height=ALTO_PX)
            ruta_png = dir_salida / f"{fig_def.clave}.png"
            figura.write_image(str(ruta_png), scale=ESCALA)
            escritas.append(ruta_png)

        version_corte = _version_del_corte(con)
    finally:
        con.close()

    ruta_galeria = dir_salida / "GALERIA.md"
    ruta_galeria.write_text(generar_galeria(FIGURAS, version_corte), encoding="utf-8")
    escritas.append(ruta_galeria)

    return escritas
