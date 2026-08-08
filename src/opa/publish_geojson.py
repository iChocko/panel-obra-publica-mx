"""Exportador de GeoJSON de observaciones georreferenciadas (Fase B del plan ATDT).

``fct_ppi_observacion`` ya trae latitud/longitud validadas contra el bbox de México en
Silver -- aquí solo se filtran las filas con coordenadas no nulas y se particiona por
``anio_corte`` en un FeatureCollection (RFC 7946) por archivo, como extra de este proyecto
sobre el mínimo tabular exigido por los Lineamientos de la ATDT.

Enriquecido con ``dim_ppi`` (nivel "Básico + montos ampliados" del plan, 2026-08-08):
``fct_ppi_observacion`` no trae el nombre del proyecto ni su ubicación textual -- esos
atributos viven en el SCD2 de ``dim_ppi`` porque cambian raro (ver dim_ppi.sql). El join usa
``vigente_desde_corte``/``vigente_hasta_corte`` (rango de ``orden_corte`` = año*10+trimestre)
para tomar la versión de ``dim_ppi`` vigente en el corte exacto de cada observación -- un
join directo por ``cve_cartera`` solo traería la última versión, no la que corresponde
históricamente a esa observación. Es LEFT JOIN a propósito: un snapshot anual genérico
(``dim_snapshot.trimestre`` nulo) no tiene ``orden_corte`` y por diseño no calza con ningún
rango de ``dim_ppi`` -- sus puntos se siguen publicando, solo sin nombre/ubicación textual.
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
    "anio_corte",
    "trimestre_corte",
    "nombre_ppi",
    "descripcion_ur",
    "localizacion",
    "descripcion_ramo",
    "descripcion_tipo_ppi",
    "entidad_federativa",
    "fase",
    "avance_fisico",
    "estatus_operacion",
    "aprobado",
    "ppef",
    "pef",
    "modificado",
    "ejercido",
    "monto_total_inversion",
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
        return con.execute(
            """
            select
                o.cve_cartera,
                o.snapshot_id,
                o.anio_corte,
                o.trimestre_corte,
                p.nombre_ppi,
                p.descripcion_ur,
                p.localizacion,
                o.descripcion_ramo,
                o.descripcion_tipo_ppi,
                o.entidad_federativa,
                o.fase,
                o.avance_fisico,
                o.estatus_operacion,
                o.aprobado,
                o.ppef,
                o.pef,
                o.modificado,
                o.ejercido,
                o.monto_total_inversion,
                o.latitud,
                o.longitud
            from fct_ppi_observacion o
            join dim_snapshot s on s.snapshot_id = o.snapshot_id
            left join dim_ppi p
                on p.cve_cartera = o.cve_cartera
                and s.anio * 10 + s.trimestre between p.vigente_desde_corte and p.vigente_hasta_corte
            where o.latitud is not null and o.longitud is not null
            order by o.cve_cartera, o.snapshot_id
            """
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


NOMBRE_CONSOLIDADO = "ppi_consolidado.geojson"


def _escribir_coleccion(ruta: Path, filas: pd.DataFrame) -> None:
    coleccion = {
        "type": "FeatureCollection",
        "features": [_feature(fila) for _, fila in filas.iterrows()],
    }
    with ruta.open("w", encoding="utf-8") as fh:
        json.dump(coleccion, fh, ensure_ascii=False, allow_nan=False)


def escribir_geojson(ruta_duckdb: Path, dir_salida: Path, version: str) -> list[Path]:
    """Exporta fct_ppi_observacion (enriquecido con dim_ppi) a GeoJSON: un FeatureCollection
    por año de corte MÁS uno consolidado (todas las observaciones georreferenciadas juntas,
    mismo grano e igual orden que la unión de los archivos por año -- ver
    ``ppi_consolidado.geojson``, útil para quien quiere cargar el panel completo en un solo
    archivo, ej. en QGIS/Leaflet, sin unir 13 archivos a mano). Ver el docstring del módulo
    para el criterio del join histórico."""
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
        ruta = dir_geojson / nombre_archivo
        _escribir_coleccion(ruta, sub)
        escritas.append(ruta)

    ruta_consolidado = dir_geojson / NOMBRE_CONSOLIDADO
    _escribir_coleccion(ruta_consolidado, df)
    escritas.append(ruta_consolidado)

    return escritas
