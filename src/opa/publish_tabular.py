"""Exportador de distribuciones tabulares abiertas (Fase B del plan de alineación ATDT).

Materializa las 8 tablas publicables de la capa Gold (data/gold/panel_opa.duckdb) a CSV
(RFC 4180) y Parquet, los formatos mínimos que exigen los Lineamientos de la ATDT para datos
abiertos (docs/normativa/2025-09-11_ATDT_Lineamientos-Datos-Abiertos-APF.md, Art. 38).

Misma filosofía que diccionario.py: la deriva entre lo esperado y lo real (tabla faltante) es
un error, no una advertencia -- nunca se publica una distribución incompleta en silencio.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

TABLAS_ORDEN_ESTABLE: dict[str, list[str]] = {
    "dim_snapshot": ["snapshot_id"],
    "dim_ramo": ["id_ramo"],
    "dim_entidad": ["id_entidad_federativa"],
    "dim_tipo_ppi": ["id_tipo_ppi"],
    "dim_ppi": ["cve_cartera", "version_ppi"],
    "fct_ppi_observacion": ["cve_cartera", "snapshot_id"],
    "fct_ppi_delta": ["cve_cartera", "snapshot_id"],
    "fct_ppi_ciclo_vida": ["cve_cartera"],
}


class ErrorPublicacion(RuntimeError):
    """Faltan tablas publicables en el duckdb de origen."""


def _leer_tablas(ruta_duckdb: Path) -> dict[str, pd.DataFrame]:
    import duckdb  # import local: el CLI de Fase 0 no necesita duckdb instalado

    con = duckdb.connect(str(ruta_duckdb), read_only=True)
    try:
        tablas_existentes = {
            fila[0] for fila in con.execute("show tables").fetchall()
        }
        faltantes = sorted(set(TABLAS_ORDEN_ESTABLE) - tablas_existentes)
        if faltantes:
            raise ErrorPublicacion(
                f"Faltan {len(faltantes)} tabla(s) publicable(s) en {ruta_duckdb}: "
                f"{', '.join(faltantes)}"
            )

        return {
            tabla: con.execute(f"select * from {tabla}").fetchdf()
            for tabla in TABLAS_ORDEN_ESTABLE
        }
    finally:
        con.close()


def escribir_tabulares(ruta_duckdb: Path, dir_salida: Path, version: str) -> list[Path]:
    """Exporta las 8 tablas publicables de Gold a CSV + Parquet. Regresa las rutas escritas."""
    tablas = _leer_tablas(ruta_duckdb)

    dir_tabular = dir_salida / version / "tabular"
    dir_tabular.mkdir(parents=True, exist_ok=True)

    escritas: list[Path] = []
    for tabla, columnas_orden in TABLAS_ORDEN_ESTABLE.items():
        df = tablas[tabla].sort_values(by=columnas_orden, kind="stable").reset_index(drop=True)

        ruta_csv = dir_tabular / f"{tabla}.csv"
        # RFC 4180 exige CRLF; pandas usa "\n" por default (rompería el "RFC 4180" que
        # promete el docstring del módulo y quedaría inconsistente con diccionario.py,
        # que sí usa CRLF vía csv.writer).
        df.to_csv(ruta_csv, index=False, lineterminator="\r\n")
        escritas.append(ruta_csv)

        ruta_parquet = dir_tabular / f"{tabla}.parquet"
        df.to_parquet(ruta_parquet, engine="pyarrow", index=False)
        escritas.append(ruta_parquet)

    return escritas
