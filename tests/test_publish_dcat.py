"""Tests de catalog.json (DCAT, JSON-LD) del paquete publicado (Fase C del plan ATDT).

Construye en tmp_path un paquete falso (tabular/ + geojson/) más los 4 insumos reales
(conf/dcat.yml, schema.yml, manifest.jsonl, calidad_silver.md) con el mismo formato que usan
dcat_config.py, diccionario.py y dcat_procedencia.py -- no depende de datos reales del repo.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from opa import publish_dcat

DCAT_YML = """
catalogo:
  titulo: "Catálogo de prueba"
  descripcion: "Descripción de prueba."
  temas:
    - "finanzas públicas"
  licencia:
    nombre: "Términos de Libre Uso MX"
    url: "https://datos.gob.mx/libreusomx"
  cadencia:
    valor: "trimestral"
  fuente_primaria:
    url: "https://www.transparenciapresupuestaria.gob.mx"
"""

SCHEMA_YML = """
version: 2
models:
  - name: dim_ramo
    description: >
      Catálogo de ramos presupuestarios.
    columns:
      - name: id_ramo
        description: Identificador del ramo.
  - name: fct_ppi_observacion
    description: Observaciones por corte trimestral.
    columns:
      - name: cve_cartera
        description: Clave de cartera.
"""

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

CALIDAD_SILVER_MD = """## Resumen

- Normalizados a parquet: **88**
- Omitidos por corrupción conocida en la fuente: **3**
- Con esquema desconocido (no en `conf/schema_map.yml`): **0**
- Con error de lectura: **0**

- Filas totales procesadas: 179,179
- Filas válidas escritas a parquet: 177,245 (98.9%)
- Filas en cuarentena (fallan el contrato Pandera, no se escriben): 1,934
"""


def _sha256(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


def _escribir_insumos(base: Path) -> dict[str, Path]:
    ruta_dcat = base / "conf" / "dcat.yml"
    ruta_dcat.parent.mkdir(parents=True, exist_ok=True)
    ruta_dcat.write_text(DCAT_YML, encoding="utf-8")

    ruta_schema = base / "schema.yml"
    ruta_schema.write_text(SCHEMA_YML, encoding="utf-8")

    ruta_manifest = base / "manifest.jsonl"
    ruta_manifest.write_text(MANIFEST_JSONL, encoding="utf-8")

    ruta_calidad = base / "calidad_silver.md"
    ruta_calidad.write_text(CALIDAD_SILVER_MD, encoding="utf-8")

    return {
        "dcat": ruta_dcat,
        "schema": ruta_schema,
        "manifest": ruta_manifest,
        "calidad": ruta_calidad,
    }


def _crear_paquete_minimo(dir_paquete: Path) -> dict[str, bytes]:
    contenidos = {
        "tabular/dim_ramo.csv": b"id_ramo,nombre\n1,Salud\n",
        "tabular/dim_ramo.parquet": b"\x00parquet-simulado-dim-ramo\x01",
    }
    for ruta_rel, contenido in contenidos.items():
        ruta = dir_paquete / ruta_rel
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_bytes(contenido)
    return contenidos


def test_catalogo_minimo_es_json_valido_con_un_dataset(tmp_path: Path) -> None:
    dir_paquete = tmp_path / "paquete"
    contenidos = _crear_paquete_minimo(dir_paquete)
    insumos = _escribir_insumos(tmp_path)

    ruta_catalog = publish_dcat.escribir_catalogo(
        dir_paquete, insumos["dcat"], insumos["schema"], insumos["manifest"], insumos["calidad"]
    )

    assert ruta_catalog == dir_paquete / "catalog.json"
    documento = json.loads(ruta_catalog.read_text(encoding="utf-8"))

    assert documento["@type"] == "dcat:Catalog"
    assert len(documento["dcat:dataset"]) == 1

    dataset = documento["dcat:dataset"][0]
    assert dataset["dct:title"] == "dim_ramo"
    distribuciones = dataset["dcat:distribution"]
    assert len(distribuciones) == 2

    por_url = {d["dcat:downloadURL"]: d for d in distribuciones}
    assert "tabular/dim_ramo.csv" in por_url
    assert "tabular/dim_ramo.parquet" in por_url

    for ruta_rel, contenido in contenidos.items():
        dist = por_url[ruta_rel]
        assert dist["dcat:byteSize"] == len(contenido)
        assert dist["dct:checksum"]["spdx:checksumValue"] == _sha256(contenido)
        assert dist["dct:checksum"]["@type"] == "spdx:Checksum"

    assert por_url["tabular/dim_ramo.csv"]["dcat:mediaType"] == "text/csv"
    assert por_url["tabular/dim_ramo.parquet"]["dcat:mediaType"] == "application/vnd.apache.parquet"


def test_catalogo_agrega_distribuciones_geojson_a_fct_ppi_observacion(tmp_path: Path) -> None:
    dir_paquete = tmp_path / "paquete"
    _crear_paquete_minimo(dir_paquete)

    contenido_csv = b"cve_cartera,anio\nA1,2021\n"
    contenido_parquet = b"\x00parquet-simulado-fct\x01"
    (dir_paquete / "tabular" / "fct_ppi_observacion.csv").write_bytes(contenido_csv)
    (dir_paquete / "tabular" / "fct_ppi_observacion.parquet").write_bytes(contenido_parquet)

    contenido_geojson = b'{"type": "FeatureCollection", "features": []}'
    dir_geojson = dir_paquete / "geojson"
    dir_geojson.mkdir()
    (dir_geojson / "ppi_2021.geojson").write_bytes(contenido_geojson)

    insumos = _escribir_insumos(tmp_path)

    ruta_catalog = publish_dcat.escribir_catalogo(
        dir_paquete, insumos["dcat"], insumos["schema"], insumos["manifest"], insumos["calidad"]
    )
    documento = json.loads(ruta_catalog.read_text(encoding="utf-8"))

    datasets_por_nombre = {d["dct:title"]: d for d in documento["dcat:dataset"]}
    assert set(datasets_por_nombre) == {"dim_ramo", "fct_ppi_observacion"}

    dataset_fct = datasets_por_nombre["fct_ppi_observacion"]
    distribuciones = dataset_fct["dcat:distribution"]
    assert len(distribuciones) == 3

    por_url = {d["dcat:downloadURL"]: d for d in distribuciones}
    assert "geojson/ppi_2021.geojson" in por_url
    dist_geojson = por_url["geojson/ppi_2021.geojson"]
    assert dist_geojson["dcat:mediaType"] == "application/geo+json"
    assert dist_geojson["dcat:byteSize"] == len(contenido_geojson)
    assert dist_geojson["dct:checksum"]["spdx:checksumValue"] == _sha256(contenido_geojson)


def test_x_procedencia_y_x_calidad_presentes_con_valores_reales(tmp_path: Path) -> None:
    dir_paquete = tmp_path / "paquete"
    _crear_paquete_minimo(dir_paquete)
    insumos = _escribir_insumos(tmp_path)

    ruta_catalog = publish_dcat.escribir_catalogo(
        dir_paquete, insumos["dcat"], insumos["schema"], insumos["manifest"], insumos["calidad"]
    )
    documento = json.loads(ruta_catalog.read_text(encoding="utf-8"))

    procedencia = documento["x-procedencia"]
    assert procedencia["n_snapshots"] == 2
    assert procedencia["por_origen"] == {"vivo": 1, "wayback": 1}
    assert procedencia["rango_anios"] == [2015, 2016]

    calidad = documento["x-calidad"]
    assert calidad["snapshots_normalizados"] == 88
    assert calidad["filas_validas"] == 177245
    assert calidad["pct_filas_validas"] == 98.9

    assert "x-nota" in documento
    assert "extensión" in documento["x-nota"]


def test_dir_tabular_faltante_levanta_excepcion(tmp_path: Path) -> None:
    dir_paquete = tmp_path / "paquete"
    dir_paquete.mkdir()
    insumos = _escribir_insumos(tmp_path)

    with pytest.raises(publish_dcat.ErrorCatalogo, match="tabular"):
        publish_dcat.escribir_catalogo(
            dir_paquete, insumos["dcat"], insumos["schema"], insumos["manifest"], insumos["calidad"]
        )


def test_dir_tabular_vacio_levanta_excepcion(tmp_path: Path) -> None:
    dir_paquete = tmp_path / "paquete"
    (dir_paquete / "tabular").mkdir(parents=True)
    insumos = _escribir_insumos(tmp_path)

    with pytest.raises(publish_dcat.ErrorCatalogo, match="tabular"):
        publish_dcat.escribir_catalogo(
            dir_paquete, insumos["dcat"], insumos["schema"], insumos["manifest"], insumos["calidad"]
        )


def test_archivo_con_extension_desconocida_en_tabular_levanta_excepcion(tmp_path: Path) -> None:
    dir_paquete = tmp_path / "paquete"
    _crear_paquete_minimo(dir_paquete)
    (dir_paquete / "tabular" / "dim_ramo.xlsx").write_bytes(b"archivo colado por error")
    insumos = _escribir_insumos(tmp_path)

    with pytest.raises(publish_dcat.ErrorCatalogo, match="[Ee]xtensión"):
        publish_dcat.escribir_catalogo(
            dir_paquete, insumos["dcat"], insumos["schema"], insumos["manifest"], insumos["calidad"]
        )
