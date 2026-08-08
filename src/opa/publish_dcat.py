"""Generador de catalog.json (DCAT, JSON-LD) para el paquete publicado (Fase C del plan ATDT).

Describe las distribuciones YA ESCRITAS por ``opa publish`` (Fase B) en
``dir_paquete/tabular/`` y ``dir_paquete/geojson/`` usando el vocabulario DCAT estándar (W3C,
namespaces dcat:/dct:/foaf:), como exige el Art. 3-XIV de los Lineamientos (ver
docs/normativa/2025-09-11_ATDT_Lineamientos-Datos-Abiertos-APF.md). Los resúmenes de
procedencia y calidad de ESTE repo no son vocabulario DCAT oficial -- viajan bajo las claves
"x-procedencia"/"x-calidad", documentadas como extensión del repo (ver Art. 3-XXII y sección 3,
Fase C de docs/PLAN-alineacion-gold-lineamientos-ATDT.md).
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from opa.dcat_config import cargar_dcat_config
from opa.dcat_procedencia import resumen_calidad, resumen_procedencia
from opa.diccionario import cargar_descripciones_de_tablas

TAMANO_CHUNK = 65536

_MEDIA_TYPE_POR_EXTENSION = {
    ".csv": "text/csv",
    ".parquet": "application/vnd.apache.parquet",
    ".geojson": "application/geo+json",
}

_CONTEXT = {
    "dcat": "http://www.w3.org/ns/dcat#",
    "dct": "http://purl.org/dc/terms/",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "spdx": "http://spdx.org/rdf/terms#",
}

_NOTA_EXTENSION = (
    "x-procedencia y x-calidad son una extensión de este repositorio, no vocabulario DCAT "
    "oficial, mientras el Manual Operativo de la ATDT no defina un perfil mexicano."
)

_NOMBRE_TABLA_GEOJSON = "fct_ppi_observacion"


class ErrorCatalogo(RuntimeError):
    """dir_paquete/tabular/ falta, está vacía, o cualquier otro insumo del catálogo es inválido."""


def _sha256_archivo(ruta: Path) -> str:
    hasher = hashlib.sha256()
    with ruta.open("rb") as fh:
        for bloque in iter(lambda: fh.read(TAMANO_CHUNK), b""):
            hasher.update(bloque)
    return hasher.hexdigest()


def _distribucion(ruta_archivo: Path, dir_paquete: Path) -> dict:
    extension = ruta_archivo.suffix
    if extension not in _MEDIA_TYPE_POR_EXTENSION:
        raise ErrorCatalogo(
            f"Extensión de distribución desconocida: {ruta_archivo} "
            f"(soportadas: {', '.join(sorted(_MEDIA_TYPE_POR_EXTENSION))})"
        )
    return {
        "@type": "dcat:Distribution",
        "dcat:mediaType": _MEDIA_TYPE_POR_EXTENSION[extension],
        "dcat:downloadURL": ruta_archivo.relative_to(dir_paquete).as_posix(),
        "dcat:byteSize": os.path.getsize(ruta_archivo),
        "dct:checksum": {
            "@type": "spdx:Checksum",
            "spdx:algorithm": "spdx:checksumAlgorithm_sha256",
            "spdx:checksumValue": _sha256_archivo(ruta_archivo),
        },
    }


def _distribuciones_tabulares_por_tabla(dir_tabular: Path, dir_paquete: Path) -> dict[str, list[dict]]:
    # Sin filtrar por sufijo aquí a propósito: cualquier archivo con extensión no reconocida
    # debe reventar en _distribucion (falla ruidoso), no desaparecer en silencio del catálogo.
    archivos = sorted(p for p in dir_tabular.iterdir() if p.is_file())
    if not archivos:
        raise ErrorCatalogo(f"dir_paquete/tabular/ no tiene ningún .csv o .parquet: {dir_tabular}")

    por_tabla: dict[str, list[dict]] = {}
    for archivo in archivos:
        por_tabla.setdefault(archivo.stem, []).append(_distribucion(archivo, dir_paquete))
    return por_tabla


def _distribuciones_geojson(dir_geojson: Path, dir_paquete: Path) -> list[dict]:
    if not dir_geojson.is_dir():
        return []
    # Misma razón que en _distribuciones_tabulares_por_tabla: no filtrar por sufijo aquí.
    archivos = sorted(p for p in dir_geojson.iterdir() if p.is_file())
    return [_distribucion(archivo, dir_paquete) for archivo in archivos]


def escribir_catalogo(
    dir_paquete: Path,
    ruta_dcat_yml: Path,
    ruta_schema_yml: Path,
    ruta_manifest: Path,
    ruta_calidad_silver: Path,
) -> Path:
    """Genera ``dir_paquete/catalog.json`` (DCAT, JSON-LD) sobre lo ya escrito por ``opa publish``."""
    config = cargar_dcat_config(ruta_dcat_yml)
    catalogo = config["catalogo"]
    descripciones = cargar_descripciones_de_tablas(ruta_schema_yml)
    procedencia = resumen_procedencia(ruta_manifest)
    calidad = resumen_calidad(ruta_calidad_silver)

    dir_tabular = dir_paquete / "tabular"
    if not dir_tabular.is_dir():
        raise ErrorCatalogo(f"dir_paquete/tabular/ no existe: {dir_tabular}")

    distribuciones_por_tabla = _distribuciones_tabulares_por_tabla(dir_tabular, dir_paquete)
    distribuciones_geojson = _distribuciones_geojson(dir_paquete / "geojson", dir_paquete)
    if distribuciones_geojson:
        distribuciones_por_tabla.setdefault(_NOMBRE_TABLA_GEOJSON, [])
        distribuciones_por_tabla[_NOMBRE_TABLA_GEOJSON].extend(distribuciones_geojson)

    datasets = [
        {
            "@type": "dcat:Dataset",
            "@id": f"#{nombre_tabla}",
            "dct:title": nombre_tabla,
            "dct:description": descripciones.get(nombre_tabla, ""),
            "dcat:distribution": distribuciones_por_tabla[nombre_tabla],
        }
        for nombre_tabla in sorted(distribuciones_por_tabla)
    ]

    documento = {
        "@context": _CONTEXT,
        "@type": "dcat:Catalog",
        "dct:title": catalogo["titulo"],
        "dct:description": catalogo["descripcion"],
        "dct:license": {
            "dct:title": catalogo["licencia"]["nombre"],
            "foaf:homepage": catalogo["licencia"]["url"],
        },
        "dcat:theme": catalogo.get("temas", []),
        "dct:accrualPeriodicity": catalogo["cadencia"]["valor"],
        "dcat:dataset": datasets,
        "x-procedencia": procedencia,
        "x-calidad": calidad,
        "x-nota": _NOTA_EXTENSION,
    }

    ruta_catalog = dir_paquete / "catalog.json"
    with ruta_catalog.open("w", encoding="utf-8") as fh:
        json.dump(documento, fh, ensure_ascii=False, indent=2, allow_nan=False)
    return ruta_catalog
