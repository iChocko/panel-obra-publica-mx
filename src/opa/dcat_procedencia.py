"""Resúmenes de procedencia y calidad para el catálogo DCAT (Fase C del plan ATDT).

Extrae de los insumos reales del pipeline (``data/manifest.jsonl`` y
``reports/calidad_silver.md``) los resúmenes que alimentan las extensiones ``x-procedencia``
y ``x-calidad`` de ``catalog.json`` -- nunca el vocabulario DCAT estándar en sí, ver
docs/PLAN-alineacion-gold-lineamientos-ATDT.md sección 3 (Fase C).
"""

from __future__ import annotations

import json
import re
from pathlib import Path


class ErrorProcedencia(RuntimeError):
    """Un insumo real (manifiesto o reporte de calidad) falta, está vacío o mal formado."""


def resumen_procedencia(ruta_manifest: Path) -> dict:
    """Agrega ``data/manifest.jsonl`` (un JSON por línea, un snapshot bronze por línea)."""
    if not ruta_manifest.is_file():
        raise ErrorProcedencia(f"No existe el manifiesto de procedencia: {ruta_manifest}")

    lineas = ruta_manifest.read_text(encoding="utf-8").splitlines()
    if not lineas:
        raise ErrorProcedencia(f"El manifiesto de procedencia está vacío: {ruta_manifest}")

    snapshots = []
    for numero_linea, linea in enumerate(lineas, start=1):
        try:
            snapshots.append(json.loads(linea))
        except json.JSONDecodeError as exc:
            raise ErrorProcedencia(
                f"Línea {numero_linea} de {ruta_manifest} no es JSON válido: {exc}"
            ) from exc

    por_origen: dict[str, int] = {}
    for snap in snapshots:
        origen = snap["origen"]
        por_origen[origen] = por_origen.get(origen, 0) + 1

    anios = [
        snap["corte_declarado"]["anio"]
        for snap in snapshots
        if snap["corte_declarado"]["anio"] is not None
    ]
    if not anios:
        raise ErrorProcedencia(
            f"Ningún snapshot en {ruta_manifest} tiene corte_declarado.anio -- "
            "no se puede calcular rango_anios"
        )

    return {
        "n_snapshots": len(snapshots),
        "por_origen": por_origen,
        "fecha_descarga_mas_reciente": max(snap["fecha_descarga"] for snap in snapshots),
        "bytes_totales": sum(snap["bytes"] for snap in snapshots),
        "rango_anios": [min(anios), max(anios)],
    }


_PATRONES_RESUMEN = {
    "snapshots_normalizados": r"Normalizados a parquet:\s*\*\*(\d+)\*\*",
    "snapshots_omitidos_corruptos": (
        r"Omitidos por corrupción conocida en la fuente:\s*\*\*(\d+)\*\*"
    ),
    "snapshots_esquema_desconocido": (
        r"Con esquema desconocido \(no en `conf/schema_map\.yml`\):\s*\*\*(\d+)\*\*"
    ),
    "snapshots_error_lectura": r"Con error de lectura:\s*\*\*(\d+)\*\*",
    "filas_totales": r"Filas totales procesadas:\s*([\d,]+)",
    "filas_validas_y_pct": r"Filas válidas escritas a parquet:\s*([\d,]+) \(([\d.]+)%\)",
    "filas_en_cuarentena": (
        r"Filas en cuarentena \(fallan el contrato Pandera, no se escriben\):\s*([\d,]+)"
    ),
}


def resumen_calidad(ruta_reporte: Path) -> dict:
    """Extrae la sección ``## Resumen`` de ``reports/calidad_silver.md`` por regex dirigida."""
    if not ruta_reporte.is_file():
        raise ErrorProcedencia(f"No existe el reporte de calidad: {ruta_reporte}")

    contenido = ruta_reporte.read_text(encoding="utf-8")

    valores: dict[str, str] = {}
    campos_faltantes: list[str] = []
    for campo, patron in _PATRONES_RESUMEN.items():
        coincidencia = re.search(patron, contenido)
        if coincidencia is None:
            campos_faltantes.append(campo)
            continue
        valores[campo] = coincidencia

    if campos_faltantes:
        raise ErrorProcedencia(
            f"{ruta_reporte} no tiene la sección '## Resumen' completa -- "
            f"faltan o no coinciden estos campos: {', '.join(sorted(campos_faltantes))}"
        )

    filas_validas_match = valores["filas_validas_y_pct"]

    return {
        "snapshots_normalizados": int(valores["snapshots_normalizados"].group(1)),
        "snapshots_omitidos_corruptos": int(valores["snapshots_omitidos_corruptos"].group(1)),
        "snapshots_esquema_desconocido": int(valores["snapshots_esquema_desconocido"].group(1)),
        "snapshots_error_lectura": int(valores["snapshots_error_lectura"].group(1)),
        "filas_totales": int(valores["filas_totales"].group(1).replace(",", "")),
        "filas_validas": int(filas_validas_match.group(1).replace(",", "")),
        "pct_filas_validas": float(filas_validas_match.group(2)),
        "filas_en_cuarentena": int(valores["filas_en_cuarentena"].group(1).replace(",", "")),
    }
