"""Tests del exportador de distribuciones tabulares (Fase B del plan de alineación ATDT).

Construye un duckdb MÍNIMO en tmp_path con las 8 tablas publicables -- no depende del
duckdb real del repo (que no existe en CI). Cubre el caso feliz, el determinismo byte a
byte (requisito duro del plan) y la falla ruidosa ante una tabla faltante.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import pytest

from opa import publish_tabular


def _crear_duckdb(ruta: Path) -> None:
    con = duckdb.connect(str(ruta))

    dim_snapshot = pd.DataFrame(
        {
            "snapshot_id": ["2021Q3_aaa", "2020Q1_bbb", "2021Q1_ccc"],
            "anio": [2021, 2020, 2021],
        }
    )
    dim_ramo = pd.DataFrame(
        {"id_ramo": [9, 11, 4], "nombre_ramo": ["Comunicaciones", "Educación", "Gobernación"]}
    )
    dim_entidad = pd.DataFrame(
        {"id_entidad_federativa": [4, 1, 24], "nombre_entidad": ["Campeche", "Aguascalientes", "SLP"]}
    )
    dim_tipo_ppi = pd.DataFrame({"id_tipo_ppi": [3, 1, 2], "nombre_tipo_ppi": ["C", "A", "B"]})
    dim_ppi = pd.DataFrame(
        {
            "cve_cartera": ["1020900001", "1020900001", "0912400002"],
            "version_ppi": [2, 1, 1],
            "id_ramo": [9, 9, 9],
        }
    )
    fct_ppi_observacion = pd.DataFrame(
        {
            "cve_cartera": ["1020900001", "0912400002", "1020900001"],
            "snapshot_id": ["2021Q1_ccc", "2020Q1_bbb", "2020Q1_bbb"],
            "monto_total": [100.0, 200.0, 150.0],
        }
    )
    fct_ppi_delta = pd.DataFrame(
        {
            "cve_cartera": ["1020900001", "0912400002", "1020900001"],
            "snapshot_id": ["2021Q1_ccc", "2020Q1_bbb", "2020Q1_bbb"],
            "delta_monto": [10.0, 20.0, 15.0],
        }
    )
    fct_ppi_ciclo_vida = pd.DataFrame(
        {
            "cve_cartera": ["1020900001", "0912400002"],
            "dias_en_cartera": [365, 90],
        }
    )

    for nombre, df in [  # noqa: B007 -- duckdb resuelve "df" por nombre de variable local en el SQL
        ("dim_snapshot", dim_snapshot),
        ("dim_ramo", dim_ramo),
        ("dim_entidad", dim_entidad),
        ("dim_tipo_ppi", dim_tipo_ppi),
        ("dim_ppi", dim_ppi),
        ("fct_ppi_observacion", fct_ppi_observacion),
        ("fct_ppi_delta", fct_ppi_delta),
        ("fct_ppi_ciclo_vida", fct_ppi_ciclo_vida),
    ]:
        con.execute(f"create table {nombre} as select * from df")

    con.close()


def test_caso_feliz_escribe_16_archivos_csv_y_parquet_coinciden(tmp_path: Path) -> None:
    db = tmp_path / "gold.duckdb"
    _crear_duckdb(db)

    escritas = publish_tabular.escribir_tabulares(db, tmp_path / "salida", "v1")

    assert len(escritas) == 16
    for ruta in escritas:
        assert ruta.exists()

    dir_tabular = tmp_path / "salida" / "v1" / "tabular"
    for tabla in publish_tabular.TABLAS_ORDEN_ESTABLE:
        ruta_csv = dir_tabular / f"{tabla}.csv"
        ruta_parquet = dir_tabular / f"{tabla}.parquet"
        assert ruta_csv in escritas
        assert ruta_parquet in escritas

        df_csv = pd.read_csv(ruta_csv)
        df_parquet = pd.read_parquet(ruta_parquet)
        assert list(df_csv.columns) == list(df_parquet.columns)
        assert df_csv.shape == df_parquet.shape

    encabezado = (dir_tabular / "dim_ramo.csv").read_text(encoding="utf-8").splitlines()[0]
    assert encabezado == "id_ramo,nombre_ramo"


def test_orden_es_deterministico_por_las_columnas_declaradas(tmp_path: Path) -> None:
    db = tmp_path / "gold.duckdb"
    _crear_duckdb(db)

    publish_tabular.escribir_tabulares(db, tmp_path / "salida", "v1")

    ruta_csv = tmp_path / "salida" / "v1" / "tabular" / "dim_ramo.csv"
    filas = ruta_csv.read_text(encoding="utf-8").splitlines()[1:]
    ids = [int(fila.split(",")[0]) for fila in filas]
    assert ids == sorted(ids)


def test_dos_corridas_producen_bytes_identicos(tmp_path: Path) -> None:
    db = tmp_path / "gold.duckdb"
    _crear_duckdb(db)

    publish_tabular.escribir_tabulares(db, tmp_path / "salida_1", "v1")
    publish_tabular.escribir_tabulares(db, tmp_path / "salida_2", "v1")

    ruta_1 = tmp_path / "salida_1" / "v1" / "tabular" / "fct_ppi_observacion.csv"
    ruta_2 = tmp_path / "salida_2" / "v1" / "tabular" / "fct_ppi_observacion.csv"
    assert ruta_1.read_bytes() == ruta_2.read_bytes()


def test_csv_usa_crlf_rfc4180(tmp_path: Path) -> None:
    db = tmp_path / "gold.duckdb"
    _crear_duckdb(db)

    publish_tabular.escribir_tabulares(db, tmp_path / "salida", "v1")

    crudo = (tmp_path / "salida" / "v1" / "tabular" / "dim_ramo.csv").read_bytes()
    assert b"\r\n" in crudo
    assert b"\n\n" not in crudo.replace(b"\r\n", b"")


def test_falla_ruidoso_si_falta_una_tabla(tmp_path: Path) -> None:
    db = tmp_path / "gold.duckdb"
    _crear_duckdb(db)

    con = duckdb.connect(str(db))
    con.execute("drop table fct_ppi_ciclo_vida")
    con.close()

    with pytest.raises(publish_tabular.ErrorPublicacion, match="fct_ppi_ciclo_vida"):
        publish_tabular.escribir_tabulares(db, tmp_path / "salida", "v1")

    assert not (tmp_path / "salida").exists()
