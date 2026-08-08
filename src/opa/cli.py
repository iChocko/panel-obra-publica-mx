"""CLI de Fase 0: descubrimiento e inspección de muestras de datos OPA."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
import typer
from rich.console import Console

from opa import discovery, manifest
from opa import normalize as normalize_mod

app = typer.Typer(help="Fase 0 -- reconocimiento del panel histórico OPA.")
console = Console()

RUTA_CONFIG = Path("conf/sources.yml")
RUTA_DISCOVERY_JSONL = Path("reports/discovery.jsonl")
RUTA_COBERTURA_MD = Path("reports/cobertura.md")
RUTA_ESQUEMAS_MD = Path("reports/esquemas.md")
RUTA_CALIDAD_SILVER_MD = Path("reports/calidad_silver.md")
DIR_MUESTRAS = Path("data/muestras")
DIR_AUXILIARES = Path("data/auxiliares")
DIR_BRONZE = Path("data/bronze")
DIR_SILVER = Path("data/silver")
RUTA_MANIFEST_JSONL = Path("data/manifest.jsonl")

TIMEOUT_DESCARGA_SEGUNDOS = 60.0
BYTES_MUESTRA_SNIFF = 8192

# Extensiones que Bronze archiva -- excluye assets del sitio (imágenes, JS) que la CDX de
# Wayback también captura bajo los mismos prefijos de URL, sin ser datos de OPA.
_EXTENSIONES_BRONZE = {"csv", "xlsx", "json"}


@app.command()
def discover() -> None:
    """Ejecuta el descubrimiento completo (vivo + espejos + Wayback) y escribe los reportes."""
    resultados = discovery.ejecutar_descubrimiento(
        ruta_config=RUTA_CONFIG,
        ruta_reporte=RUTA_DISCOVERY_JSONL,
        dir_auxiliares=DIR_AUXILIARES,
    )
    cfg = discovery.cargar_config(RUTA_CONFIG)
    reporte_md = discovery.generar_reporte_cobertura(resultados, cfg)
    RUTA_COBERTURA_MD.parent.mkdir(parents=True, exist_ok=True)
    RUTA_COBERTURA_MD.write_text(reporte_md, encoding="utf-8")

    console.print(f"\n[bold green]Descubrimiento completo.[/] {len(resultados)} registros escritos.")
    console.print(f"  Crudo:     {RUTA_DISCOVERY_JSONL}")
    console.print(f"  Cobertura: {RUTA_COBERTURA_MD}")


# --------------------------------------------------------------------------
# Bronze -- ingesta completa y manifiesto (Fase 1, ver ARQUITECTURA sección 4.1)
# --------------------------------------------------------------------------


def _candidatas_bronze(filas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filtra discovery.jsonl a snapshots reales descargables -- existe=True, extensión de
    datos (csv/xlsx/json), de una fuente descargable (vivo/wayback/espejo). Excluye consultas
    de metadatos (CDX_QUERY, API sin recurso) y assets del sitio (imágenes, JS) que Wayback
    captura bajo los mismos prefijos de URL sin ser datos de OPA."""
    candidatas = []
    for f in filas:
        if not f.get("existe") or f.get("fuente") not in ("vivo", "wayback", "espejo"):
            continue
        url = str(f.get("url", ""))
        nombre = url.rsplit("/", 1)[-1].split("?")[0]
        ext = nombre.rsplit(".", 1)[-1].lower() if "." in nombre else ""
        if ext not in _EXTENSIONES_BRONZE:
            continue
        candidatas.append(f)
    return candidatas


@app.command()
def bronze() -> None:
    """Descarga completa de todos los snapshots recuperables y escribe el manifiesto (Fase 1 -- Bronze).

    Regla dura: bronze nunca se reescribe. El nombre de archivo es direccionable por contenido
    (incluye los primeros 8 caracteres del sha256), así que re-correr esto es idempotente --
    lo ya ingerido (por ``url`` + corte declarado) no se vuelve a descargar.
    """
    filas = _leer_discovery(RUTA_DISCOVERY_JSONL)
    candidatas = _candidatas_bronze(filas)
    console.print(
        f"[bold]{len(candidatas)}[/] candidatas con contenido real de {len(filas)} renglones en discovery.jsonl."
    )

    cfg = discovery.cargar_config(RUTA_CONFIG)
    manifiesto_previo = manifest.cargar_manifiesto(RUTA_MANIFEST_JSONL)
    ya_ingeridas = manifest.claves_ya_ingeridas(manifiesto_previo)

    DIR_BRONZE.mkdir(parents=True, exist_ok=True)
    RUTA_MANIFEST_JSONL.parent.mkdir(parents=True, exist_ok=True)

    limitador = discovery.LimitadorTasa(cfg["red"]["rate_limit_segundos_shcp"])
    user_agent = cfg["red"]["user_agent"]
    timeout = cfg["red"]["timeout_segundos"]

    descargados = saltados = fallidos = 0
    total_bytes = 0
    cache_por_url: dict[str, tuple[int, bytes]] = {}

    with (
        httpx.Client(headers={"User-Agent": user_agent}, follow_redirects=True) as cliente,
        RUTA_MANIFEST_JSONL.open("a", encoding="utf-8") as f_manifest,
    ):
        for i, fila in enumerate(candidatas, start=1):
            anio, trimestre = fila.get("anio"), fila.get("trimestre")
            url = str(fila["url"])
            clave = (url, anio, trimestre)
            if clave in ya_ingeridas:
                saltados += 1
                continue

            url_descarga = _url_para_descarga(fila)
            if url_descarga not in cache_por_url:
                limitador.esperar()
                try:
                    cache_por_url[url_descarga] = _get_completo_con_fallback(cliente, url_descarga, user_agent, timeout)
                except (httpx.HTTPError, RuntimeError) as exc:
                    console.log(f"[red]Fallo descargando {url_descarga}: {exc}[/]")
                    fallidos += 1
                    continue
            status, contenido = cache_por_url[url_descarga]
            if not contenido:
                console.log(f"[yellow]Cuerpo vacío: {url_descarga}[/]")
                fallidos += 1
                continue

            try:
                sha256 = manifest.calcular_sha256(contenido)
                ext = url.rsplit("/", 1)[-1].split("?")[0].rsplit(".", 1)[-1].lower()
                slug = manifest.slug_desde_url(url) if anio is None else None
                nombre_bronze = manifest.nombre_archivo_bronze(anio, trimestre, sha256, ext, slug)
                ruta_bronze = DIR_BRONZE / nombre_bronze
                if not ruta_bronze.exists():
                    ruta_bronze.write_bytes(contenido)

                columnas, encoding = manifest.inspeccionar_columnas(contenido, ext)
                registro = manifest.RegistroManifiesto(
                    snapshot_id=manifest.construir_snapshot_id(anio, trimestre, sha256, slug),
                    url=url,
                    origen=fila["fuente"],
                    fecha_descarga=datetime.now(UTC).date().isoformat(),
                    http_status=status,
                    sha256=sha256,
                    bytes=len(contenido),
                    corte_declarado={"anio": anio, "trimestre": trimestre},
                    archivo_bronze=nombre_bronze,
                    header_hash=manifest.calcular_header_hash(columnas),
                    n_columnas=len(columnas) if columnas else None,
                    encoding_detectado=encoding,
                    wayback_timestamp=fila.get("wayback_timestamp") if fila["fuente"] == "wayback" else None,
                )
            except Exception as exc:  # un archivo raro (encabezado no estándar, etc.) no debe tumbar el lote
                console.log(f"[red]Fallo procesando {url} (contenido ya descargado, no se pierde): {exc}[/]")
                fallidos += 1
                continue

            f_manifest.write(registro.to_json_line() + "\n")
            f_manifest.flush()
            descargados += 1
            total_bytes += len(contenido)
            ya_ingeridas.add(clave)

            if i % 20 == 0 or i == len(candidatas):
                console.print(
                    f"  ... {i}/{len(candidatas)} procesadas "
                    f"({descargados} nuevas, {saltados} ya ingeridas, {fallidos} fallidas)"
                )

    console.print(
        f"\n[bold green]Bronze completo.[/] {descargados} snapshots nuevos "
        f"({total_bytes / 1_048_576:.1f} MB), {saltados} ya ingeridos, {fallidos} fallidos."
    )
    console.print(f"  Bronze:     {DIR_BRONZE}/")
    console.print(f"  Manifiesto: {RUTA_MANIFEST_JSONL}")


# --------------------------------------------------------------------------
# Silver -- normalización a esquema canónico (Fase 2, ver src/opa/normalize.py)
# --------------------------------------------------------------------------


@app.command()
def normalize() -> None:
    """Bronze -> Silver: normaliza a parquet los snapshots con esquema conocido en conf/schema_map.yml.

    Falla ruidoso (código de salida 1) si aparece un esquema no mapeado o un error de
    lectura -- ver ARQUITECTURA sección 5.3. Los snapshots que sí se normalizan quedan
    escritos aunque otros fallen: no se pierde trabajo bueno por uno malo.
    """
    resultados = normalize_mod.ejecutar_normalizacion(
        ruta_manifest=RUTA_MANIFEST_JSONL, ruta_schema_map=Path("conf/schema_map.yml"),
        dir_bronze=DIR_BRONZE, dir_silver=DIR_SILVER,
    )
    reporte_md = normalize_mod.generar_reporte_calidad(resultados)
    RUTA_CALIDAD_SILVER_MD.parent.mkdir(parents=True, exist_ok=True)
    RUTA_CALIDAD_SILVER_MD.write_text(reporte_md, encoding="utf-8")

    ok = [r for r in resultados if r.estado == "ok"]
    corruptos = [r for r in resultados if r.estado == "corrupto_conocido"]
    desconocidos = [r for r in resultados if r.estado == "esquema_desconocido"]
    errores = [r for r in resultados if r.estado == "error"]

    console.print(f"[bold green]Silver: {len(ok)} snapshots normalizados[/] de {len(resultados)} candidatos.")
    console.print(f"  Omitidos por corrupción conocida: {len(corruptos)}")
    if desconocidos:
        console.print(f"[bold red]{len(desconocidos)} con esquema DESCONOCIDO -- no están en conf/schema_map.yml:[/]")
        for r in desconocidos:
            console.print(f"  - {r.archivo_bronze}")
    if errores:
        console.print(f"[bold red]{len(errores)} con error de lectura:[/]")
        for r in errores:
            console.print(f"  - {r.archivo_bronze}: {r.detalle_error}")
    console.print(f"  Silver:  {DIR_SILVER}/")
    console.print(f"  Reporte: {RUTA_CALIDAD_SILVER_MD}")

    if desconocidos or errores:
        raise typer.Exit(code=1)


# --------------------------------------------------------------------------
# Selección e inspección de muestras
# --------------------------------------------------------------------------


def _leer_discovery(ruta: Path) -> list[dict[str, Any]]:
    if not ruta.exists():
        console.print(f"[red]No existe {ruta}. Corre primero:[/] uv run opa discover")
        raise typer.Exit(code=1)
    filas = []
    with ruta.open(encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if linea:
                filas.append(json.loads(linea))
    return filas


def elegir_muestras(filas: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Elige 3 filas representativas -- más antigua, ~2019-2020, más reciente -- de discovery.jsonl."""
    candidatas = [
        f
        for f in filas
        if f.get("existe")
        and f.get("anio") is not None
        and f.get("metodo") not in ("CDX_QUERY", "API")
        and str(f.get("url", "")).lower().endswith((".csv", ".xlsx"))
    ]
    if not candidatas:
        console.print("[red]No hay candidatas descargables en discovery.jsonl.[/]")
        raise typer.Exit(code=1)

    def orden(f: dict[str, Any]) -> tuple[int, int, int]:
        return (f["anio"], f.get("trimestre") or 0, 0 if f["fuente"] == "vivo" else 1)

    candidatas.sort(key=orden)

    elegidas: dict[str, dict[str, Any]] = {}
    elegidas["antigua"] = candidatas[0]
    elegidas["reciente"] = candidatas[-1]

    restantes = [f for f in candidatas if f is not elegidas["antigua"] and f is not elegidas["reciente"]]
    fuente_intermedia = restantes or candidatas
    elegidas["intermedia"] = min(fuente_intermedia, key=lambda f: abs(f["anio"] - 2019.5))

    return elegidas


def _url_para_descarga(fila: dict[str, Any]) -> str:
    if fila["fuente"] == "wayback":
        return f"http://web.archive.org/web/{fila['wayback_timestamp']}id_/{fila['url']}"
    return fila["url"]


def _get_completo_con_fallback(
    cliente: httpx.Client, url: str, user_agent: str, timeout: float
) -> tuple[int, bytes]:
    """GET completo; cae a curl si httpx no puede armar la cadena de certificados -- ver la
    nota en ``discovery.es_error_cadena_tls`` (caso real y confirmado en dominios .gob.mx)."""
    try:
        resp = cliente.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.status_code, resp.content
    except httpx.HTTPError as exc:
        error = f"{type(exc).__name__}: {exc}"
        if not discovery.es_error_cadena_tls(error):
            raise
        status, _headers, cuerpo = discovery.curl_get(url, user_agent, timeout)
        if status is None or status >= 400:
            raise RuntimeError(f"No se pudo descargar {url} (tampoco vía curl): {error}") from exc
        return status, cuerpo


def descargar_muestra(
    cliente: httpx.Client, etiqueta: str, fila: dict[str, Any], destino_dir: Path, user_agent: str
) -> Path:
    """Descarga una muestra completa (excepción explícita a "solo metadatos" de discovery)."""
    url_descarga = _url_para_descarga(fila)
    _status, contenido = _get_completo_con_fallback(cliente, url_descarga, user_agent, TIMEOUT_DESCARGA_SEGUNDOS)

    destino_dir.mkdir(parents=True, exist_ok=True)
    ext = fila["url"].rsplit(".", 1)[-1].split("?")[0].lower()
    trimestre = f"t{fila['trimestre']}" if fila.get("trimestre") else "anual"
    nombre = f"opa_{fila['anio']}_{trimestre}_{etiqueta}_{fila['fuente']}.{ext}"
    ruta = destino_dir / nombre
    ruta.write_bytes(contenido)
    return ruta


def _detectar_encoding_csv(contenido: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            contenido.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
    return "latin-1"  # decodifica cualquier secuencia de bytes: último recurso


def _detectar_dialecto_csv(texto: str) -> csv.Dialect:
    muestra = texto[:BYTES_MUESTRA_SNIFF]
    try:
        return csv.Sniffer().sniff(muestra, delimiters=",;\t|")
    except csv.Error:
        return csv.excel  # separador coma por defecto de Excel


def _buscar_columna(columnas: list[str], candidatos: list[str]) -> str | None:
    normalizadas = {c.strip().lower(): c for c in columnas}
    for candidato in candidatos:
        if candidato in normalizadas:
            return normalizadas[candidato]
    return None


@dataclass
class InspeccionEsquema:
    """Resultado de inspeccionar un snapshot muestra."""

    etiqueta: str
    ruta: Path
    anio: int | None
    trimestre: int | None
    fuente_datos: str
    url_original: str
    formato: str
    encoding: str | None = None
    separador: str | None = None
    quotechar: str | None = None
    columnas: list[str] | None = None
    n_filas: int | None = None
    n_ppi_unicos: int | None = None
    columna_cartera: str | None = None
    cve_cartera_min: str | None = None
    cve_cartera_max: str | None = None
    cve_cartera_formato_consistente: bool | None = None
    cve_cartera_pct_valido: float | None = None
    error: str | None = None


def inspeccionar_archivo(etiqueta: str, ruta: Path, fila: dict[str, Any]) -> InspeccionEsquema:
    """Detecta encoding, separador, columnas y consistencia de cve_cartera de un snapshot."""
    formato = ruta.suffix.lower().lstrip(".")
    insp = InspeccionEsquema(
        etiqueta=etiqueta,
        ruta=ruta,
        anio=fila.get("anio"),
        trimestre=fila.get("trimestre"),
        fuente_datos=fila["fuente"],
        url_original=fila["url"],
        formato=formato,
    )
    try:
        if formato == "csv":
            crudo = ruta.read_bytes()
            insp.encoding = _detectar_encoding_csv(crudo)
            texto = crudo.decode(insp.encoding)
            dialecto = _detectar_dialecto_csv(texto)
            insp.separador = dialecto.delimiter
            insp.quotechar = dialecto.quotechar
            df = pd.read_csv(
                io.StringIO(texto), sep=insp.separador, quotechar=insp.quotechar, dtype=str, engine="python"
            )
        elif formato == "xlsx":
            df = pd.read_excel(ruta, dtype=str)
        else:
            insp.error = f"formato no soportado para inspección: {formato}"
            return insp
    except (pd.errors.ParserError, ValueError, UnicodeDecodeError) as exc:
        insp.error = f"{type(exc).__name__}: {exc}"
        return insp

    insp.columnas = list(df.columns)
    insp.n_filas = len(df)

    col_cartera = _buscar_columna(insp.columnas, ["cve_cartera", "clave_cartera"])
    col_ppi = _buscar_columna(insp.columnas, ["id_ppi", "cve_cartera", "clave_cartera"])
    insp.columna_cartera = col_cartera
    insp.n_ppi_unicos = int(df[col_ppi].nunique()) if col_ppi else None

    if col_cartera:
        serie = df[col_cartera].dropna().astype(str).str.strip()
        serie = serie[serie != ""]
        if len(serie):
            insp.cve_cartera_min, insp.cve_cartera_max = serie.min(), serie.max()
            valido = serie.str.match(r"^\d{10,11}$")
            insp.cve_cartera_pct_valido = round(float(valido.mean()) * 100, 1)
            insp.cve_cartera_formato_consistente = bool(valido.all())

    return insp


def _tabla_comparativa_columnas(inspecciones: list[InspeccionEsquema]) -> list[str]:
    todas: list[str] = []
    vistas: set[str] = set()
    for insp in inspecciones:
        for c in insp.columnas or []:
            clave = c.strip().lower()
            if clave not in vistas:
                vistas.add(clave)
                todas.append(c)

    filas = [
        "| Columna | " + " | ".join(i.etiqueta for i in inspecciones) + " |",
        "|---|" + "---|" * len(inspecciones),
    ]
    for columna in todas:
        clave = columna.strip().lower()
        marcas = ["✓" if any(c.strip().lower() == clave for c in (i.columnas or [])) else "—" for i in inspecciones]
        filas.append(f"| `{columna}` | " + " | ".join(marcas) + " |")
    return filas


def generar_reporte_esquemas(inspecciones: list[InspeccionEsquema]) -> str:
    """Renderiza ``reports/esquemas.md`` con el detalle y la comparación de las 3 muestras."""
    lineas = [
        "# Comparación de esquemas — muestras de Fase 0",
        "",
        f"*Generado por `opa inspect` el {datetime.now(UTC).isoformat()}.*",
        "",
    ]
    for insp in inspecciones:
        corte = f"{insp.anio} T{insp.trimestre}" if insp.trimestre else f"{insp.anio} (anual/genérico)"
        lineas.append(f"## {insp.etiqueta}: `{insp.ruta.name}` ({corte})")
        lineas.append("")
        lineas.append(f"- Fuente: **{insp.fuente_datos}** -- `{insp.url_original}`")
        lineas.append(f"- Formato: {insp.formato}")
        if insp.error:
            lineas.append(f"- ⚠️ **Error al inspeccionar:** {insp.error}")
            lineas.append("")
            continue
        lineas.append(f"- Encoding detectado: {insp.encoding or 'N/A (binario, xlsx)'}")
        if insp.separador:
            lineas.append(f"- Separador: `{insp.separador}` / quotechar: `{insp.quotechar}`")
        else:
            lineas.append("- Separador: N/A (xlsx)")
        lineas.append(f"- Filas: {insp.n_filas}")
        lineas.append(
            f"- Columna de cartera detectada: `{insp.columna_cartera}`"
            if insp.columna_cartera
            else "- Columna de cartera: **NO DETECTADA**"
        )
        if insp.n_ppi_unicos is not None:
            lineas.append(f"- PPI únicos: {insp.n_ppi_unicos}")
        if insp.cve_cartera_min is not None:
            consistente = "sí" if insp.cve_cartera_formato_consistente else "no"
            lineas.append(f"- Rango `cve_cartera`: {insp.cve_cartera_min} – {insp.cve_cartera_max}")
            lineas.append(
                f"- Formato consistente (`^\\d{{10,11}}$`): {consistente} ({insp.cve_cartera_pct_valido}% válido)"
            )
        lineas.append(f"- Columnas ({len(insp.columnas or [])}): " + ", ".join(f"`{c}`" for c in insp.columnas or []))
        lineas.append("")

    lineas.append("## Comparación de columnas entre las 3 muestras")
    lineas.append("")
    lineas.extend(_tabla_comparativa_columnas(inspecciones))
    lineas.append("")
    return "\n".join(lineas) + "\n"


@app.command()
def inspect() -> None:
    """Descarga 3 snapshots muestra (antiguo, ~2019-2020, reciente) e inspecciona sus esquemas."""
    filas = _leer_discovery(RUTA_DISCOVERY_JSONL)
    muestras = elegir_muestras(filas)

    cfg = discovery.cargar_config(RUTA_CONFIG)
    headers = {"User-Agent": cfg["red"]["user_agent"]}

    inspecciones: list[InspeccionEsquema] = []
    with httpx.Client(headers=headers, follow_redirects=True) as cliente:
        for etiqueta, fila in muestras.items():
            console.print(f"Descargando muestra [bold]{etiqueta}[/] ({fila['anio']}, fuente={fila['fuente']}) ...")
            ruta = descargar_muestra(cliente, etiqueta, fila, DIR_MUESTRAS, cfg["red"]["user_agent"])
            console.print(f"  -> {ruta}")
            inspecciones.append(inspeccionar_archivo(etiqueta, ruta, fila))

    reporte_md = generar_reporte_esquemas(inspecciones)
    RUTA_ESQUEMAS_MD.parent.mkdir(parents=True, exist_ok=True)
    RUTA_ESQUEMAS_MD.write_text(reporte_md, encoding="utf-8")

    console.print(f"\n[bold green]Inspección completa.[/] Reporte: {RUTA_ESQUEMAS_MD}")


# --------------------------------------------------------------------------
# Diccionario de datos (Fase A del plan de alineación ATDT -- ver
# docs/PLAN-alineacion-gold-lineamientos-ATDT.md)
# --------------------------------------------------------------------------

RUTA_SCHEMA_MARTS = Path("dbt/models/marts/schema.yml")
RUTA_GOLD_DUCKDB = Path("data/gold/panel_opa.duckdb")
DIR_DICCIONARIO = Path("reports/diccionario")


@app.command()
def diccionario() -> None:
    """Genera el diccionario de datos de Gold desde schema.yml contra el duckdb real.

    Falla ruidoso (código 1) si alguna columna real no tiene descripción o si schema.yml
    documenta columnas que ya no existen -- la deriva es un error, no una advertencia.
    """
    from opa import diccionario as diccionario_mod

    if not RUTA_GOLD_DUCKDB.exists():
        console.print(
            f"[bold red]No existe {RUTA_GOLD_DUCKDB}.[/] Corre primero: "
            "dbt build --project-dir dbt --profiles-dir dbt"
        )
        raise typer.Exit(code=1)

    try:
        escritas = diccionario_mod.generar(RUTA_SCHEMA_MARTS, RUTA_GOLD_DUCKDB, DIR_DICCIONARIO)
    except diccionario_mod.ErrorDiccionario as exc:
        console.print(f"[bold red]Diccionario incompleto.[/]\n{exc}")
        raise typer.Exit(code=1) from exc

    console.print(f"[bold green]Diccionario generado.[/] {len(escritas)} archivos:")
    for ruta in escritas:
        console.print(f"  {ruta}")


if __name__ == "__main__":
    app()
