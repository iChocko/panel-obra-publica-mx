"""Descubrimiento de fuentes de datos abiertos de Obra Pública Abierta (OPA).

Prueba tres fuentes en cascada -- URLs vivas de la SHCP, espejos (CKAN /
datamx.io) y capturas del Wayback Machine -- y produce una matriz de
cobertura año x trimestre para decidir el alcance del panel (Fase 0).
No descarga archivos completos salvo los auxiliares declarados en
``conf/sources.yml`` cuando responden 200.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import yaml
from rich.console import Console

console = Console()

ORD_A_TRIMESTRE: dict[str, int] = {"1er": 1, "2do": 2, "3er": 3, "4to": 4}

# Patrones sin trimestre explícito: cuentan como cobertura anual de respaldo,
# nunca se asignan a una celda trimestral de la matriz de decisión (ver
# reports/cobertura.md, sección "Cobertura anual").
PATRONES_ANUALES_GENERICOS = frozenset({"anual_generico", "anual_generico_antiguo"})

LEGEND_PRIORIDAD: tuple[str, ...] = ("vivo", "espejo", "wayback")


@dataclass
class ResultadoProbe:
    """Resultado crudo de probar una URL o consulta contra una fuente."""

    fuente: str  # "vivo" | "espejo" | "wayback"
    url: str
    metodo: str  # "HEAD" | "GET_RANGE" | "GET" | "API" | "CDX_QUERY" | "WAYBACK_CAPTURE" | "CKAN_RESOURCE"
    status: int | None
    content_length: int | None = None
    content_type: str | None = None
    last_modified: str | None = None
    anio: int | None = None
    trimestre: int | None = None
    patron: str | None = None
    existe: bool = False
    error: str | None = None
    intentos: int = 1
    timestamp_consulta: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_json_line(self) -> str:
        """Serializa a una línea JSON plana (los campos de ``extra`` se aplanan)."""
        datos = asdict(self)
        extra = datos.pop("extra")
        datos.update(extra)
        return json.dumps(datos, ensure_ascii=False)


def _ahora_iso() -> str:
    return datetime.now(UTC).isoformat()


def _parse_int(valor: Any) -> int | None:
    if valor is None:
        return None
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def cargar_config(ruta: Path = Path("conf/sources.yml")) -> dict[str, Any]:
    """Carga los patrones de URL y parámetros de red desde YAML."""
    with ruta.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class LimitadorTasa:
    """Aplica un intervalo mínimo entre solicitudes sucesivas a un mismo dominio."""

    def __init__(self, intervalo_segundos: float) -> None:
        self.intervalo = intervalo_segundos
        self._ultima: float | None = None

    def esperar(self) -> None:
        if self._ultima is not None:
            faltante = self.intervalo - (time.monotonic() - self._ultima)
            if faltante > 0:
                time.sleep(faltante)
        self._ultima = time.monotonic()


def _llamar_con_reintentos[T](
    func: Callable[[], T], max_intentos: int, backoff_base: float
) -> tuple[T | None, int, str | None]:
    """Ejecuta ``func()`` con reintentos y backoff exponencial ante errores de red.

    Solo reintenta excepciones de red/timeout -- una respuesta HTTP válida
    (incluidos 404/403) no se reintenta porque es una respuesta definitiva,
    no un fallo transitorio.
    """
    ultimo_error: str | None = None
    for intento in range(1, max_intentos + 1):
        try:
            return func(), intento, None
        except httpx.HTTPError as exc:
            ultimo_error = f"{type(exc).__name__}: {exc}"
            if intento < max_intentos:
                time.sleep(backoff_base * (2 ** (intento - 1)))
    return None, max_intentos, ultimo_error


# --------------------------------------------------------------------------
# Fuente 1: URLs vivas
# --------------------------------------------------------------------------


def generar_urls_vivas(
    cfg: dict[str, Any],
) -> Iterator[tuple[str, int | None, int | None, str]]:
    """Genera ``(url, anio, trimestre, patron)`` para el producto cartesiano de Fuente 1."""
    fv = cfg["fuente_viva"]
    base = fv["base_url"]
    anio_desde, anio_hasta = cfg["anios"]["desde"], cfg["anios"]["hasta"]

    for anio in range(anio_desde, anio_hasta + 1):
        for patron in fv["patrones"]:
            if "{n}" in patron:
                for n in fv["trimestre_n"]:
                    yield base + patron.format(anio=anio, n=n), anio, n, patron
            elif "{ord}" in patron and "{v}" in patron:
                for ord_ in fv["trimestre_ord"]:
                    for v in fv["version_v"]:
                        yield (
                            base + patron.format(anio=anio, ord=ord_, v=v),
                            anio,
                            ORD_A_TRIMESTRE[ord_],
                            patron,
                        )
            elif "{ord}" in patron:
                for ord_ in fv["trimestre_ord"]:
                    yield (
                        base + patron.format(anio=anio, ord=ord_),
                        anio,
                        ORD_A_TRIMESTRE[ord_],
                        patron,
                    )
            else:
                yield base + patron.format(anio=anio), anio, None, patron

    for aux in fv["auxiliares"]:
        yield base + aux, None, None, "auxiliar"


def _get_metadatos_via_range(
    cliente: httpx.Client, url: str, headers_extra: dict[str, str], timeout: float, tope_bytes: int
) -> tuple[int, dict[str, str]]:
    """GET en streaming leyendo pocos bytes -- nunca descarga el archivo completo.

    Los encabezados (incluido ``content-length`` real) llegan antes que el
    cuerpo, así que cortar la lectura no compromete los metadatos.
    """
    with cliente.stream("GET", url, headers=headers_extra, timeout=timeout) as resp:
        leido = 0
        for chunk in resp.iter_bytes():
            leido += len(chunk)
            if leido >= tope_bytes:
                break
        return resp.status_code, {k.lower(): v for k, v in resp.headers.items()}


def probar_url_vivo(
    cliente: httpx.Client,
    url: str,
    limitador: LimitadorTasa,
    cfg_red: dict[str, Any],
    anio: int | None,
    trimestre: int | None,
    patron: str,
) -> ResultadoProbe:
    """Prueba una URL viva con HEAD; cae a GET+Range si el servidor no responde bien."""
    max_intentos, backoff, timeout = (
        cfg_red["max_reintentos"],
        cfg_red["backoff_base_segundos"],
        cfg_red["timeout_segundos"],
    )

    limitador.esperar()
    resp, intentos, error = _llamar_con_reintentos(lambda: cliente.head(url, timeout=timeout), max_intentos, backoff)
    metodo = "HEAD"
    status: int | None = resp.status_code if resp is not None else None
    headers: dict[str, str] = {k.lower(): v for k, v in resp.headers.items()} if resp is not None else {}

    necesita_fallback = (
        resp is None
        or status in (403, 405, 501)
        or (status == 200 and "content-length" not in headers and "content-type" not in headers)
    )

    if necesita_fallback:
        limitador.esperar()
        metodo = "GET_RANGE"
        headers_extra = {"Range": cfg_red["head_range_bytes"]}
        resultado, intentos2, error2 = _llamar_con_reintentos(
            lambda: _get_metadatos_via_range(cliente, url, headers_extra, timeout, cfg_red["bytes_maximos_get_range"]),
            max_intentos,
            backoff,
        )
        intentos += intentos2
        if resultado is not None:
            status, headers = resultado
            error = None
        else:
            error = error2

    existe = status in (200, 206)
    return ResultadoProbe(
        fuente="vivo",
        url=url,
        metodo=metodo,
        status=status,
        content_length=_parse_int(headers.get("content-length")),
        content_type=headers.get("content-type"),
        last_modified=headers.get("last-modified"),
        anio=anio,
        trimestre=trimestre,
        patron=patron,
        existe=existe,
        error=error if status is None else None,
        intentos=intentos,
        timestamp_consulta=_ahora_iso(),
    )


def _descargar_auxiliar(
    cliente: httpx.Client, url: str, destino_dir: Path, limitador: LimitadorTasa, cfg_red: dict[str, Any]
) -> None:
    """Descarga completa de un auxiliar (diccionario/catálogo) -- excepción declarada a "solo metadatos"."""
    limitador.esperar()
    try:
        resp = cliente.get(url, timeout=cfg_red["timeout_segundos"])
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        console.log(f"[yellow]No se pudo descargar auxiliar {url}: {exc}[/]")
        return
    destino_dir.mkdir(parents=True, exist_ok=True)
    nombre = url.rsplit("/", 1)[-1]
    (destino_dir / nombre).write_bytes(resp.content)
    console.log(f"[green]Auxiliar descargado:[/] {nombre}")


def ejecutar_fuente_viva(
    cliente: httpx.Client,
    cfg: dict[str, Any],
    dir_auxiliares: Path,
    registrar: Callable[[ResultadoProbe], None],
) -> None:
    """Prueba el producto cartesiano completo de Fuente 1, respetando el rate limit."""
    limitador = LimitadorTasa(cfg["red"]["rate_limit_segundos_shcp"])
    urls = list(generar_urls_vivas(cfg))
    console.log(f"Fuente 1 (vivo): {len(urls)} URLs candidatas a probar (~1 cada 2s).")
    for i, (url, anio, trimestre, patron) in enumerate(urls, start=1):
        r = probar_url_vivo(cliente, url, limitador, cfg["red"], anio, trimestre, patron)
        registrar(r)
        if patron == "auxiliar" and r.existe:
            _descargar_auxiliar(cliente, url, dir_auxiliares, limitador, cfg["red"])
        if i % 25 == 0 or i == len(urls):
            console.log(f"  ... {i}/{len(urls)} probadas")


# --------------------------------------------------------------------------
# Fuente 2: espejos (CKAN / datamx.io)
# --------------------------------------------------------------------------


def ejecutar_fuente_espejo(
    cliente: httpx.Client, cfg: dict[str, Any], registrar: Callable[[ResultadoProbe], None]
) -> None:
    """Consulta el mirror CKAN de datos.gob.mx (por id conocido y por nombre) y datamx.io."""
    fe = cfg["fuente_espejo"]
    max_intentos, backoff, timeout = (
        cfg["red"]["max_reintentos"],
        cfg["red"]["backoff_base_segundos"],
        cfg["red"]["timeout_segundos"],
    )
    console.log("Fuente 2 (espejo): CKAN datos.gob.mx + datamx.io")

    # 1. package_show por el id histórico documentado en el dictamen.
    url_show = f"{fe['ckan_base']}/package_show?id={fe['ckan_package_id']}"
    resp, _intentos, error = _llamar_con_reintentos(
        lambda: cliente.get(url_show, timeout=timeout), max_intentos, backoff
    )
    existe_show = False
    recursos: list[dict[str, Any]] = []
    if resp is not None:
        try:
            cuerpo = resp.json()
        except json.JSONDecodeError:
            cuerpo = {}
        existe_show = bool(cuerpo.get("success"))
        if existe_show:
            recursos = cuerpo.get("result", {}).get("resources", [])
    registrar(
        ResultadoProbe(
            fuente="espejo",
            url=url_show,
            metodo="API",
            status=resp.status_code if resp is not None else None,
            existe=existe_show,
            error=error or (None if existe_show else "dataset no encontrado con este id"),
            timestamp_consulta=_ahora_iso(),
            extra={"n_recursos": len(recursos)},
        )
    )
    for r in recursos:
        anio_r, trimestre_r, patron_r = clasificar_captura(r.get("url", ""))
        registrar(
            ResultadoProbe(
                fuente="espejo",
                url=r.get("url", ""),
                metodo="CKAN_RESOURCE",
                status=None,
                anio=anio_r,
                trimestre=trimestre_r,
                patron=patron_r if patron_r != "no_reconocido" else "recurso_ckan",
                existe=True,
                timestamp_consulta=_ahora_iso(),
                extra={"nombre_recurso": r.get("name"), "formato": r.get("format")},
            )
        )

    # 2. Búsqueda de respaldo por nombre, por si el id cambió de lugar.
    url_search = f"{fe['ckan_base']}/package_search"
    resp2, _intentos2, error2 = _llamar_con_reintentos(
        lambda: cliente.get(url_search, params={"q": fe["ckan_busqueda_respaldo"]}, timeout=timeout),
        max_intentos,
        backoff,
    )
    n_resultados = None
    if resp2 is not None:
        try:
            n_resultados = resp2.json().get("result", {}).get("count")
        except json.JSONDecodeError:
            n_resultados = None
    registrar(
        ResultadoProbe(
            fuente="espejo",
            url=f"{url_search}?q={fe['ckan_busqueda_respaldo']}",
            metodo="API",
            status=resp2.status_code if resp2 is not None else None,
            existe=bool(n_resultados),
            error=error2,
            timestamp_consulta=_ahora_iso(),
            extra={"n_resultados_busqueda": n_resultados},
        )
    )

    # 3. datamx.io -- sondeo directo, referenciado en el dictamen como mirror candidato.
    resp3, _intentos3, error3 = _llamar_con_reintentos(
        lambda: cliente.get(fe["datamx_io"], timeout=timeout), max_intentos, backoff
    )
    contiene_opa = False
    if resp3 is not None and resp3.status_code == 200:
        texto = resp3.text.lower()
        contiene_opa = "opa" in texto and ("obra p" in texto or "inversi" in texto)
    registrar(
        ResultadoProbe(
            fuente="espejo",
            url=fe["datamx_io"],
            metodo="GET",
            status=resp3.status_code if resp3 is not None else None,
            existe=contiene_opa,
            error=error3,
            timestamp_consulta=_ahora_iso(),
            extra={"referencia_opa_detectada": contiene_opa},
        )
    )


# --------------------------------------------------------------------------
# Fuente 3: Wayback Machine (CDX API)
# --------------------------------------------------------------------------


_PATRONES_CLASIFICACION: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"/OPA/(?P<anio>\d{4})/proyectos_opa_0(?P<n>[1-4])t\d{4}\.(csv|xlsx)", re.IGNORECASE),
        "trimestral_numerico",
    ),
    (
        re.compile(
            r"/OPA/(?P<anio>\d{4})/reporteOPA(?P<ord>1er|2do|3er|4to)Trimestre(_V\d)?\.xlsx",
            re.IGNORECASE,
        ),
        "trimestral_ordinal",
    ),
    (
        re.compile(r"/DatosAbiertos/OPA/(?P<anio>\d{4})/proyectos_opa\.(csv|xlsx)", re.IGNORECASE),
        "anual_generico",
    ),
    (
        re.compile(r"/PTP/OPA/(?P<anio>\d{4})/Proyectos_OPA\.csv", re.IGNORECASE),
        "anual_generico_antiguo",
    ),
]


def clasificar_captura(url_original: str) -> tuple[int | None, int | None, str]:
    """Determina ``(anio, trimestre, patron)`` de una URL viva o capturada por Wayback.

    El trimestre solo se asigna cuando el nombre de archivo lo declara
    explícitamente. Los patrones anuales genéricos devuelven ``trimestre=None``
    a propósito -- no hay manera honesta de saber a qué corte trimestral
    corresponde un archivo que fue sobreescrito con nombre genérico.
    """
    for regex, nombre in _PATRONES_CLASIFICACION:
        m = regex.search(url_original)
        if not m:
            continue
        gd = m.groupdict()
        anio = int(gd["anio"])
        trimestre = None
        if gd.get("n"):
            trimestre = int(gd["n"])
        elif gd.get("ord"):
            trimestre = ORD_A_TRIMESTRE[gd["ord"].lower()]
        return anio, trimestre, nombre
    return None, None, "no_reconocido"


def consultar_cdx(
    cliente: httpx.Client, prefijo: str, cfg: dict[str, Any]
) -> tuple[list[dict[str, Any]] | None, str | None]:
    """Consulta la CDX API para un prefijo.

    Devuelve ``(capturas, error)``. ``capturas is None`` significa que la
    consulta falló o fue bloqueada (no se pudo obtener una respuesta JSON
    confiable) -- distinto de ``capturas == []``, que es una respuesta válida
    confirmando cero resultados. Esta distinción es la que exige el reporte:
    no asumir ausencia de capturas cuando en realidad hubo un bloqueo.
    """
    fw = cfg["fuente_wayback"]
    params = {
        "url": prefijo,
        "matchType": fw["match_type"],
        "output": "json",
        "collapse": fw["collapse"],
        "fl": ",".join(fw["campos"]),
        "filter": [fw["filtro_status"], fw["filtro_mimetype_excluir"]],
    }
    max_intentos, backoff, timeout = (
        cfg["red"]["max_reintentos"],
        cfg["red"]["backoff_base_segundos"],
        cfg["red"]["timeout_segundos"],
    )

    def _pedir() -> httpx.Response:
        resp = cliente.get(fw["cdx_base"], params=params, timeout=timeout)
        if resp.status_code == 429 or resp.status_code >= 500:
            raise httpx.HTTPStatusError(f"HTTP {resp.status_code}", request=resp.request, response=resp)
        return resp

    resp, _intentos, error = _llamar_con_reintentos(_pedir, max_intentos, backoff)
    if resp is None:
        return None, error or "sin respuesta"
    if resp.status_code != 200:
        return None, f"HTTP {resp.status_code}"

    texto = resp.text.strip()
    if not texto:
        return [], None
    try:
        filas = json.loads(texto)
    except json.JSONDecodeError as exc:
        return None, f"respuesta no es JSON válido (posible bloqueo/captcha): {exc}"

    if len(filas) <= 1:
        return [], None
    encabezado = filas[0]
    return [dict(zip(encabezado, fila, strict=True)) for fila in filas[1:]], None


def ejecutar_fuente_wayback(
    cliente: httpx.Client, cfg: dict[str, Any], registrar: Callable[[ResultadoProbe], None]
) -> None:
    """Consulta la CDX API para cada prefijo configurado y clasifica cada captura."""
    fw = cfg["fuente_wayback"]
    console.log("Fuente 3 (Wayback): consultando CDX API")
    for prefijo in fw["prefijos"]:
        capturas, error = consultar_cdx(cliente, prefijo, cfg)
        registrar(
            ResultadoProbe(
                fuente="wayback",
                url=f"{fw['cdx_base']}?url={prefijo}",
                metodo="CDX_QUERY",
                status=200 if capturas is not None else None,
                existe=bool(capturas),
                error=error,
                timestamp_consulta=_ahora_iso(),
                extra={"n_capturas": len(capturas) if capturas is not None else None, "prefijo": prefijo},
            )
        )
        if error:
            console.log(f"  [red]Prefijo {prefijo}: {error}[/]")
        elif not capturas:
            console.log(f"  Prefijo {prefijo}: 0 capturas (respuesta válida, no bloqueo)")
        else:
            console.log(f"  Prefijo {prefijo}: {len(capturas)} capturas únicas")
        for cap in capturas or []:
            anio, trimestre, patron = clasificar_captura(cap.get("original", ""))
            registrar(
                ResultadoProbe(
                    fuente="wayback",
                    url=cap.get("original", ""),
                    metodo="WAYBACK_CAPTURE",
                    status=_parse_int(cap.get("statuscode")),
                    content_type=cap.get("mimetype"),
                    content_length=_parse_int(cap.get("length")),
                    anio=anio,
                    trimestre=trimestre,
                    patron=patron,
                    existe=True,
                    timestamp_consulta=_ahora_iso(),
                    extra={"wayback_timestamp": cap.get("timestamp"), "digest": cap.get("digest")},
                )
            )


# --------------------------------------------------------------------------
# Orquestación
# --------------------------------------------------------------------------


def ejecutar_descubrimiento(
    ruta_config: Path = Path("conf/sources.yml"),
    ruta_reporte: Path = Path("reports/discovery.jsonl"),
    dir_auxiliares: Path = Path("data/auxiliares"),
) -> list[ResultadoProbe]:
    """Corre las tres fuentes en cascada y escribe cada resultado incrementalmente en JSONL."""
    cfg = cargar_config(ruta_config)
    ruta_reporte.parent.mkdir(parents=True, exist_ok=True)
    resultados: list[ResultadoProbe] = []

    with (
        httpx.Client(headers={"User-Agent": cfg["red"]["user_agent"]}, follow_redirects=True) as cliente,
        ruta_reporte.open("w", encoding="utf-8") as f,
    ):

        def registrar(r: ResultadoProbe) -> None:
            resultados.append(r)
            f.write(r.to_json_line() + "\n")
            f.flush()

        ejecutar_fuente_viva(cliente, cfg, dir_auxiliares, registrar)
        ejecutar_fuente_espejo(cliente, cfg, registrar)
        ejecutar_fuente_wayback(cliente, cfg, registrar)

    return resultados


# --------------------------------------------------------------------------
# Matriz de cobertura y puerta de decisión
# --------------------------------------------------------------------------


def construir_matriz_trimestral(
    resultados: list[ResultadoProbe], anio_desde: int, anio_hasta: int
) -> dict[tuple[int, int], str]:
    """Construye ``{(anio, trimestre): "vivo"|"espejo"|"wayback"|"hueco"}``.

    Solo considera patrones con trimestre explícito en el nombre -- el
    patrón anual genérico se excluye a propósito (ver
    ``PATRONES_ANUALES_GENERICOS``) y se reporta aparte.
    """
    celdas: dict[tuple[int, int], set[str]] = {}
    for r in resultados:
        if r.anio is None or r.trimestre is None or not r.existe:
            continue
        if r.patron in PATRONES_ANUALES_GENERICOS:
            continue
        celdas.setdefault((r.anio, r.trimestre), set()).add(r.fuente)

    matriz: dict[tuple[int, int], str] = {}
    for anio in range(anio_desde, anio_hasta + 1):
        for trimestre in (1, 2, 3, 4):
            fuentes = celdas.get((anio, trimestre), set())
            matriz[(anio, trimestre)] = next((c for c in LEGEND_PRIORIDAD if c in fuentes), "hueco")
    return matriz


def construir_cobertura_anual_generica(
    resultados: list[ResultadoProbe], anio_desde: int, anio_hasta: int
) -> dict[int, str]:
    """Cobertura de respaldo por año a partir del patrón genérico (sin trimestre)."""
    anios: dict[int, set[str]] = {}
    for r in resultados:
        if r.anio is None or not r.existe or r.patron not in PATRONES_ANUALES_GENERICOS:
            continue
        anios.setdefault(r.anio, set()).add(r.fuente)

    return {
        anio: next((c for c in LEGEND_PRIORIDAD if c in anios.get(anio, set())), "hueco")
        for anio in range(anio_desde, anio_hasta + 1)
    }


def calcular_recuperabilidad(
    matriz: dict[tuple[int, int], str], anio_desde: int = 2016, anio_hasta: int = 2024
) -> tuple[int, int, float]:
    """Recuperabilidad sobre los trimestres de ``[anio_desde, anio_hasta]``. Devuelve (recuperables, total, %)."""
    total = (anio_hasta - anio_desde + 1) * 4
    recuperables = sum(
        1
        for anio in range(anio_desde, anio_hasta + 1)
        for trimestre in (1, 2, 3, 4)
        if matriz.get((anio, trimestre), "hueco") != "hueco"
    )
    porcentaje = (recuperables / total * 100) if total else 0.0
    return recuperables, total, porcentaje


def recomendar(porcentaje: float) -> str:
    """Aplica la puerta de decisión del dictamen de viabilidad."""
    if porcentaje >= 70:
        return "Panel trimestral completo, alcance original."
    if porcentaje >= 50:
        return "Panel trimestral parcial, huecos documentados en el reporte de calidad."
    return (
        "Pivotar a panel anual (Tomo VIII del PEF + OPA anual) y usar SRFT para la capa subnacional georreferenciada."
    )


def generar_reporte_cobertura(resultados: list[ResultadoProbe], cfg: dict[str, Any]) -> str:
    """Renderiza ``reports/cobertura.md`` completo a partir de los resultados crudos."""
    anio_desde, anio_hasta = cfg["anios"]["desde"], cfg["anios"]["hasta"]
    matriz = construir_matriz_trimestral(resultados, anio_desde, anio_hasta)
    anual = construir_cobertura_anual_generica(resultados, anio_desde, anio_hasta)
    recuperables, total, porcentaje = calcular_recuperabilidad(matriz)
    recomendacion = recomendar(porcentaje)

    simbolo = {"vivo": "🟢 vivo", "espejo": "🔵 espejo", "wayback": "🟡 wayback", "hueco": "⚪ hueco"}

    lineas: list[str] = []
    lineas.append("# Matriz de cobertura — Obra Pública Abierta (OPA)")
    lineas.append("")
    lineas.append(f"*Generado por `opa discover` el {_ahora_iso()}.*")
    lineas.append("")
    lineas.append("## Leyenda")
    lineas.append("")
    lineas.append("- 🟢 **vivo** — responde en el servidor actual de la SHCP")
    lineas.append("- 🔵 **espejo** — declarado en un mirror (datos.gob.mx / datamx.io)")
    lineas.append("- 🟡 **wayback** — únicamente recuperable vía Internet Archive")
    lineas.append("- ⚪ **hueco** — no se encontró en ninguna fuente")
    lineas.append("")
    lineas.append("## Matriz año × trimestre (patrones con trimestre explícito en el nombre)")
    lineas.append("")
    lineas.append("| Año | Q1 | Q2 | Q3 | Q4 |")
    lineas.append("|---|---|---|---|---|")
    for anio in range(anio_desde, anio_hasta + 1):
        fila = [simbolo[matriz[(anio, t)]] for t in (1, 2, 3, 4)]
        lineas.append(f"| {anio} | " + " | ".join(fila) + " |")
    lineas.append("")
    lineas.append("## Cobertura anual (patrón genérico `proyectos_opa.csv` / `.xlsx`)")
    lineas.append("")
    lineas.append(
        "> Nota metodológica: el archivo genérico no declara trimestre en el nombre; "
        'representa "el corte vigente al momento de la consulta", que es ambiguo una vez '
        "sobreescrito por publicaciones posteriores. Por rigor, **no se asigna a ningún "
        "trimestre específico** en la matriz anterior -- se reporta aparte como respaldo."
    )
    lineas.append("")
    lineas.append("| Año | Cobertura |")
    lineas.append("|---|---|")
    for anio in range(anio_desde, anio_hasta + 1):
        lineas.append(f"| {anio} | {simbolo[anual[anio]]} |")
    lineas.append("")
    lineas.append("## Puerta de decisión (2016–2024, 36 trimestres)")
    lineas.append("")
    lineas.append(f"- Trimestres recuperables: **{recuperables} / {total} ({porcentaje:.1f}%)**")
    lineas.append(f"- Recomendación: **{recomendacion}**")
    lineas.append("")
    lineas.extend(_seccion_wayback(resultados))
    lineas.extend(_seccion_espejo(resultados))

    return "\n".join(lineas) + "\n"


def _seccion_wayback(resultados: list[ResultadoProbe]) -> list[str]:
    lineas = ["## Wayback — detalle de la pregunta clave", ""]
    consultas = [r for r in resultados if r.fuente == "wayback" and r.metodo == "CDX_QUERY"]
    capturas = [r for r in resultados if r.fuente == "wayback" and r.metodo == "WAYBACK_CAPTURE"]

    for consulta in consultas:
        prefijo = consulta.extra.get("prefijo", consulta.url)
        if consulta.error:
            lineas.append(
                f"- `{prefijo}`: ⚠️ **bloqueo o error** -- {consulta.error}. No se asume ausencia de capturas."
            )
        else:
            n = consulta.extra.get("n_capturas", 0)
            lineas.append(f"- `{prefijo}`: {n} capturas únicas (respuesta válida, `collapse=digest`)")
    lineas.append("")

    if capturas:
        mimetypes = sorted({c.content_type for c in capturas if c.content_type})
        timestamps = sorted(c.extra.get("wayback_timestamp", "") for c in capturas if c.extra.get("wayback_timestamp"))
        con_trimestre = [c for c in capturas if c.trimestre is not None]
        lineas.append(f"- Total de capturas de **archivos de datos** (no HTML): **{len(capturas)}**")
        if timestamps:
            lineas.append(f"- Rango de fechas: {timestamps[0]} – {timestamps[-1]}")
        lineas.append(f"- Mimetypes encontrados: {', '.join(mimetypes) if mimetypes else '(desconocido)'}")
        lineas.append(
            f"- De esas, **{len(con_trimestre)}** declaran trimestre explícito en el nombre "
            "(las únicas que cuentan para la puerta de decisión)."
        )
    else:
        lineas.append("- No se recuperó ninguna captura de archivo de datos (ver detalle de bloqueo arriba si aplica).")
    lineas.append("")
    return lineas


def _seccion_espejo(resultados: list[ResultadoProbe]) -> list[str]:
    lineas = ["## Fuente 2 — Espejos: resultado", ""]
    espejo = [r for r in resultados if r.fuente == "espejo"]
    for r in espejo:
        estado = "✅ encontrado" if r.existe else "❌ no encontrado"
        detalle = f" -- {r.error}" if r.error else ""
        lineas.append(f"- `{r.metodo}` `{r.url}`: {estado}{detalle}")
    lineas.append("")
    return lineas
