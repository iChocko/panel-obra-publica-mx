"""Tests del módulo de figuras (visualizaciones estáticas del panel).

Construye un duckdb mínimo en tmp_path con las tablas reales que consume figuras.py (no
depende del duckdb real del repo, que no existe en CI) -- mismo patrón que
tests/test_publish_geojson.py. Los tests de construcción (construir_*) son puros: no llaman
a Kaleido, no exportan PNG -- eso se prueba aparte, y se salta si no hay Chrome disponible.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import plotly.graph_objects as go
import pytest

from opa import figuras


def _crear_duckdb(ruta: Path) -> None:
    con = duckdb.connect(str(ruta))

    con.execute(
        "create table stg_snapshots (snapshot_id varchar, anio integer, trimestre integer, "
        "producto varchar, origen varchar)"
    )
    con.execute(
        """
        insert into stg_snapshots values
        ('2020Q1', 2020, 1, 'consolidado', 'vivo'),
        ('2020Q3', 2020, 3, 'consolidado', 'vivo'),
        ('2020Q4', 2020, 4, 'seguimiento', 'vivo'),
        ('2021Q1', 2021, 1, 'consolidado', 'vivo')
        """
    )
    # 2020 T2 NO tiene ningún renglón -- ese es el "hueco real" del fixture.

    con.execute(
        "create table dim_snapshot (snapshot_id varchar, anio integer, trimestre integer, estado varchar)"
    )
    con.execute(
        """
        insert into dim_snapshot values
        ('2020Q1', 2020, 1, 'normalizado'),
        ('2020Q3', 2020, 3, 'excluido_de_silver'),
        ('2020Q4', 2020, 4, 'normalizado'),
        ('2021Q1', 2021, 1, 'normalizado')
        """
    )
    # 2020Q3 tiene datos declarados pero quedó excluido de Silver -- "corrupto".

    con.execute(
        "create table int_snapshot_canonico (anio integer, trimestre integer, "
        "cobertura_parcial_del_universo boolean)"
    )
    con.execute(
        """
        insert into int_snapshot_canonico values
        (2020, 1, false),
        (2020, 4, true),
        (2021, 1, false)
        """
    )
    # 2020 T4 es "parcial" (producto seguimiento, no consolidado).

    con.execute(
        "create table int_ppi_observaciones_canonicas (anio integer, trimestre integer, "
        "cve_cartera varchar, descripcion_ramo varchar, modificado double)"
    )
    con.execute(
        """
        insert into int_ppi_observaciones_canonicas values
        (2020, 1, 'OPA001', 'Comunicaciones', 1000000.0),
        (2020, 1, 'OPA002', 'Salud', 2000000.0),
        (2020, 4, 'OPA001', 'Comunicaciones', 1000000.0),
        (2021, 1, 'OPA001', 'Comunicaciones', 500000.0),
        (2021, 1, 'OPA003', 'Educación', 300000.0)
        """
    )
    # 2020 T3 (corrupto) no aparece aquí -- 0 filas reales, consistente con "excluido_de_silver".

    con.execute(
        "create table fct_ppi_observacion (cve_cartera varchar, snapshot_id varchar, "
        "latitud double, longitud double, monto_total_inversion double, descripcion_ramo varchar)"
    )
    con.execute(
        """
        insert into fct_ppi_observacion values
        ('OPA001', '2021Q1', 19.4326, -99.1332, 1000.0, 'Comunicaciones'),
        ('OPA002', '2020Q1', 20.6597, -103.3496, 5176591194784.0, 'Salud'),
        ('OPA003', '2021Q1', NULL, NULL, 300000.0, 'Educación')
        """
    )
    # OPA003 sin coordenadas -- excluido del mapa. Montos con 6+ órdenes de magnitud (1e3 a 5e12).

    con.execute(
        "create table fct_ppi_ciclo_vida (cve_cartera varchar, "
        "estatus_terminal_inferido varchar, sobrecosto_pct double)"
    )
    con.execute(
        """
        insert into fct_ppi_ciclo_vida values
        ('OPA001', 'terminado_probable', 15.0),
        ('OPA002', 'salida_no_explicada', NULL),
        ('OPA003', 'vigente_ultimo_corte_disponible', -150.0)
        """
    )
    # -150.0 queda fuera del recorte [-100, 300] de construir_sobrecosto -- ejercita el conteo de excluidos.

    con.execute("create table dim_ramo (id_ramo integer, descripcion_ramo varchar)")
    con.execute("insert into dim_ramo values (9, 'Comunicaciones')")

    con.close()


def _duckdb_incompleto(ruta: Path) -> None:
    con = duckdb.connect(str(ruta))
    con.execute("create table dim_snapshot (snapshot_id varchar)")
    con.close()


# ---------------------------------------------------------------------------
# _leer_cobertura / construir_cobertura
# ---------------------------------------------------------------------------


def test_leer_cobertura_clasifica_hueco_corrupto_parcial_y_vivo(tmp_path: Path) -> None:
    db = tmp_path / "gold.duckdb"
    _crear_duckdb(db)
    con = duckdb.connect(str(db), read_only=True)
    try:
        df = figuras._leer_cobertura(con)
    finally:
        con.close()

    fila = lambda anio, t: df[(df.anio == anio) & (df.trimestre == t)].iloc[0]  # noqa: E731

    assert fila(2020, 1)["categoria"] == "vivo"
    assert not bool(fila(2020, 1)["parcial"])
    assert fila(2020, 2)["categoria"] == "hueco"
    assert fila(2020, 3)["categoria"] == "corrupto"
    assert fila(2020, 4)["categoria"] == "vivo"
    assert bool(fila(2020, 4)["parcial"])
    assert fila(2021, 1)["categoria"] == "vivo"


def test_leer_cobertura_es_deterministico_entre_llamadas(tmp_path: Path) -> None:
    db = tmp_path / "gold.duckdb"
    _crear_duckdb(db)
    con = duckdb.connect(str(db), read_only=True)
    try:
        resultados = [figuras._leer_cobertura(con)["categoria"].tolist() for _ in range(5)]
    finally:
        con.close()
    assert all(r == resultados[0] for r in resultados)


def test_construir_cobertura_regresa_figura_valida(tmp_path: Path) -> None:
    db = tmp_path / "gold.duckdb"
    _crear_duckdb(db)
    con = duckdb.connect(str(db), read_only=True)
    try:
        df = figuras._leer_cobertura(con)
    finally:
        con.close()

    fig = figuras.construir_cobertura(df)
    assert isinstance(fig, go.Figure)
    heatmap = fig.data[0]
    assert heatmap.type == "heatmap"
    # El texto visible de cada celda debe traer el código corto, no la categoría completa.
    textos_planos = [t for fila in heatmap.text for t in fila]
    assert "hueco" not in textos_planos  # texto visible es corto (V/W/X/""), no la etiqueta larga


def test_construir_cobertura_falla_con_dataframe_vacio() -> None:
    import pandas as pd

    with pytest.raises(figuras.ErrorFiguras, match="no tiene datos"):
        figuras.construir_cobertura(pd.DataFrame(columns=["anio", "trimestre", "categoria", "parcial"]))


# ---------------------------------------------------------------------------
# _leer_universo_por_corte / construir_universo_por_corte
# ---------------------------------------------------------------------------


def test_universo_por_corte_no_pierde_cortes_con_anio_corte_nulo(tmp_path: Path) -> None:
    """Ver figuras.py: la fuente correcta es int_ppi_observaciones_canonicas, no
    fct_ppi_observacion.anio_corte (que puede venir NULL para un corte completo)."""
    db = tmp_path / "gold.duckdb"
    _crear_duckdb(db)
    con = duckdb.connect(str(db), read_only=True)
    try:
        df = figuras._leer_universo_por_corte(con)
    finally:
        con.close()

    fila_2020t1 = df[(df.anio == 2020) & (df.trimestre == 1)].iloc[0]
    assert fila_2020t1["n_ppi"] == 2  # OPA001 + OPA002


def test_construir_universo_por_corte_marca_bandas_de_hueco_corrupto_parcial(tmp_path: Path) -> None:
    db = tmp_path / "gold.duckdb"
    _crear_duckdb(db)
    con = duckdb.connect(str(db), read_only=True)
    try:
        df = figuras._leer_universo_por_corte(con)
    finally:
        con.close()

    fig = figuras.construir_universo_por_corte(df)
    assert isinstance(fig, go.Figure)
    # 3 franjas esperadas: hueco (2020T2), corrupto (2020T3), parcial (2020T4).
    assert len(fig.layout.shapes) == 3
    # connectgaps=False -- la traza principal no debe conectar visualmente el hueco.
    assert fig.data[0].connectgaps is False


def test_construir_universo_por_corte_falla_si_todo_es_nulo() -> None:
    import pandas as pd

    df = pd.DataFrame(
        {
            "anio": [2020, 2020],
            "trimestre": [1, 2],
            "n_ppi": [None, None],
            "categoria": ["hueco", "hueco"],
            "parcial": [False, False],
            "etiqueta": ["2020T1", "2020T2"],
        }
    )
    with pytest.raises(figuras.ErrorFiguras):
        figuras.construir_universo_por_corte(df)


# ---------------------------------------------------------------------------
# inversión por ramo
# ---------------------------------------------------------------------------


def test_inversion_por_ramo_usa_fuente_canonica(tmp_path: Path) -> None:
    db = tmp_path / "gold.duckdb"
    _crear_duckdb(db)
    con = duckdb.connect(str(db), read_only=True)
    try:
        df = figuras._leer_inversion_por_ramo(con, top_n=2)
        fig = figuras.construir_inversion_por_ramo(df)
    finally:
        con.close()
    assert isinstance(fig, go.Figure)
    assert len(fig.data) >= 1


# ---------------------------------------------------------------------------
# mapa
# ---------------------------------------------------------------------------


def test_mapa_excluye_ppi_sin_coordenadas_y_calcula_porcentaje_real(tmp_path: Path) -> None:
    db = tmp_path / "gold.duckdb"
    _crear_duckdb(db)
    con = duckdb.connect(str(db), read_only=True)
    try:
        df = figuras._leer_mapa(con)
    finally:
        con.close()

    assert "OPA003" not in df["cve_cartera"].tolist()  # sin coordenadas
    assert df.attrs["total_universo"] == 3  # las 3 cve_cartera de fct_ppi_observacion

    fig = figuras.construir_mapa(df)
    assert isinstance(fig, go.Figure)
    assert "2 de 3" in fig.layout.title.text


def test_construir_mapa_falla_sin_coordenadas() -> None:
    import pandas as pd

    df = pd.DataFrame(columns=["cve_cartera", "latitud", "longitud", "monto_total_inversion", "descripcion_ramo"])
    df.attrs["total_universo"] = 0
    with pytest.raises(figuras.ErrorFiguras):
        figuras.construir_mapa(df)


# ---------------------------------------------------------------------------
# estatus terminal
# ---------------------------------------------------------------------------


def test_estatus_terminal_anota_advertencia_de_inferencia(tmp_path: Path) -> None:
    db = tmp_path / "gold.duckdb"
    _crear_duckdb(db)
    con = duckdb.connect(str(db), read_only=True)
    try:
        df = figuras._leer_estatus_terminal(con)
    finally:
        con.close()

    fig = figuras.construir_estatus_terminal(df)
    assert "INFERENCIA" in fig.layout.title.text
    assert "salida_no_explicada" in fig.layout.title.text


# ---------------------------------------------------------------------------
# sobrecosto
# ---------------------------------------------------------------------------


def test_sobrecosto_recorta_colas_y_declara_cuantos_excluye(tmp_path: Path) -> None:
    db = tmp_path / "gold.duckdb"
    _crear_duckdb(db)
    con = duckdb.connect(str(db), read_only=True)
    try:
        df = figuras._leer_sobrecosto(con)
    finally:
        con.close()

    # Solo OPA001 (15.0) y OPA003 (-150.0) tienen sobrecosto_pct no nulo.
    assert len(df) == 2
    fig = figuras.construir_sobrecosto(df)
    # -150.0 está fuera de [-100, 300] -- debe declararse explícitamente, no desaparecer mudo.
    assert "1 proyecto" in fig.layout.title.text
    assert "pesos corrientes" in fig.layout.title.text.lower()


# ---------------------------------------------------------------------------
# _ajustar
# ---------------------------------------------------------------------------


def test_ajustar_envuelve_texto_largo_con_br() -> None:
    texto = "palabra " * 30
    resultado = figuras._ajustar(texto, ancho=40)
    assert "<br>" in resultado
    assert all(len(linea) <= 40 for linea in resultado.split("<br>"))


def test_ajustar_no_toca_texto_corto() -> None:
    assert figuras._ajustar("texto corto", ancho=95) == "texto corto"


# ---------------------------------------------------------------------------
# generar_galeria
# ---------------------------------------------------------------------------


def test_generar_galeria_incluye_todas_las_figuras_registradas() -> None:
    md = figuras.generar_galeria(figuras.FIGURAS, "2026T1")
    assert "2026T1" in md
    for fig_def in figuras.FIGURAS:
        assert f"![{fig_def.titulo}]({fig_def.clave}.png)" in md
        assert fig_def.interpretacion in md
        assert fig_def.caveat in md


# ---------------------------------------------------------------------------
# exportar: falla ruidosa
# ---------------------------------------------------------------------------


def test_exportar_falla_ruidoso_si_falta_una_tabla(tmp_path: Path) -> None:
    db = tmp_path / "incompleto.duckdb"
    _duckdb_incompleto(db)
    with pytest.raises(figuras.ErrorFiguras, match="Faltan"):
        figuras.exportar(db, tmp_path / "salida")
    assert not (tmp_path / "salida" / "cobertura_cortes.png").exists()


def test_exportar_completo_contra_duckdb_real(tmp_path: Path) -> None:
    """Corrida end-to-end real, incluyendo Kaleido -- se salta si no hay Chrome disponible
    en esta máquina (mismo criterio que el resto del repo: no se prueba Kaleido en CI)."""
    pytest.importorskip("kaleido")
    try:
        go.Figure().to_image(format="png")
    except Exception:
        pytest.skip("Kaleido no puede exportar PNG en este entorno (falta Chrome)")

    db = tmp_path / "gold.duckdb"
    _crear_duckdb(db)
    escritas = figuras.exportar(db, tmp_path / "salida")

    nombres = {p.name for p in escritas}
    assert "GALERIA.md" in nombres
    for fig_def in figuras.FIGURAS:
        ruta_png = tmp_path / "salida" / f"{fig_def.clave}.png"
        assert ruta_png.exists()
        with ruta_png.open("rb") as fh:
            assert fh.read(8) == b"\x89PNG\r\n\x1a\n"  # firma real de PNG, no solo "el archivo existe"
