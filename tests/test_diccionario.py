"""Tests del diccionario de datos (Fase A del plan de alineación ATDT).

La pieza crítica es la validación de deriva: el diccionario debe NEGARSE a generarse si
schema.yml y las columnas reales del duckdb no coinciden exactamente -- en cualquiera de
las dos direcciones. Los tests construyen un duckdb y un schema.yml mínimos en tmp_path;
no dependen del duckdb real del repo (que no existe en CI).
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from opa import diccionario


def _crear_duckdb(ruta: Path) -> None:
    con = duckdb.connect(str(ruta))
    con.execute("create table dim_prueba (id integer, nombre varchar)")
    con.close()


def _escribir_schema(ruta: Path, contenido: str) -> Path:
    ruta.write_text(contenido, encoding="utf-8")
    return ruta


SCHEMA_COMPLETO = """
version: 2
models:
  - name: dim_prueba
    description: >
      Tabla de prueba con descripción
      en dos líneas plegadas.
    columns:
      - name: id
        description: Identificador de prueba.
      - name: nombre
        description: Nombre de prueba.
"""

SCHEMA_SIN_DESCRIPCION = """
version: 2
models:
  - name: dim_prueba
    columns:
      - name: id
        description: Identificador de prueba.
      - name: nombre
"""

SCHEMA_COLUMNA_FANTASMA = """
version: 2
models:
  - name: dim_prueba
    columns:
      - name: id
        description: Identificador de prueba.
      - name: nombre
        description: Nombre de prueba.
      - name: columna_borrada
        description: Documenta algo que ya no existe.
"""


def test_genera_csv_y_md_con_schema_completo(tmp_path: Path) -> None:
    db = tmp_path / "gold.duckdb"
    _crear_duckdb(db)
    schema = _escribir_schema(tmp_path / "schema.yml", SCHEMA_COMPLETO)

    escritas = diccionario.generar(schema, db, tmp_path / "salida")

    nombres = {p.name for p in escritas}
    assert nombres == {"diccionario_datos_dim_prueba.csv", "DICCIONARIO.md"}

    csv_texto = (tmp_path / "salida" / "diccionario_datos_dim_prueba.csv").read_text(encoding="utf-8")
    assert "tabla,posicion,columna,tipo_dato,descripcion" in csv_texto
    assert "dim_prueba,1,id,INTEGER,Identificador de prueba." in csv_texto
    assert "dim_prueba,2,nombre,VARCHAR,Nombre de prueba." in csv_texto

    md_texto = (tmp_path / "salida" / "DICCIONARIO.md").read_text(encoding="utf-8")
    assert "## dim_prueba" in md_texto
    # La descripción de tabla plegada en YAML se colapsa a una sola línea.
    assert "Tabla de prueba con descripción en dos líneas plegadas." in md_texto
    assert "| 1 | `id` | INTEGER | Identificador de prueba. |" in md_texto


def test_falla_ruidoso_si_columna_real_sin_descripcion(tmp_path: Path) -> None:
    db = tmp_path / "gold.duckdb"
    _crear_duckdb(db)
    schema = _escribir_schema(tmp_path / "schema.yml", SCHEMA_SIN_DESCRIPCION)

    with pytest.raises(diccionario.ErrorDiccionario, match=r"dim_prueba\.nombre: sin descripción"):
        diccionario.generar(schema, db, tmp_path / "salida")
    # Y no debe dejar salida parcial: la validación ocurre antes de escribir nada.
    assert not (tmp_path / "salida").exists()


def test_falla_ruidoso_si_schema_documenta_columna_inexistente(tmp_path: Path) -> None:
    db = tmp_path / "gold.duckdb"
    _crear_duckdb(db)
    schema = _escribir_schema(tmp_path / "schema.yml", SCHEMA_COLUMNA_FANTASMA)

    with pytest.raises(
        diccionario.ErrorDiccionario, match=r"dim_prueba\.columna_borrada: documentada .* no existe"
    ):
        diccionario.generar(schema, db, tmp_path / "salida")


def test_reporta_todos_los_problemas_juntos_no_solo_el_primero(tmp_path: Path) -> None:
    db = tmp_path / "gold.duckdb"
    _crear_duckdb(db)
    schema = _escribir_schema(
        tmp_path / "schema.yml",
        """
version: 2
models:
  - name: dim_prueba
    columns:
      - name: id
      - name: columna_borrada
        description: Fantasma.
""",
    )

    with pytest.raises(diccionario.ErrorDiccionario) as exc_info:
        diccionario.generar(schema, db, tmp_path / "salida")
    mensaje = str(exc_info.value)
    # nombre sin entrada, id sin descripción y la fantasma: los 3 en un solo reporte.
    assert "dim_prueba.id: sin descripción" in mensaje
    assert "dim_prueba.nombre: sin descripción" in mensaje
    assert "dim_prueba.columna_borrada" in mensaje


def test_schema_real_del_repo_no_tiene_columnas_sin_descripcion() -> None:
    """Guardia de CI sobre el schema.yml REAL: toda columna listada debe traer descripción.

    No requiere el duckdb (no existe en CI) -- la deriva contra columnas reales la valida
    `opa diccionario` localmente. Esto atrapa el caso más común: alguien agrega una columna
    a schema.yml (por un test nuevo) sin documentarla.
    """
    ruta = Path(__file__).parent.parent / "dbt" / "models" / "marts" / "schema.yml"
    por_tabla = diccionario.cargar_descripciones(ruta)
    sin_descripcion = [
        f"{tabla}.{col}"
        for tabla, columnas in por_tabla.items()
        for col, desc in columnas.items()
        if not desc
    ]
    assert sin_descripcion == [], (
        "Columnas en dbt/models/marts/schema.yml sin descripción (el diccionario de datos "
        f"las necesita -- ver docs/PLAN-alineacion-gold-lineamientos-ATDT.md): {sin_descripcion}"
    )
