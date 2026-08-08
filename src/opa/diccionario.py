"""Diccionario de datos de la capa Gold (Fase A del plan de alineación ATDT).

Genera, a partir de ``dbt/models/marts/schema.yml`` (fuente única de las descripciones) y de
las columnas REALES de ``data/gold/panel_opa.duckdb``, un diccionario por tabla publicable:
``diccionario_datos_{tabla}.csv`` (tabular, como pide el Art. 38 de los Lineamientos incluso
para el diccionario mismo -- Art. 3-XV) más un ``DICCIONARIO.md`` legible por humanos.

Regla dura, misma filosofía que normalize: la deriva entre schema.yml y el duckdb es un
error, no una advertencia. Si una columna real no tiene descripción, o schema.yml documenta
una columna que ya no existe, esto LEVANTA -- así el diccionario publicado nunca puede
quedarse atrás de los datos sin que el build lo grite.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

import yaml


class ErrorDiccionario(RuntimeError):
    """Deriva entre schema.yml y las columnas reales del duckdb, o schema.yml inválido."""


@dataclass(frozen=True)
class ColumnaDiccionario:
    tabla: str
    posicion: int
    columna: str
    tipo_dato: str
    descripcion: str


def _normalizar_descripcion(texto: str) -> str:
    """Colapsa los saltos de línea de los bloques YAML plegados a una sola línea CSV-amigable."""
    return re.sub(r"\s+", " ", texto).strip()


def cargar_descripciones(ruta_schema_yml: Path) -> dict[str, dict[str, str]]:
    """Lee schema.yml y regresa {tabla: {columna: descripción}}.

    Solo incluye modelos con ``columns``; las descripciones de tabla no viajan aquí (van al
    encabezado del markdown vía :func:`cargar_descripciones_de_tablas`).
    """
    contenido = yaml.safe_load(ruta_schema_yml.read_text(encoding="utf-8"))
    por_tabla: dict[str, dict[str, str]] = {}
    for modelo in contenido.get("models", []):
        columnas = {}
        for col in modelo.get("columns", []):
            descripcion = col.get("description")
            if descripcion:
                columnas[col["name"]] = _normalizar_descripcion(descripcion)
            else:
                # Se registra como vacía a propósito: la validación de abajo la reporta con
                # nombre y tabla exactos en vez de omitirla silenciosamente.
                columnas[col["name"]] = ""
        por_tabla[modelo["name"]] = columnas
    return por_tabla


def cargar_descripciones_de_tablas(ruta_schema_yml: Path) -> dict[str, str]:
    """Descripción de cada modelo (tabla) de schema.yml, normalizada a una línea."""
    contenido = yaml.safe_load(ruta_schema_yml.read_text(encoding="utf-8"))
    return {
        m["name"]: _normalizar_descripcion(m.get("description", ""))
        for m in contenido.get("models", [])
    }


def columnas_reales(ruta_duckdb: Path, tablas: list[str]) -> dict[str, list[tuple[str, str]]]:
    """``[(columna, tipo)]`` por tabla, leído del duckdb en solo-lectura."""
    import duckdb  # import local: el CLI de Fase 0 no necesita duckdb instalado

    con = duckdb.connect(str(ruta_duckdb), read_only=True)
    try:
        resultado = {}
        for tabla in tablas:
            filas = con.execute(f"describe {tabla}").fetchall()
            resultado[tabla] = [(f[0], f[1]) for f in filas]
        return resultado
    finally:
        con.close()


def construir_diccionario(
    ruta_schema_yml: Path, ruta_duckdb: Path
) -> list[ColumnaDiccionario]:
    """Cruza schema.yml contra las columnas reales y falla ruidoso ante cualquier deriva.

    Errores que levantan :class:`ErrorDiccionario` (todos juntos, no solo el primero):
    - columna real sin descripción en schema.yml (o con descripción vacía);
    - columna documentada en schema.yml que ya no existe en la tabla real.
    """
    descripciones = cargar_descripciones(ruta_schema_yml)
    reales = columnas_reales(ruta_duckdb, list(descripciones))

    problemas: list[str] = []
    filas: list[ColumnaDiccionario] = []
    for tabla, columnas in reales.items():
        documentadas = descripciones[tabla]
        nombres_reales = {nombre for nombre, _ in columnas}
        for fantasma in sorted(set(documentadas) - nombres_reales):
            problemas.append(f"{tabla}.{fantasma}: documentada en schema.yml pero no existe en la tabla")
        for posicion, (nombre, tipo) in enumerate(columnas, start=1):
            descripcion = documentadas.get(nombre, "")
            if not descripcion:
                problemas.append(f"{tabla}.{nombre}: sin descripción en schema.yml")
                continue
            filas.append(ColumnaDiccionario(tabla, posicion, nombre, tipo, descripcion))

    if problemas:
        detalle = "\n  - ".join(problemas)
        raise ErrorDiccionario(
            f"Deriva entre schema.yml y el duckdb ({len(problemas)} problema(s)):\n  - {detalle}"
        )
    return filas


def escribir_diccionario(
    filas: list[ColumnaDiccionario],
    descripciones_tablas: dict[str, str],
    dir_salida: Path,
) -> list[Path]:
    """Escribe un CSV por tabla + DICCIONARIO.md consolidado. Regresa las rutas escritas."""
    dir_salida.mkdir(parents=True, exist_ok=True)
    escritas: list[Path] = []

    tablas = sorted({f.tabla for f in filas})
    for tabla in tablas:
        ruta_csv = dir_salida / f"diccionario_datos_{tabla}.csv"
        with ruta_csv.open("w", encoding="utf-8", newline="") as fh:
            escritor = csv.writer(fh)
            escritor.writerow(["tabla", "posicion", "columna", "tipo_dato", "descripcion"])
            for f in sorted(
                (f for f in filas if f.tabla == tabla), key=lambda f: f.posicion
            ):
                escritor.writerow([f.tabla, f.posicion, f.columna, f.tipo_dato, f.descripcion])
        escritas.append(ruta_csv)

    lineas = [
        "# Diccionario de datos -- panel OPA (capa Gold)",
        "",
        "Generado desde `dbt/models/marts/schema.yml` (fuente única) contra las columnas",
        "reales de `data/gold/panel_opa.duckdb` -- no editar a mano, regenerar con",
        "`opa diccionario`. Montos en pesos corrientes MXN salvo indicación contraria;",
        "avance físico en puntos porcentuales 0-100.",
        "",
    ]
    for tabla in tablas:
        lineas.append(f"## {tabla}")
        lineas.append("")
        if descripciones_tablas.get(tabla):
            lineas.append(descripciones_tablas[tabla])
            lineas.append("")
        lineas.append("| # | Columna | Tipo | Descripción |")
        lineas.append("|---|---------|------|-------------|")
        for f in sorted((f for f in filas if f.tabla == tabla), key=lambda f: f.posicion):
            descripcion_md = f.descripcion.replace("|", "\\|")
            lineas.append(f"| {f.posicion} | `{f.columna}` | {f.tipo_dato} | {descripcion_md} |")
        lineas.append("")

    ruta_md = dir_salida / "DICCIONARIO.md"
    ruta_md.write_text("\n".join(lineas), encoding="utf-8")
    escritas.append(ruta_md)
    return escritas


def generar(ruta_schema_yml: Path, ruta_duckdb: Path, dir_salida: Path) -> list[Path]:
    """Pipeline completo: construir (validando) y escribir. La cara que usa el CLI."""
    filas = construir_diccionario(ruta_schema_yml, ruta_duckdb)
    tablas = cargar_descripciones_de_tablas(ruta_schema_yml)
    return escribir_diccionario(filas, tablas, dir_salida)
