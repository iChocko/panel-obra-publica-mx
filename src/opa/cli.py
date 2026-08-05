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

from opa import discovery

app = typer.Typer(help="Fase 0 -- reconocimiento del panel histórico OPA.")
console = Console()

RUTA_CONFIG = Path("conf/sources.yml")
RUTA_DISCOVERY_JSONL = Path("reports/discovery.jsonl")
RUTA_COBERTURA_MD = Path("reports/cobertura.md")
RUTA_ESQUEMAS_MD = Path("reports/esquemas.md")
DIR_MUESTRAS = Path("data/muestras")
DIR_AUXILIARES = Path("data/auxiliares")

TIMEOUT_DESCARGA_SEGUNDOS = 60.0
BYTES_MUESTRA_SNIFF = 8192


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


def descargar_muestra(
    cliente: httpx.Client, etiqueta: str, fila: dict[str, Any], destino_dir: Path, user_agent: str
) -> Path:
    """Descarga una muestra completa (excepción explícita a "solo metadatos" de discovery).

    Cae a curl si httpx no puede armar la cadena de certificados -- ver la nota en
    ``discovery.es_error_cadena_tls`` (caso real y confirmado en dominios .gob.mx).
    """
    url_descarga = _url_para_descarga(fila)
    try:
        resp = cliente.get(url_descarga, timeout=TIMEOUT_DESCARGA_SEGUNDOS)
        resp.raise_for_status()
        contenido = resp.content
    except httpx.HTTPError as exc:
        error = f"{type(exc).__name__}: {exc}"
        if not discovery.es_error_cadena_tls(error):
            raise
        status, _headers, cuerpo = discovery.curl_get(url_descarga, user_agent, TIMEOUT_DESCARGA_SEGUNDOS)
        if status != 200:
            raise RuntimeError(f"No se pudo descargar {url_descarga} (tampoco vía curl): {error}") from exc
        contenido = cuerpo

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


if __name__ == "__main__":
    app()
