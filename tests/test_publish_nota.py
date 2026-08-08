"""Tests de NOTA-TECNICA.md del paquete publicado (Fase D del plan ATDT).

Construye en tmp_path un manifest.jsonl y calidad_silver.md de prueba con el mismo formato
que usan los tests de dcat_procedencia.py -- no depende de datos reales del repo.
"""

from __future__ import annotations

import json
from pathlib import Path

from opa import publish_nota

MANIFEST_JSONL = "\n".join(
    [
        json.dumps(
            {
                "snapshot_id": "2015_anual_cf606d2d",
                "url": "https://www.transparenciapresupuestaria.gob.mx/x.csv",
                "origen": "vivo",
                "fecha_descarga": "2026-08-08",
                "http_status": 200,
                "sha256": "cf606d2d",
                "bytes": 3701756,
                "corte_declarado": {"anio": 2015, "trimestre": None},
                "archivo_bronze": "opa_2015_anual_cf606d2d.csv",
                "header_hash": "abc",
                "n_columnas": 45,
                "encoding_detectado": "utf-8-sig",
                "wayback_timestamp": None,
            }
        ),
        json.dumps(
            {
                "snapshot_id": "2016_t3_abc123",
                "url": "https://web.archive.org/x.csv",
                "origen": "wayback",
                "fecha_descarga": "2026-08-01",
                "http_status": 200,
                "sha256": "abc123",
                "bytes": 100,
                "corte_declarado": {"anio": 2016, "trimestre": 3},
                "archivo_bronze": "opa_2016_t3_abc123.csv",
                "header_hash": "def",
                "n_columnas": 45,
                "encoding_detectado": "utf-8",
                "wayback_timestamp": "20160930000000",
            }
        ),
    ]
)

CALIDAD_SILVER_MD = """# Reporte de calidad Silver

## Resumen

- Normalizados a parquet: **88**
- Omitidos por corrupción conocida en la fuente: **3**
- Con esquema desconocido (no en `conf/schema_map.yml`): **0**
- Con error de lectura: **0**

- Filas totales procesadas: 179,179
- Filas válidas escritas a parquet: 177,245 (98.9%)
- Filas en cuarentena (fallan el contrato Pandera, no se escriben): 1,934
"""

SECCIONES_ESPERADAS = [
    "## Evaluación de datos personales (Art. 38-VI)",
    "## Patrón estacional Q4→Q1",
    "## Cortes con calidad conocida y verificada",
    "## Cobertura parcial en algunos cortes",
    "## Huecos históricos reales",
    "## Deflactación pendiente",
    "## Variantes de texto sin normalizar",
]


def _escribir_insumos(base: Path) -> dict[str, Path]:
    ruta_manifest = base / "manifest.jsonl"
    ruta_manifest.write_text(MANIFEST_JSONL, encoding="utf-8")

    ruta_calidad = base / "calidad_silver.md"
    ruta_calidad.write_text(CALIDAD_SILVER_MD, encoding="utf-8")

    return {"manifest": ruta_manifest, "calidad": ruta_calidad}


def test_nota_tecnica_contiene_las_siete_secciones(tmp_path: Path) -> None:
    dir_paquete = tmp_path / "paquete"
    insumos = _escribir_insumos(tmp_path)

    ruta_nota = publish_nota.escribir_nota_tecnica(
        dir_paquete, insumos["manifest"], insumos["calidad"]
    )

    assert ruta_nota == dir_paquete / "NOTA-TECNICA.md"
    contenido = ruta_nota.read_text(encoding="utf-8")

    for encabezado in SECCIONES_ESPERADAS:
        assert encabezado in contenido


def test_veredicto_de_privacidad_aparece_textual(tmp_path: Path) -> None:
    dir_paquete = tmp_path / "paquete"
    insumos = _escribir_insumos(tmp_path)

    ruta_nota = publish_nota.escribir_nota_tecnica(
        dir_paquete, insumos["manifest"], insumos["calidad"]
    )
    contenido = ruta_nota.read_text(encoding="utf-8")

    assert (
        "Se evaluaron las 3 columnas de texto libre de dim_ppi (nombre_ppi: 11,119 valores "
        "distintos; descripcion_ur: 506; localizacion: 5,166) buscando datos personales de "
        "personas físicas identificables, conforme al Art. 38-VI de los Lineamientos ATDT."
    ) in contenido
    assert (
        "Resultado: CONFIRMADO -- no se encontró ningún nombre de persona física "
        "identificable en su carácter privado."
    ) in contenido


def test_pie_de_pagina_coincide_con_fixture_de_manifest(tmp_path: Path) -> None:
    dir_paquete = tmp_path / "paquete"
    insumos = _escribir_insumos(tmp_path)

    ruta_nota = publish_nota.escribir_nota_tecnica(
        dir_paquete, insumos["manifest"], insumos["calidad"]
    )
    contenido = ruta_nota.read_text(encoding="utf-8")

    assert "2026-08-08" in contenido
    assert "2015-2016" in contenido


def test_seccion_de_calidad_coincide_con_fixture_de_calidad_silver(tmp_path: Path) -> None:
    dir_paquete = tmp_path / "paquete"
    insumos = _escribir_insumos(tmp_path)

    ruta_nota = publish_nota.escribir_nota_tecnica(
        dir_paquete, insumos["manifest"], insumos["calidad"]
    )
    contenido = ruta_nota.read_text(encoding="utf-8")

    assert "**3**" in contenido
    assert "98.9%" in contenido
    assert "177,245" in contenido
    assert "179,179" in contenido
    assert "1,934" in contenido


def test_dir_paquete_inexistente_se_crea(tmp_path: Path) -> None:
    dir_paquete = tmp_path / "no_existe_aun" / "paquete"
    insumos = _escribir_insumos(tmp_path)

    assert not dir_paquete.exists()

    ruta_nota = publish_nota.escribir_nota_tecnica(
        dir_paquete, insumos["manifest"], insumos["calidad"]
    )

    assert dir_paquete.is_dir()
    assert ruta_nota.is_file()
