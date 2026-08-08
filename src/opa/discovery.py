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
import subprocess
import tempfile
import time
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass, field, fields
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


_CAMPOS_RESULTADO_PROBE = {f.name for f in fields(ResultadoProbe)} - {"extra"}


def cargar_resultados(ruta: Path) -> list[ResultadoProbe]:
    """Reconstruye los ``ResultadoProbe`` de un ``discovery.jsonl`` ya escrito -- sin volver a tocar la red.

    Inverso de :meth:`ResultadoProbe.to_json_line`: útil para regenerar
    ``cobertura.md`` a partir de una corrida ya hecha, por ejemplo tras
    corregir un bug de presentación en el reporte.
    """
    resultados = []
    with ruta.open(encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea:
                continue
            datos = json.loads(linea)
            conocidos = {k: v for k, v in datos.items() if k in _CAMPOS_RESULTADO_PROBE}
            extra = {k: v for k, v in datos.items() if k not in _CAMPOS_RESULTADO_PROBE}
            resultados.append(ResultadoProbe(**conocidos, extra=extra))
    return resultados


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
    no un fallo transitorio. Una cadena TLS incompleta (``es_error_cadena_tls``)
    tampoco se reintenta: es un fallo determinista de httpx/OpenSSL contra ese
    host, no algo que un reintento vaya a arreglar -- se corta de inmediato
    para que el llamador pase al fallback de curl sin gastar el backoff.
    """
    ultimo_error: str | None = None
    for intento in range(1, max_intentos + 1):
        try:
            return func(), intento, None
        except httpx.HTTPError as exc:
            ultimo_error = f"{type(exc).__name__}: {exc}"
            if es_error_cadena_tls(ultimo_error):
                return None, intento, ultimo_error
            if intento < max_intentos:
                time.sleep(backoff_base * (2 ** (intento - 1)))
    return None, max_intentos, ultimo_error


# --------------------------------------------------------------------------
# Fallback de red: curl del sistema para dominios con cadena TLS incompleta
# --------------------------------------------------------------------------
#
# Hallazgo real de esta corrida: transparenciapresupuestaria.gob.mx y
# datos.gob.mx rotaron su intermedio de Let's Encrypt (a "YR1" y "E8"
# respectivamente) pero el servidor sigue sin enviarlo -- httpx/OpenSSL no
# arman la cadena (no hacen "AIA chasing"), mientras que curl sí, vía el
# almacén de confianza del sistema operativo. Confirmado con
# `openssl x509 -noout -text` (extensión Authority Information Access) y
# reproducido con curl -L contra ambos dominios el 2026-08-05. No es un
# bloqueo ni una VPN/proxy: es una cadena de certificados mal servida por
# los propios hosts .gob.mx. No se desactiva verificación TLS en ningún
# punto -- se usa un cliente distinto que sí completa la cadena.

_ERRORES_CADENA_TLS = ("CERTIFICATE_VERIFY_FAILED", "unable to get local issuer certificate")


def es_error_cadena_tls(error: str | None) -> bool:
    """True si el error es específicamente una cadena TLS incompleta (no otro tipo de falla)."""
    return error is not None and any(marca in error for marca in _ERRORES_CADENA_TLS)


def _parsear_respuesta_curl(ruta_headers: Path) -> tuple[int | None, dict[str, str]]:
    """Parsea el archivo de cabeceras que escribe ``curl -D``. Con -L puede haber varios bloques
    (uno por redirección); se usa el último, que corresponde a la respuesta final."""
    if not ruta_headers.exists():
        return None, {}
    texto = ruta_headers.read_text(errors="replace")
    bloques = [b for b in texto.replace("\r\n", "\n").split("\n\n") if b.strip()]
    if not bloques:
        return None, {}
    lineas = bloques[-1].strip().splitlines()
    if not lineas or not lineas[0].startswith("HTTP/"):
        return None, {}
    try:
        status = int(lineas[0].split()[1])
    except (IndexError, ValueError):
        return None, {}
    headers = {}
    for linea in lineas[1:]:
        if ":" in linea:
            clave, _, valor = linea.partition(":")
            headers[clave.strip().lower()] = valor.strip()
    return status, headers


def curl_get(
    url: str,
    user_agent: str,
    timeout: float,
    solo_headers: bool = False,
    headers_extra: dict[str, str] | None = None,
) -> tuple[int | None, dict[str, str], bytes]:
    """GET/HEAD vía el curl del sistema. Único uso: fallback ante ``es_error_cadena_tls``.

    curl completa la cadena de certificados igual que un navegador (usa el
    almacén de confianza del sistema, con "AIA chasing"); sigue verificando
    TLS por completo, solo que con un cliente distinto a httpx/OpenSSL puro.
    """
    with tempfile.TemporaryDirectory() as tmp:
        ruta_headers = Path(tmp) / "headers.txt"
        ruta_body = Path(tmp) / "body.bin"
        args = [
            "curl",
            "-s",
            "-L",
            "-A",
            user_agent,
            "--max-time",
            str(int(timeout)),
            "-D",
            str(ruta_headers),
            "-o",
            str(ruta_body),
        ]
        if solo_headers:
            args.append("-I")
        for clave, valor in (headers_extra or {}).items():
            args += ["-H", f"{clave}: {valor}"]
        args.append(url)
        try:
            subprocess.run(args, capture_output=True, timeout=timeout + 5, check=False)
        except (subprocess.TimeoutExpired, OSError):
            return None, {}, b""

        status, headers = _parsear_respuesta_curl(ruta_headers)
        cuerpo = ruta_body.read_bytes() if ruta_body.exists() else b""
        return status, headers, cuerpo


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
                    yield base + patron.format(anio=anio, n=n), anio, n, "trimestral_numerico"
            elif "{ord}" in patron and "{v}" in patron:
                for ord_ in fv["trimestre_ord"]:
                    for v in fv["version_v"]:
                        yield (
                            base + patron.format(anio=anio, ord=ord_, v=v),
                            anio,
                            ORD_A_TRIMESTRE[ord_],
                            "trimestral_ordinal",
                        )
            elif "{ord}" in patron:
                for ord_ in fv["trimestre_ord"]:
                    yield (
                        base + patron.format(anio=anio, ord=ord_),
                        anio,
                        ORD_A_TRIMESTRE[ord_],
                        "trimestral_ordinal",
                    )
            else:
                # Mismo vocabulario que clasificar_captura(), para que "vivo" y "wayback"
                # sean comparables: el patrón nuevo vive bajo DatosAbiertos/, el antiguo no.
                etiqueta = "anual_generico" if "DatosAbiertos" in patron else "anual_generico_antiguo"
                yield base + patron.format(anio=anio), anio, None, etiqueta

    # Casos especiales (Fase 1b): URLs exactas de un solo año/trimestre, nomenclatura
    # irregular que no sigue ningún patrón parametrizable -- no forman parte del producto
    # cartesiano de arriba, se prueban tal cual con el (anio, trimestre) declarado en config.
    for caso in fv.get("casos_especiales", []):
        yield base + caso["url"], caso["anio"], caso["trimestre"], "caso_especial"

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

    if status is None and es_error_cadena_tls(error):
        limitador.esperar()
        metodo = "GET_RANGE+CURL"
        status_curl, headers_curl, _cuerpo = curl_get(url, cfg_red["user_agent"], timeout, solo_headers=True)
        if status_curl is not None:
            status, headers, error = status_curl, headers_curl, None

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
    contenido: bytes | None = None
    try:
        resp = cliente.get(url, timeout=cfg_red["timeout_segundos"])
        resp.raise_for_status()
        contenido = resp.content
    except httpx.HTTPError as exc:
        error = f"{type(exc).__name__}: {exc}"
        if not es_error_cadena_tls(error):
            console.log(f"[yellow]No se pudo descargar auxiliar {url}: {exc}[/]")
            return
        status_curl, _headers, cuerpo_curl = curl_get(url, cfg_red["user_agent"], cfg_red["timeout_segundos"])
        if status_curl != 200:
            console.log(f"[yellow]No se pudo descargar auxiliar {url} (tampoco vía curl): {error}[/]")
            return
        contenido = cuerpo_curl

    destino_dir.mkdir(parents=True, exist_ok=True)
    nombre = url.rsplit("/", 1)[-1]
    (destino_dir / nombre).write_bytes(contenido)
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


def _get_con_fallback_curl(
    cliente: httpx.Client,
    url: str,
    cfg_red: dict[str, Any],
    params: dict[str, Any] | None = None,
) -> tuple[int | None, bytes, str | None, str]:
    """GET con httpx; si falla por cadena TLS incompleta (ver nota más arriba), reintenta con curl.

    Devuelve ``(status, cuerpo, error, metodo)``.
    """
    max_intentos, backoff, timeout = (
        cfg_red["max_reintentos"],
        cfg_red["backoff_base_segundos"],
        cfg_red["timeout_segundos"],
    )
    resp, _intentos, error = _llamar_con_reintentos(
        lambda: cliente.get(url, params=params, timeout=timeout), max_intentos, backoff
    )
    if resp is not None:
        return resp.status_code, resp.content, None, "API"
    if es_error_cadena_tls(error):
        url_completa = str(httpx.URL(url, params=params)) if params else url
        status_curl, _headers, cuerpo_curl = curl_get(url_completa, cfg_red["user_agent"], timeout)
        if status_curl is not None:
            return status_curl, cuerpo_curl, None, "API+CURL"
    return None, b"", error, "API"


def ejecutar_fuente_espejo(
    cliente: httpx.Client, cfg: dict[str, Any], registrar: Callable[[ResultadoProbe], None]
) -> None:
    """Consulta el mirror CKAN de datos.gob.mx (por id conocido y por nombre) y datamx.io."""
    fe = cfg["fuente_espejo"]
    console.log("Fuente 2 (espejo): CKAN datos.gob.mx + datamx.io")

    # 1. package_show por el id histórico documentado en el dictamen.
    url_show = f"{fe['ckan_base']}/package_show?id={fe['ckan_package_id']}"
    status, cuerpo_bytes, error, metodo = _get_con_fallback_curl(cliente, url_show, cfg["red"])
    existe_show = False
    recursos: list[dict[str, Any]] = []
    if status is not None:
        try:
            cuerpo = json.loads(cuerpo_bytes)
        except json.JSONDecodeError:
            cuerpo = {}
        existe_show = bool(cuerpo.get("success"))
        if existe_show:
            recursos = cuerpo.get("result", {}).get("resources", [])
    registrar(
        ResultadoProbe(
            fuente="espejo",
            url=url_show,
            metodo=metodo,
            status=status,
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

    # 2. Búsqueda de respaldo por nombre, por si el id cambió de lugar. CKAN/Solr hace un
    # match laxo por palabra suelta (ej. "obra" solo ya matchea 21 datasets no relacionados,
    # confirmado manualmente) -- por eso NO basta con count > 0, hay que revisar que algún
    # resultado sea realmente sobre OPA (nombre/título contiene "obra" Y "abiert").
    url_search = f"{fe['ckan_base']}/package_search"
    status2, cuerpo2_bytes, error2, metodo2 = _get_con_fallback_curl(
        cliente, url_search, cfg["red"], params={"q": fe["ckan_busqueda_respaldo"]}
    )
    n_resultados = None
    coincidencia_real = None
    if status2 is not None:
        try:
            resultado_busqueda = json.loads(cuerpo2_bytes).get("result", {})
        except json.JSONDecodeError:
            resultado_busqueda = {}
        n_resultados = resultado_busqueda.get("count")
        for r in resultado_busqueda.get("results", []):
            texto = f"{r.get('name', '')} {r.get('title', '')}".lower()
            if "obra" in texto and "abiert" in texto:
                coincidencia_real = r.get("name")
                break
    registrar(
        ResultadoProbe(
            fuente="espejo",
            url=f"{url_search}?q={fe['ckan_busqueda_respaldo']}",
            metodo=metodo2,
            status=status2,
            existe=coincidencia_real is not None,
            error=error2
            or (
                None if coincidencia_real else f"{n_resultados} resultados por palabra suelta, ninguno es realmente OPA"
            ),
            timestamp_consulta=_ahora_iso(),
            extra={"n_resultados_busqueda": n_resultados, "coincidencia_real": coincidencia_real},
        )
    )

    # 3. datamx.io -- sondeo directo, referenciado en el dictamen como mirror candidato.
    status3, cuerpo3_bytes, error3, metodo3 = _get_con_fallback_curl(cliente, fe["datamx_io"], cfg["red"])
    contiene_opa = False
    if status3 == 200:
        texto = cuerpo3_bytes.decode("utf-8", errors="replace").lower()
        contiene_opa = "opa" in texto and ("obra p" in texto or "inversi" in texto)
    registrar(
        ResultadoProbe(
            fuente="espejo",
            url=fe["datamx_io"],
            metodo=metodo3,
            status=status3,
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
        # Patrón nuevo descubierto en Fase 1 (2026-08): reemplaza a reporteOPA{ord}Trimestre
        # a partir de ~2020. "Concluido(s)" alterna singular/plural sin regla clara por año.
        re.compile(
            r"/OPA/(?P<anio>\d{4})/(Consolidado|Concluidos?|Seguimiento)OPA(?P<ord>1er|2do|3er|4to)Trimestre\d{4}\.csv",
            re.IGNORECASE,
        ),
        "trimestral_nuevo",
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


def _racha_final_hueca(anual: dict[int, str], anio_desde: int, anio_hasta: int) -> int:
    """Cuenta los años consecutivos con hueco al final del rango (posible cambio de patrón de URL)."""
    racha = 0
    for anio in range(anio_hasta, anio_desde - 1, -1):
        if anual.get(anio) != "hueco":
            break
        racha += 1
    return racha


def _anios_con_cobertura_trimestral(matriz: dict[tuple[int, int], str], anio_desde: int, anio_hasta: int) -> set[int]:
    """Años que tienen al menos un trimestre no-hueco en la matriz trimestral."""
    return {
        anio
        for anio in range(anio_desde, anio_hasta + 1)
        if any(matriz[(anio, t)] != "hueco" for t in (1, 2, 3, 4))
    }


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
    racha_final_hueca = _racha_final_hueca(anual, anio_desde, anio_hasta)
    if racha_final_hueca:
        anio_racha_desde = anio_hasta - racha_final_hueca + 1
        anios_con_trimestral = _anios_con_cobertura_trimestral(matriz, anio_desde, anio_hasta)
        if all(anio in anios_con_trimestral for anio in range(anio_racha_desde, anio_hasta + 1)):
            lineas.append(
                f"> ℹ️ **{anio_racha_desde}–{anio_hasta} salen como hueco en este patrón genérico "
                "específico** (sin trimestre en el nombre), con 404 limpios -- pero **no es un hueco "
                "de datos real**: la matriz trimestral de arriba sí tiene cobertura para estos años "
                "bajo otro nombre de archivo (investigado en Fase 1, ver README). El portal retiró "
                "este nombre genérico a favor de archivos con trimestre explícito en el nombre."
            )
        else:
            lineas.append(
                f"> ⚠️ **{anio_racha_desde}–{anio_hasta} salen todos como hueco** en el patrón "
                "genérico conocido, con 404 limpios (no error de red -- ver detalle crudo). Dos "
                "hipótesis quedan abiertas: (a) la SHCP descontinuó OPA en ese punto, o (b) cambió a "
                "un patrón de URL no incluido en `sources.yml`. No se concluye descontinuación sin "
                "antes buscar un patrón nuevo."
            )
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


_ERRORES_DE_CONEXION = ("ConnectError", "ConnectTimeout", "ReadTimeout", "PoolTimeout", "SSLError")


def _es_error_de_conexion(error: str | None) -> bool:
    """Distingue una falla de conexión/TLS (no sabemos si existe) de una respuesta negativa real."""
    return error is not None and any(tipo in error for tipo in _ERRORES_DE_CONEXION)


def _seccion_espejo(resultados: list[ResultadoProbe]) -> list[str]:
    lineas = ["## Fuente 2 — Espejos: resultado", ""]
    espejo = [r for r in resultados if r.fuente == "espejo"]
    hubo_falla_conexion = False
    for r in espejo:
        if _es_error_de_conexion(r.error):
            estado = "⚠️ no se pudo verificar (falla de conexión/TLS, no es una confirmación de ausencia)"
            hubo_falla_conexion = True
        elif r.existe:
            estado = "✅ encontrado"
        else:
            estado = "❌ no encontrado"
        detalle = f" -- {r.error}" if r.error else ""
        lineas.append(f"- `{r.metodo}` `{r.url}`: {estado}{detalle}")
    if hubo_falla_conexion:
        lineas.append("")
        lineas.append(
            "> ⚠️ **Nota de verificación manual:** ante la falla de conexión de arriba, se confirmó "
            "por fuera de este script (`curl`, 2026-08-05) que `www.datos.gob.mx` sí es alcanzable "
            "-- el problema es que su cadena de certificados TLS está incompleta para clientes que no "
            "hacen *AIA chasing* (Python/httpx), no un bloqueo de red. Con `curl` se confirmó "
            "independientemente: el id de CKAN histórico responde `404 No encontrado`, la búsqueda "
            'por nombre "Obra Pública Abierta" da 0 resultados, y la organización '
            "`secretaria_hacienda` tiene 54 datasets en el catálogo actual, ninguno es OPA. "
            "Conclusión: el mirror fue retirado del catálogo, no es un problema de acceso."
        )
    lineas.append("")
    return lineas
