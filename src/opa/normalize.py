"""Bronze -> Silver: normaliza snapshots crudos a parquet con esquema unificado.

Ver ARQUITECTURA-panel-obra-publica-mx.md sección 4.2 (qué hace Silver) y 5.3 (qué hacer
cuando aparece un esquema no visto -- fallar ruidoso, no adivinar), conf/schema_map.yml
(el mapeo columna por columna) y src/opa/contracts.py (el contrato Pandera de salida).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
import pandera.errors
import yaml
from rich.console import Console

from opa.contracts import OPASnapshot, limpiar_cve_cartera
from opa.manifest import RegistroManifiesto, cargar_manifiesto

console = Console()

RUTA_SCHEMA_MAP = Path("conf/schema_map.yml")
RUTA_MANIFEST_JSONL = Path("data/manifest.jsonl")
DIR_BRONZE = Path("data/bronze")
DIR_SILVER = Path("data/silver")
RUTA_REPORTE_CALIDAD = Path("reports/calidad_silver.md")

# "Montos a decimal ... coordenadas a float64" (arquitectura 4.2) -- todas las columnas
# canónicas semánticamente numéricas que aparecen en algún esquema real (ver
# columnas_canonicas en conf/schema_map.yml). Las que no existan en un esquema dado
# simplemente se saltan, no es un error.
COLUMNAS_NUMERICAS = frozenset(
    {
        "anio",
        "id_ramo",
        "id_ur",
        "id_entidad_federativa",
        "id_ppi",
        "anios_he",
        "ppef",
        "pef",
        "aprobado",
        "modificado",
        "ejercido",
        "avance_fisico",
        "monto_total_inversion",
        "monto_operacion_mantenimiento",
        "otros_costos",
        "costo_total_inversion",
        "fiscal",
        "propio",
        "estatal",
        "municipal",
        "privada",
        "fideicomiso",
        "otros",
        "latitud",
        "longitud",
        "monto_asignacion_actual",
        "total_gasto_operacion_he",
        "total_gasto_no_considerado",
        "aprobado_pef_2017",
    }
)

# Todas de precisión de MES, nunca de día real -- confirmado sobre datos reales: incluso el
# formato moderno DD/MM/YYYY siempre trae "01" como día (verificado sobre 2021 completo).
COLUMNAS_FECHA = frozenset(
    {"fecha_inicio_cal_ff", "fecha_fin_cal_ff", "fecha_inicio_cal_fiscal", "fecha_fin_cal_fiscal"}
)

# Columnas que el contrato Pandera exige (ver OPASnapshot) pero que algunos esquemas viejos
# no tenían -- se agregan vacías antes de validar, nunca se inventan valores.
COLUMNAS_REQUERIDAS_POR_CONTRATO = (
    "cve_cartera", "anio", "avance_fisico", "latitud", "longitud", "monto_total_inversion",
)

_MESES_ES = {
    "ene": 1, "enero": 1,
    "feb": 2, "febrero": 2,
    "mar": 3, "marzo": 3,
    "abr": 4, "abril": 4,
    "may": 5, "mayo": 5,
    "jun": 6, "junio": 6,
    "jul": 7, "julio": 7,
    "ago": 8, "agosto": 8,
    "sep": 9, "septiembre": 9,
    "oct": 10, "octubre": 10,
    "nov": 11, "noviembre": 11,
    "dic": 12, "diciembre": 12,
}

_RE_ISO = re.compile(r"^(\d{4})-(\d{1,2})-\d{1,2}")
_RE_DMY = re.compile(r"^\d{1,2}/(\d{1,2})/(\d{4})$")
_RE_MES_ABREV_ANIO2 = re.compile(r"^([a-záéíóúñ]{3})-(\d{2})$")
_RE_MES_COMPLETO_ANIO4 = re.compile(r"^([a-záéíóúñ]+)/(\d{4})$")


class EsquemaDesconocidoError(Exception):
    """header_hash no está en conf/schema_map.yml -- fallar ruidoso, no adivinar (sección 5.3)."""


def parsear_fecha_mes(valor: Any) -> pd.Timestamp | None:
    """Parsea las 4 formas reales encontradas en el corpus bronze (2015-2026) a un
    ``pd.Timestamp`` con día fijo en 1 -- ninguna de las 4 tiene precisión real de día:

    - ``2003-01-01 00:00:00`` -- xlsx con fecha nativa de Excel leída como texto (2018 T3).
    - ``01/12/2002`` (DD/MM/YYYY) -- esquema moderno (2019-2026); el "DD" es siempre "01"
      en los datos reales, confirmado sobre 2021 completo.
    - ``mar-06`` (mes abreviado en español + año de 2 dígitos) -- 2016.
    - ``Enero/2001`` (mes completo en español + año de 4 dígitos) -- 2015, 2017, 2018.

    Un valor que no matchea ninguna de las 4 formas devuelve ``None`` -- no se adivina un
    quinto formato. El llamador (``normalizar_snapshot``) cuenta cuántos ``None`` produce
    esta función contra cuántos valores no nulos había, para reportarlo como calidad de
    datos en vez de dejarlo pasar en silencio.
    """
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None
    texto = str(valor).strip()
    if not texto or texto.lower() in ("nan", "nat", "none"):
        return None

    m = _RE_ISO.match(texto)
    if m:
        return pd.Timestamp(year=int(m.group(1)), month=int(m.group(2)), day=1)

    m = _RE_DMY.match(texto)
    if m:
        return pd.Timestamp(year=int(m.group(2)), month=int(m.group(1)), day=1)

    m = _RE_MES_ABREV_ANIO2.match(texto.lower())
    if m and m.group(1) in _MESES_ES:
        anio2 = int(m.group(2))
        anio = 2000 + anio2 if anio2 < 70 else 1900 + anio2  # sin datos anteriores a 1970 esperados
        return pd.Timestamp(year=anio, month=_MESES_ES[m.group(1)], day=1)

    m = _RE_MES_COMPLETO_ANIO4.match(texto.lower())
    if m and m.group(1) in _MESES_ES:
        return pd.Timestamp(year=int(m.group(2)), month=_MESES_ES[m.group(1)], day=1)

    return None


def cargar_schema_map(ruta: Path = RUTA_SCHEMA_MAP) -> dict[str, Any]:
    with ruta.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _leer_bronze(ruta: Path, ext: str, encoding: str | None) -> pd.DataFrame:
    if ext == "csv":
        return pd.read_csv(ruta, dtype=str, encoding=encoding or "latin-1", engine="python", sep=None)
    if ext == "xlsx":
        return pd.read_excel(ruta, dtype=str)
    raise ValueError(f"extensión no soportada para normalizar: {ext}")


@dataclass
class ResultadoNormalizacion:
    """Qué pasó al intentar normalizar un snapshot -- éxito o fallo, nunca silencioso."""

    snapshot_id: str
    archivo_bronze: str
    estado: str  # "ok" | "esquema_desconocido" | "corrupto_conocido" | "error"
    filas_totales: int = 0
    filas_validas: int = 0
    filas_rechazadas: int = 0
    motivos_rechazo: dict[str, int] = field(default_factory=dict)
    fechas_no_parseadas: int = 0
    detalle_error: str | None = None
    ruta_parquet: Path | None = None


def _validar_con_cuarentena(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Valida contra OPASnapshot; separa filas que fallan (cuarentena) de las válidas.

    Un snapshot con algunas filas basura reales (ver cve_cartera centinela / basura de
    coordenadas en src/opa/contracts.py) no se descarta completo por eso -- pero las filas
    rechazadas tampoco se cuelan en silencio: se cuentan por tipo de motivo y se excluyen
    del parquet final.
    """
    try:
        OPASnapshot.validate(df, lazy=True)
        return df, {}
    except pandera.errors.SchemaErrors as exc:
        fallas = exc.failure_cases
        indices_malos = {int(i) for i in fallas["index"].dropna()}
        motivos = fallas["check"].value_counts().to_dict()
        validas = df.loc[~df.index.isin(indices_malos)]
        return validas, motivos


def normalizar_snapshot(
    registro: RegistroManifiesto,
    schema_map: dict[str, Any],
    dir_bronze: Path = DIR_BRONZE,
    dir_silver: Path = DIR_SILVER,
) -> ResultadoNormalizacion:
    """Normaliza un snapshot bronze a parquet canónico, o reporta con precisión por qué no."""
    corruptos = {c["archivo_bronze"] for c in schema_map.get("snapshots_conocidos_corruptos", [])}
    if registro.archivo_bronze in corruptos:
        return ResultadoNormalizacion(registro.snapshot_id, registro.archivo_bronze, "corrupto_conocido")

    esquemas = schema_map["esquemas"]
    if registro.header_hash not in esquemas:
        return ResultadoNormalizacion(registro.snapshot_id, registro.archivo_bronze, "esquema_desconocido")

    esquema = esquemas[registro.header_hash]
    ruta = dir_bronze / registro.archivo_bronze
    if not ruta.exists():
        return ResultadoNormalizacion(
            registro.snapshot_id, registro.archivo_bronze, "error",
            detalle_error=f"no existe {ruta} -- correr 'uv run opa bronze' primero",
        )

    ext = registro.archivo_bronze.rsplit(".", 1)[-1]
    try:
        df = _leer_bronze(ruta, ext, registro.encoding_detectado)
    except (pd.errors.ParserError, UnicodeDecodeError, ValueError) as exc:
        return ResultadoNormalizacion(
            registro.snapshot_id, registro.archivo_bronze, "error", detalle_error=f"{type(exc).__name__}: {exc}"
        )

    filas_totales = len(df)
    df = df.rename(columns=esquema["columnas"])

    for col in COLUMNAS_REQUERIDAS_POR_CONTRATO:
        if col not in df.columns:
            df[col] = pd.NA

    df["cve_cartera"] = df["cve_cartera"].map(lambda v: limpiar_cve_cartera(v) if pd.notna(v) else v)

    fechas_no_parseadas = 0
    for col in COLUMNAS_FECHA:
        if col in df.columns:
            antes = int(df[col].notna().sum())
            df[col] = df[col].map(parsear_fecha_mes)
            despues = int(df[col].notna().sum())
            fechas_no_parseadas += antes - despues

    for col in COLUMNAS_NUMERICAS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", "").str.strip(), errors="coerce")

    for col in ("latitud", "longitud"):
        if col in df.columns:
            # "0" es un centinela real de "sin coordenadas" en el esquema viejo (2015-2018):
            # 48.6% de LATITUD_INICIAL en 2015 es literalmente 0 (verificado), y (0°N, 0°E) es
            # geográficamente imposible en México de cualquier forma -- no es basura a rechazar,
            # es ausencia de dato mal codificada. El esquema moderno no usa esta convención (0
            # apariciones en LATITUD 2021, verificado), pero tratarlo igual ahí es inofensivo.
            df.loc[df[col] == 0, col] = pd.NA

    df["snapshot_id"] = registro.snapshot_id

    validas, motivos = _validar_con_cuarentena(df)

    resultado = ResultadoNormalizacion(
        snapshot_id=registro.snapshot_id,
        archivo_bronze=registro.archivo_bronze,
        estado="ok",
        filas_totales=filas_totales,
        filas_validas=len(validas),
        filas_rechazadas=filas_totales - len(validas),
        motivos_rechazo=motivos,
        fechas_no_parseadas=fechas_no_parseadas,
    )

    dir_silver.mkdir(parents=True, exist_ok=True)
    ruta_parquet = dir_silver / f"{registro.snapshot_id}.parquet"
    validas.to_parquet(ruta_parquet, index=False)
    resultado.ruta_parquet = ruta_parquet
    return resultado


def ejecutar_normalizacion(
    ruta_manifest: Path = RUTA_MANIFEST_JSONL,
    ruta_schema_map: Path = RUTA_SCHEMA_MAP,
    dir_bronze: Path = DIR_BRONZE,
    dir_silver: Path = DIR_SILVER,
) -> list[ResultadoNormalizacion]:
    """Normaliza todos los snapshots del manifiesto con corte declarado (año no nulo).

    Los renglones sin año (auxiliares: diccionarios, catálogos, Pidiregas, Tomo VIII, APP,
    el manifiesto JSON del portal) son otros datasets -- fuera de alcance de Silver por
    ahora, no se tocan aquí.

    El manifiesto puede tener más de un renglón con el mismo snapshot_id -- el mismo
    contenido (mismo sha256) descubierto por más de una fuente (ej. vivo y Wayback a la vez,
    caso real: Proyectos_OPA.csv de 2015). Es procedencia legítima y se queda tal cual en
    data/manifest.jsonl, pero normalizar el mismo contenido dos veces no aporta nada y
    duplica las filas en el reporte de calidad -- se deduplica aquí, no en el manifiesto.
    """
    schema_map = cargar_schema_map(ruta_schema_map)
    registros = cargar_manifiesto(ruta_manifest)
    vistos: set[str] = set()
    resultados = []
    for r in registros:
        if r.corte_declarado.get("anio") is None:
            continue
        if r.snapshot_id in vistos:
            continue
        vistos.add(r.snapshot_id)
        resultados.append(normalizar_snapshot(r, schema_map, dir_bronze, dir_silver))
    return resultados


def generar_reporte_calidad(resultados: list[ResultadoNormalizacion]) -> str:
    """Renderiza ``reports/calidad_silver.md`` -- cada snapshot, su estado, y por qué."""
    ok = [r for r in resultados if r.estado == "ok"]
    corruptos = [r for r in resultados if r.estado == "corrupto_conocido"]
    desconocidos = [r for r in resultados if r.estado == "esquema_desconocido"]
    errores = [r for r in resultados if r.estado == "error"]

    total_filas = sum(r.filas_totales for r in ok)
    total_validas = sum(r.filas_validas for r in ok)
    total_rechazadas = sum(r.filas_rechazadas for r in ok)

    lineas: list[str] = []
    lineas.append("# Reporte de calidad -- Bronze a Silver")
    lineas.append("")
    lineas.append(f"*Generado por `opa normalize`. {len(resultados)} snapshots con corte declarado en el manifiesto.*")
    lineas.append("")
    lineas.append("## Resumen")
    lineas.append("")
    lineas.append(f"- Normalizados a parquet: **{len(ok)}**")
    lineas.append(f"- Omitidos por corrupción conocida en la fuente: **{len(corruptos)}**")
    lineas.append(f"- Con esquema desconocido (no en `conf/schema_map.yml`): **{len(desconocidos)}**")
    lineas.append(f"- Con error de lectura: **{len(errores)}**")
    lineas.append("")
    lineas.append(f"- Filas totales procesadas: {total_filas:,}")
    lineas.append(
        f"- Filas válidas escritas a parquet: {total_validas:,} "
        f"({total_validas / total_filas * 100:.1f}%)" if total_filas else "- Filas válidas: 0"
    )
    lineas.append(f"- Filas en cuarentena (fallan el contrato Pandera, no se escriben): {total_rechazadas:,}")
    lineas.append("")

    if desconocidos:
        lineas.append("## ⚠️ Esquemas desconocidos -- requieren mapear en conf/schema_map.yml")
        lineas.append("")
        lineas.append(
            "Por diseño (arquitectura sección 5.3) estos snapshots NO se normalizan hasta que "
            "alguien revise sus columnas y agregue una entrada a `esquemas:` -- no se adivina el mapeo."
        )
        lineas.append("")
        for r in desconocidos:
            lineas.append(f"- `{r.archivo_bronze}`")
        lineas.append("")

    if errores:
        lineas.append("## ⚠️ Errores de lectura")
        lineas.append("")
        for r in errores:
            lineas.append(f"- `{r.archivo_bronze}`: {r.detalle_error}")
        lineas.append("")

    if corruptos:
        lineas.append("## Omitidos por corrupción conocida en la fuente")
        lineas.append("")
        lineas.append("Ver `conf/schema_map.yml` (`snapshots_conocidos_corruptos`) para el detalle de cada uno.")
        lineas.append("")
        for r in corruptos:
            lineas.append(f"- `{r.archivo_bronze}`")
        lineas.append("")

    lineas.append("## Detalle por snapshot normalizado")
    lineas.append("")
    lineas.append("| snapshot_id | archivo | filas | válidas | rechazadas | fechas sin parsear |")
    lineas.append("|---|---|---|---|---|---|")
    for r in sorted(ok, key=lambda r: r.snapshot_id):
        lineas.append(
            f"| {r.snapshot_id} | `{r.archivo_bronze}` | {r.filas_totales} | {r.filas_validas} | "
            f"{r.filas_rechazadas} | {r.fechas_no_parseadas} |"
        )
    lineas.append("")

    con_rechazos = [r for r in ok if r.motivos_rechazo]
    if con_rechazos:
        lineas.append("## Motivos de rechazo (filas en cuarentena)")
        lineas.append("")
        for r in con_rechazos:
            lineas.append(f"- `{r.archivo_bronze}`: " + ", ".join(f"{k} ({v})" for k, v in r.motivos_rechazo.items()))
        lineas.append("")

    return "\n".join(lineas) + "\n"
