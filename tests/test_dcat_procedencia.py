"""Tests de los resúmenes de procedencia y calidad para el catálogo DCAT (Fase C, ATDT).

Verifica la agregación real de ``data/manifest.jsonl`` y la extracción por regex de la
sección ``## Resumen`` de ``reports/calidad_silver.md``, y que ambas fallen ruidoso ante
insumos faltantes, vacíos o mal formados en vez de regresar ceros o Nones silenciosos.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from opa import dcat_procedencia

MANIFEST_LINEAS = [
    {
        "snapshot_id": "2015_anual_cf606d2d",
        "url": "https://www.transparenciapresupuestaria.gob.mx/work/models/PTP/OPA/2015/Proyectos_OPA.csv",
        "origen": "vivo",
        "fecha_descarga": "2026-08-08",
        "http_status": 200,
        "sha256": "cf606d2d",
        "bytes": 3701756,
        "corte_declarado": {"anio": 2015, "trimestre": None},
        "archivo_bronze": "opa_2015_anual_cf606d2d.csv",
        "header_hash": "hash1",
        "n_columnas": 45,
        "encoding_detectado": "utf-8-sig",
        "wayback_timestamp": None,
    },
    {
        "snapshot_id": "2016_t3_abc12345",
        "url": "https://web.archive.org/web/2016xxxx/https://www.transparenciapresupuestaria.gob.mx/...",
        "origen": "wayback",
        "fecha_descarga": "2026-08-01",
        "http_status": 200,
        "sha256": "abc12345",
        "bytes": 1500000,
        "corte_declarado": {"anio": 2016, "trimestre": 3},
        "archivo_bronze": "opa_2016_t3_abc12345.csv",
        "header_hash": "hash2",
        "n_columnas": 45,
        "encoding_detectado": "utf-8",
        "wayback_timestamp": "20161015000000",
    },
    {
        "snapshot_id": "2019_t1_deadbeef",
        "url": "https://www.transparenciapresupuestaria.gob.mx/work/models/PTP/OPA/2019/OPAPrimerTrimestre2019.csv",
        "origen": "vivo",
        "fecha_descarga": "2026-08-05",
        "http_status": 200,
        "sha256": "deadbeef",
        "bytes": 2200000,
        "corte_declarado": {"anio": 2019, "trimestre": 1},
        "archivo_bronze": "opa_2019_t1_deadbeef.csv",
        "header_hash": "hash3",
        "n_columnas": 47,
        "encoding_detectado": "utf-8-sig",
        "wayback_timestamp": None,
    },
    {
        "snapshot_id": "2020_anual_00000000",
        "url": "https://www.transparenciapresupuestaria.gob.mx/work/models/PTP/OPA/2020/Proyectos_OPA.csv",
        "origen": "wayback",
        "fecha_descarga": "2026-07-20",
        "http_status": 200,
        "sha256": "00000000",
        "bytes": 4000000,
        "corte_declarado": {"anio": None, "trimestre": None},
        "archivo_bronze": "opa_2020_anual_00000000.csv",
        "header_hash": "hash4",
        "n_columnas": 45,
        "encoding_detectado": "utf-8",
        "wayback_timestamp": "20200101000000",
    },
]

CALIDAD_MD = """# Reporte de calidad Silver

## Resumen

- Normalizados a parquet: **88**
- Omitidos por corrupción conocida en la fuente: **3**
- Con esquema desconocido (no en `conf/schema_map.yml`): **0**
- Con error de lectura: **0**

- Filas totales procesadas: 179,179
- Filas válidas escritas a parquet: 177,245 (98.9%)
- Filas en cuarentena (fallan el contrato Pandera, no se escriben): 1,934
"""


def _escribir_manifest(ruta: Path, lineas: list[dict]) -> None:
    ruta.write_text("\n".join(json.dumps(linea) for linea in lineas) + "\n", encoding="utf-8")


def test_resumen_procedencia_agrega_correctamente(tmp_path: Path) -> None:
    ruta = tmp_path / "manifest.jsonl"
    _escribir_manifest(ruta, MANIFEST_LINEAS)

    resumen = dcat_procedencia.resumen_procedencia(ruta)

    assert resumen["n_snapshots"] == 4
    assert resumen["por_origen"] == {"vivo": 2, "wayback": 2}
    assert resumen["fecha_descarga_mas_reciente"] == "2026-08-08"
    assert resumen["bytes_totales"] == 3701756 + 1500000 + 2200000 + 4000000
    assert resumen["rango_anios"] == [2015, 2019]


def test_resumen_procedencia_manifiesto_inexistente_levanta_excepcion(tmp_path: Path) -> None:
    with pytest.raises(dcat_procedencia.ErrorProcedencia, match="No existe"):
        dcat_procedencia.resumen_procedencia(tmp_path / "no_existe.jsonl")


def test_resumen_procedencia_manifiesto_vacio_levanta_excepcion(tmp_path: Path) -> None:
    ruta = tmp_path / "manifest.jsonl"
    ruta.write_text("", encoding="utf-8")

    with pytest.raises(dcat_procedencia.ErrorProcedencia, match="vacío"):
        dcat_procedencia.resumen_procedencia(ruta)


def test_resumen_procedencia_linea_corrupta_reporta_numero_de_linea(tmp_path: Path) -> None:
    ruta = tmp_path / "manifest.jsonl"
    lineas_texto = [json.dumps(linea) for linea in MANIFEST_LINEAS[:2]]
    lineas_texto.append("{esto no es json valido")
    lineas_texto.append(json.dumps(MANIFEST_LINEAS[2]))
    ruta.write_text("\n".join(lineas_texto) + "\n", encoding="utf-8")

    with pytest.raises(dcat_procedencia.ErrorProcedencia, match="Línea 3"):
        dcat_procedencia.resumen_procedencia(ruta)


def test_resumen_calidad_extrae_valores_correctos(tmp_path: Path) -> None:
    ruta = tmp_path / "calidad_silver.md"
    ruta.write_text(CALIDAD_MD, encoding="utf-8")

    resumen = dcat_procedencia.resumen_calidad(ruta)

    assert resumen == {
        "snapshots_normalizados": 88,
        "snapshots_omitidos_corruptos": 3,
        "snapshots_esquema_desconocido": 0,
        "snapshots_error_lectura": 0,
        "filas_totales": 179179,
        "filas_validas": 177245,
        "pct_filas_validas": 98.9,
        "filas_en_cuarentena": 1934,
    }


def test_resumen_calidad_archivo_inexistente_levanta_excepcion(tmp_path: Path) -> None:
    with pytest.raises(dcat_procedencia.ErrorProcedencia, match="No existe"):
        dcat_procedencia.resumen_calidad(tmp_path / "no_existe.md")


def test_resumen_calidad_sin_seccion_resumen_lista_campos_faltantes(tmp_path: Path) -> None:
    ruta = tmp_path / "calidad_silver.md"
    ruta.write_text("# Reporte de calidad Silver\n\nSin sección de resumen aquí.\n", encoding="utf-8")

    with pytest.raises(dcat_procedencia.ErrorProcedencia, match="snapshots_normalizados"):
        dcat_procedencia.resumen_calidad(ruta)


def test_resumen_calidad_linea_faltante_lista_ese_campo(tmp_path: Path) -> None:
    md_incompleto = CALIDAD_MD.replace(
        "- Filas en cuarentena (fallan el contrato Pandera, no se escriben): 1,934\n", ""
    )
    ruta = tmp_path / "calidad_silver.md"
    ruta.write_text(md_incompleto, encoding="utf-8")

    with pytest.raises(dcat_procedencia.ErrorProcedencia, match="filas_en_cuarentena"):
        dcat_procedencia.resumen_calidad(ruta)
