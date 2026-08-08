"""Exportador de GeoJSON de observaciones georreferenciadas (Fase B del plan ATDT).

``fct_ppi_observacion`` ya trae latitud/longitud validadas contra el bbox de México en
Silver -- aquí solo se filtran las filas con coordenadas no nulas y se particiona por
``anio_corte`` en un FeatureCollection (RFC 7946) por archivo, como extra de este proyecto
sobre el mínimo tabular exigido por los Lineamientos de la ATDT.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

COLUMNAS_PROPIEDADES = [
    "cve_cartera",
    "snapshot_id",
    "descripcion_ramo",
    "descripcion_tipo_ppi",
    "entidad_federativa",
    "avance_fisico",
    "estatus_operacion",
    "modificado",
    "ejercido",
    "monto_total_inversion",
]

COLUMNAS_CONSULTA = [
    "cve_cartera",
    "snapshot_id",
    "anio_corte",
    "latitud",
    "longitud",
    *COLUMNAS_PROPIEDADES[2:],
]


def _valor_json(valor: Any) -> Any:
    if pd.isna(valor):
        return None
    if hasattr(valor, "item"):
        # numpy int64/float64 que trae pandas -- json no los serializa sin convertir.
        return valor.item()
    return valor


def _leer_observaciones_georreferenciadas(ruta_duckdb: Path) -> pd.DataFrame:
    con = duckdb.connect(str(ruta_duckdb), read_only=True)
    try:
        columnas = ", ".join(COLUMNAS_CONSULTA)
        return con.execute(
            f"select {columnas} from fct_ppi_observacion "
            "where latitud is not null and longitud is not null "
            "order by cve_cartera, snapshot_id"
        ).df()
    finally:
        con.close()


def _nombre_grupo(anio_corte: Any) -> str:
    if pd.isna(anio_corte):
        return "sin_anio"
    return str(int(anio_corte))


def _feature(fila: pd.Series) -> dict[str, Any]:
    propiedades = {campo: _valor_json(fila[campo]) for campo in COLUMNAS_PROPIEDADES}
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [_valor_json(fila["longitud"]), _valor_json(fila["latitud"])],
        },
        "properties": propiedades,
    }


def escribir_geojson(ruta_duckdb: Path, dir_salida: Path, version: str) -> list[Path]:
    """Exporta fct_ppi_observacion a GeoJSON, un FeatureCollection por año de corte."""
    df = _leer_observaciones_georreferenciadas(ruta_duckdb)

    dir_geojson = dir_salida / version / "geojson"
    dir_geojson.mkdir(parents=True, exist_ok=True)

    if df.empty:
        return []

    df = df.assign(_grupo=df["anio_corte"].map(_nombre_grupo))

    escritas: list[Path] = []
    for grupo in sorted(df["_grupo"].unique()):
        sub = df[df["_grupo"] == grupo]
        nombre_archivo = "ppi_sin_anio.geojson" if grupo == "sin_anio" else f"ppi_{grupo}.geojson"
        coleccion = {
            "type": "FeatureCollection",
            "features": [_feature(fila) for _, fila in sub.iterrows()],
        }
        ruta = dir_geojson / nombre_archivo
        with ruta.open("w", encoding="utf-8") as fh:
            json.dump(coleccion, fh, ensure_ascii=False, allow_nan=False)
        escritas.append(ruta)

    return escritas
