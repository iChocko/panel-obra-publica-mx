"""Tests del exportador GeoJSON (Fase B del plan de alineación ATDT).

Construye un duckdb mínimo con fct_ppi_observacion + dim_snapshot + dim_ppi directamente (no
depende del duckdb real del repo, que no existe en CI) -- patrón de test_diccionario.py.
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
            snapshot_id varchar,
            anio_corte double,
            trimestre_corte integer,
            latitud double,
            longitud double,
            descripcion_ramo varchar,
            descripcion_tipo_ppi varchar,
            entidad_federativa varchar,
            fase varchar,
            avance_fisico double,
            estatus_operacion varchar,
            aprobado double,
            ppef double,
            pef double,
            modificado double,
            ejercido double,
            monto_total_inversion double
        )
        """
    )
    con.execute(
        """
        create table dim_snapshot (
            snapshot_id varchar,
            anio integer,
            trimestre integer
        )
        """
    )
    con.execute(
        """
        create table dim_ppi (
            cve_cartera varchar,
            version_ppi integer,
            vigente_desde_corte integer,
            vigente_hasta_corte integer,
            nombre_ppi varchar,
            descripcion_ur varchar,
            localizacion varchar
        )
        """
    )
    con.execute(
        """
        insert into dim_snapshot values
        ('2020Q1', 2020, 1),
        ('2021Q1', 2021, 1),
        ('2019_anual', 2019, NULL)
        """
    )
    con.execute(
        """
        insert into dim_ppi values
        ('OPA001', 1, 20191, 20204, 'Puente Peatonal Reforma', 'Dirección de Obras Públicas',
         'Av. Reforma esq. Insurgentes, CDMX'),
        ('OPA003', 1, 20211, 20214, 'Escuela Primaria Benito Juárez', 'Secretaría de Educación',
         'Col. Centro, Monterrey')
        """
    )
    con.execute(
        """
        insert into fct_ppi_observacion values
        ('OPA001', '2020Q1', 2020.0, 1, 19.4326, -99.1332, 'Comunicaciones', 'Carretero',
         'Ciudad de México', NULL, 45.5, 'En ejecución', 1200000.0, 1100000.0, 1050000.0,
         1000000.0, 500000.0, 2000000.0),
        ('OPA002', '2020Q1', 2020.0, 1, 20.6597, -103.3496, 'Salud', 'Hospitalario',
         'Jalisco', NULL, NULL, 'En ejecución', 900000.0, NULL, NULL,
         800000.0, 400000.0, 1500000.0),
        ('OPA003', '2021Q1', 2021.0, 1, 25.6866, -100.3161, 'Educación', 'Escolar',
         'Nuevo León', NULL, 60.0, 'Concluido', 500000.0, 500000.0, 500000.0,
         500000.0, 500000.0, 500000.0),
        ('OPA004', '2019_anual', 2019.0, NULL, NULL, NULL, 'Salud', 'Hospitalario',
         'Campeche', NULL, 10.0, 'En ejecución', 100000.0, 100000.0, 100000.0,
         100000.0, 50000.0, 300000.0),
        ('OPA005', '2020Q1', NULL, NULL, 18.5, -91.0, 'Agua', 'Hidráulico',
         'Campeche', NULL, 30.0, 'En ejecución', 200000.0, 200000.0, 200000.0,
         200000.0, 100000.0, 400000.0)
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
    assert feature_opa002["properties"]["ppef"] is None
    # OPA002 no está en dim_ppi -- el LEFT JOIN debe traer None, no tronar.
    assert feature_opa002["properties"]["nombre_ppi"] is None
    assert feature_opa002["properties"]["descripcion_ur"] is None


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
            snapshot_id varchar,
            anio_corte double,
            trimestre_corte integer,
            latitud double,
            longitud double,
            descripcion_ramo varchar,
            descripcion_tipo_ppi varchar,
            entidad_federativa varchar,
            fase varchar,
            avance_fisico double,
            estatus_operacion varchar,
            aprobado double,
            ppef double,
            pef double,
            modificado double,
            ejercido double,
            monto_total_inversion double
        )
        """
    )
    con.execute("create table dim_snapshot (snapshot_id varchar, anio integer, trimestre integer)")
    con.execute(
        """
        create table dim_ppi (
            cve_cartera varchar, version_ppi integer, vigente_desde_corte integer,
            vigente_hasta_corte integer, nombre_ppi varchar, descripcion_ur varchar,
            localizacion varchar
        )
        """
    )
    con.execute("insert into dim_snapshot values ('2019_anual', 2019, NULL)")
    con.execute(
        """
        insert into fct_ppi_observacion values
        ('OPA001', '2019_anual', 2019.0, NULL, NULL, NULL, 'Salud', 'Hospitalario',
         'Campeche', NULL, 10.0, 'En ejecución', 100000.0, 100000.0, 100000.0,
         100000.0, 50000.0, 300000.0)
        """
    )
    con.close()

    escritas = publish_geojson.escribir_geojson(db, tmp_path / "salida", "v1")

    assert escritas == []


def test_enriquece_con_nombre_y_ubicacion_del_ppi_vigente_en_el_corte(tmp_path: Path) -> None:
    db = tmp_path / "gold.duckdb"
    _crear_duckdb(db)

    publish_geojson.escribir_geojson(db, tmp_path / "salida", "v1")

    ruta_2020 = tmp_path / "salida" / "v1" / "geojson" / "ppi_2020.geojson"
    with ruta_2020.open(encoding="utf-8") as fh:
        propiedades_2020 = {
            f["properties"]["cve_cartera"]: f["properties"]
            for f in json.load(fh)["features"]
        }

    # OPA001 en el corte 2020Q1 (orden_corte 20201) cae dentro del rango vigente 20191-20204
    # de dim_ppi -- debe traer el nombre y ubicación de esa versión.
    assert propiedades_2020["OPA001"]["nombre_ppi"] == "Puente Peatonal Reforma"
    assert propiedades_2020["OPA001"]["descripcion_ur"] == "Dirección de Obras Públicas"
    assert propiedades_2020["OPA001"]["localizacion"] == "Av. Reforma esq. Insurgentes, CDMX"
    assert propiedades_2020["OPA001"]["trimestre_corte"] == 1
    assert propiedades_2020["OPA001"]["aprobado"] == 1200000.0
    assert propiedades_2020["OPA001"]["ppef"] == 1100000.0
    assert propiedades_2020["OPA001"]["pef"] == 1050000.0

    ruta_2021 = tmp_path / "salida" / "v1" / "geojson" / "ppi_2021.geojson"
    with ruta_2021.open(encoding="utf-8") as fh:
        propiedades_2021 = {
            f["properties"]["cve_cartera"]: f["properties"]
            for f in json.load(fh)["features"]
        }
    assert propiedades_2021["OPA003"]["nombre_ppi"] == "Escuela Primaria Benito Juárez"


def test_snapshot_anual_sin_trimestre_no_enriquece_pero_se_publica(tmp_path: Path) -> None:
    """dim_snapshot.trimestre nulo -> orden_corte nulo -> no calza ningún rango de dim_ppi.

    El punto se sigue publicando (LEFT JOIN), solo sin nombre/ubicación -- ver docstring del
    módulo. OPA004 no tiene coordenadas en el fixture, así que se prueba con OPA005 en su
    lugar cambiando el fixture puntualmente aquí (snapshot 2019_anual con coordenadas).
    """
    db = tmp_path / "gold.duckdb"
    con = duckdb.connect(str(db))
    con.execute(
        """
        create table fct_ppi_observacion (
            cve_cartera varchar, snapshot_id varchar, anio_corte double, trimestre_corte integer,
            latitud double, longitud double, descripcion_ramo varchar, descripcion_tipo_ppi varchar,
            entidad_federativa varchar, fase varchar, avance_fisico double, estatus_operacion varchar,
            aprobado double, ppef double, pef double, modificado double, ejercido double,
            monto_total_inversion double
        )
        """
    )
    con.execute("create table dim_snapshot (snapshot_id varchar, anio integer, trimestre integer)")
    con.execute(
        """
        create table dim_ppi (
            cve_cartera varchar, version_ppi integer, vigente_desde_corte integer,
            vigente_hasta_corte integer, nombre_ppi varchar, descripcion_ur varchar,
            localizacion varchar
        )
        """
    )
    con.execute("insert into dim_snapshot values ('2019_anual', 2019, NULL)")
    con.execute(
        "insert into dim_ppi values ('OPA006', 1, 20191, 20304, 'Cualquiera', 'Cualquiera', 'Cualquiera')"
    )
    con.execute(
        """
        insert into fct_ppi_observacion values
        ('OPA006', '2019_anual', 2019.0, NULL, 19.0, -99.0, 'Salud', 'Hospitalario',
         'Campeche', NULL, 10.0, 'En ejecución', 100000.0, 100000.0, 100000.0,
         100000.0, 50000.0, 300000.0)
        """
    )
    con.close()

    publish_geojson.escribir_geojson(db, tmp_path / "salida", "v1")

    ruta = tmp_path / "salida" / "v1" / "geojson" / "ppi_2019.geojson"
    with ruta.open(encoding="utf-8") as fh:
        feature = json.load(fh)["features"][0]

    assert feature["properties"]["cve_cartera"] == "OPA006"
    assert feature["properties"]["nombre_ppi"] is None
