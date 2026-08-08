"""Tests del exportador GeoJSON (Fase B del plan de alineación ATDT).

Construye un duckdb mínimo con la tabla fct_ppi_observacion directamente (no depende del
duckdb real del repo, que no existe en CI) -- exactamente el patrón de test_diccionario.py.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb

from opa import publish_geojson


def _crear_duckdb(ruta: Path) -> None:
    con = duckdb.connect(str(ruta))
    con.execute(
        """
        create table fct_ppi_observacion (
            cve_cartera varchar,
            snapshot_id integer,
            anio_corte double,
            latitud double,
            longitud double,
            descripcion_ramo varchar,
            descripcion_tipo_ppi varchar,
            entidad_federativa varchar,
            avance_fisico double,
            estatus_operacion varchar,
            modificado double,
            ejercido double,
            monto_total_inversion double
        )
        """
    )
    con.execute(
        """
        insert into fct_ppi_observacion values
        ('OPA001', 1, 2020.0, 19.4326, -99.1332, 'Comunicaciones', 'Carretero',
         'Ciudad de México', 45.5, 'En ejecución', 1000000.0, 500000.0, 2000000.0),
        ('OPA002', 1, 2020.0, 20.6597, -103.3496, 'Salud', 'Hospitalario',
         'Jalisco', NULL, 'En ejecución', 800000.0, 400000.0, 1500000.0),
        ('OPA003', 1, 2021.0, 25.6866, -100.3161, 'Educación', 'Escolar',
         'Nuevo León', 60.0, 'Concluido', 500000.0, 500000.0, 500000.0),
        ('OPA004', 1, 2019.0, NULL, NULL, 'Salud', 'Hospitalario',
         'Campeche', 10.0, 'En ejecución', 100000.0, 50000.0, 300000.0),
        ('OPA005', 1, NULL, 18.5, -91.0, 'Agua', 'Hidráulico',
         'Campeche', 30.0, 'En ejecución', 200000.0, 100000.0, 400000.0)
        """
    )
    con.close()


def test_escribe_un_archivo_por_anio_y_excluye_filas_sin_coordenadas(tmp_path: Path) -> None:
    db = tmp_path / "gold.duckdb"
    _crear_duckdb(db)

    escritas = publish_geojson.escribir_geojson(db, tmp_path / "salida", "v1")

    nombres = {p.name for p in escritas}
    assert nombres == {"ppi_2020.geojson", "ppi_2021.geojson", "ppi_sin_anio.geojson"}
    for ruta in escritas:
        assert ruta.parent == tmp_path / "salida" / "v1" / "geojson"
    # OPA004 (sin coordenadas) no debe aparecer en ningún archivo.
    assert not (tmp_path / "salida" / "v1" / "geojson" / "ppi_2019.geojson").exists()


def test_archivos_son_geojson_valido_con_orden_lon_lat(tmp_path: Path) -> None:
    db = tmp_path / "gold.duckdb"
    _crear_duckdb(db)

    publish_geojson.escribir_geojson(db, tmp_path / "salida", "v1")

    ruta_2020 = tmp_path / "salida" / "v1" / "geojson" / "ppi_2020.geojson"
    with ruta_2020.open(encoding="utf-8") as fh:
        coleccion = json.load(fh)

    assert coleccion["type"] == "FeatureCollection"
    assert len(coleccion["features"]) == 2

    feature_opa001 = next(
        f for f in coleccion["features"] if f["properties"]["cve_cartera"] == "OPA001"
    )
    assert feature_opa001["type"] == "Feature"
    assert feature_opa001["geometry"] == {
        "type": "Point",
        "coordinates": [-99.1332, 19.4326],
    }


def test_nulos_se_convierten_a_none_no_a_nan_ni_a_texto(tmp_path: Path) -> None:
    db = tmp_path / "gold.duckdb"
    _crear_duckdb(db)

    publish_geojson.escribir_geojson(db, tmp_path / "salida", "v1")

    ruta_2020 = tmp_path / "salida" / "v1" / "geojson" / "ppi_2020.geojson"
    with ruta_2020.open(encoding="utf-8") as fh:
        coleccion = json.load(fh)

    feature_opa002 = next(
        f for f in coleccion["features"] if f["properties"]["cve_cartera"] == "OPA002"
    )
    assert feature_opa002["properties"]["avance_fisico"] is None


def test_archivo_sin_anio_contiene_solo_la_fila_con_anio_corte_nulo(tmp_path: Path) -> None:
    db = tmp_path / "gold.duckdb"
    _crear_duckdb(db)

    publish_geojson.escribir_geojson(db, tmp_path / "salida", "v1")

    ruta_sin_anio = tmp_path / "salida" / "v1" / "geojson" / "ppi_sin_anio.geojson"
    with ruta_sin_anio.open(encoding="utf-8") as fh:
        coleccion = json.load(fh)

    assert [f["properties"]["cve_cartera"] for f in coleccion["features"]] == ["OPA005"]


def test_no_escribe_archivo_para_grupo_vacio(tmp_path: Path) -> None:
    db = tmp_path / "gold.duckdb"
    con = duckdb.connect(str(db))
    con.execute(
        """
        create table fct_ppi_observacion (
            cve_cartera varchar,
            snapshot_id integer,
            anio_corte double,
            latitud double,
            longitud double,
            descripcion_ramo varchar,
            descripcion_tipo_ppi varchar,
            entidad_federativa varchar,
            avance_fisico double,
            estatus_operacion varchar,
            modificado double,
            ejercido double,
            monto_total_inversion double
        )
        """
    )
    con.execute(
        """
        insert into fct_ppi_observacion values
        ('OPA001', 1, 2019.0, NULL, NULL, 'Salud', 'Hospitalario',
         'Campeche', 10.0, 'En ejecución', 100000.0, 50000.0, 300000.0)
        """
    )
    con.close()

    escritas = publish_geojson.escribir_geojson(db, tmp_path / "salida", "v1")

    assert escritas == []
