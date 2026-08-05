"""Tests de las funciones puras de discovery.py -- sin red."""

from __future__ import annotations

from pathlib import Path

import httpx

from opa.discovery import (
    ResultadoProbe,
    _es_error_de_conexion,
    _llamar_con_reintentos,
    _parsear_respuesta_curl,
    calcular_recuperabilidad,
    cargar_resultados,
    clasificar_captura,
    construir_cobertura_anual_generica,
    construir_matriz_trimestral,
    es_error_cadena_tls,
    generar_urls_vivas,
    recomendar,
)

CFG_MINIMA = {
    "anios": {"desde": 2017, "hasta": 2018},
    "fuente_viva": {
        "base_url": "https://example.mx",
        "patrones": [
            "/OPA/{anio}/proyectos_opa.csv",
            "/OPA/{anio}/proyectos_opa_0{n}t{anio}.csv",
            "/OPA/{anio}/reporteOPA{ord}Trimestre.xlsx",
            "/OPA/{anio}/reporteOPA{ord}Trimestre_V{v}.xlsx",
        ],
        "trimestre_n": [1, 2, 3, 4],
        "trimestre_ord": ["1er", "2do", "3er", "4to"],
        "version_v": [2, 3],
        "auxiliares": ["/aux/diccionario_opa.xlsx"],
    },
}


def test_generar_urls_vivas_cuenta_producto_cartesiano() -> None:
    urls = list(generar_urls_vivas(CFG_MINIMA))
    # 2 años x (1 anual + 4 trimestral_numerico + 4 ordinal + 4*2 ordinal_v) + 1 auxiliar
    esperado = 2 * (1 + 4 + 4 + 8) + 1
    assert len(urls) == esperado


def test_generar_urls_vivas_asigna_trimestre_correcto() -> None:
    urls = list(generar_urls_vivas(CFG_MINIMA))
    trimestrales = [u for u in urls if "proyectos_opa_02t" in u[0]]
    assert len(trimestrales) == 2  # uno por año
    assert all(t[2] == 2 for t in trimestrales)


def test_generar_urls_vivas_auxiliar_sin_anio_ni_trimestre() -> None:
    urls = list(generar_urls_vivas(CFG_MINIMA))
    auxiliares = [u for u in urls if u[3] == "auxiliar"]
    assert len(auxiliares) == 1
    assert auxiliares[0][1] is None
    assert auxiliares[0][2] is None
    assert auxiliares[0][0] == "https://example.mx/aux/diccionario_opa.xlsx"


def test_clasificar_captura_trimestral_numerico() -> None:
    url = (
        "http://www.transparenciapresupuestaria.gob.mx/work/models/PTP/DatosAbiertos/OPA/2017/proyectos_opa_01t2017.csv"
    )
    anio, trimestre, patron = clasificar_captura(url)
    assert (anio, trimestre, patron) == (2017, 1, "trimestral_numerico")


def test_clasificar_captura_trimestral_ordinal() -> None:
    url = "https://www.transparenciapresupuestaria.gob.mx/work/models/PTP/DatosAbiertos/OPA/2018/reporteOPA3erTrimestre_V3.xlsx"
    anio, trimestre, patron = clasificar_captura(url)
    assert (anio, trimestre, patron) == (2018, 3, "trimestral_ordinal")


def test_clasificar_captura_anual_generico_no_asigna_trimestre() -> None:
    # Caso real observado por curl contra la CDX API.
    url = "http://www.transparenciapresupuestaria.gob.mx/work/models/PTP/DatosAbiertos/OPA/2016/Proyectos_OPA.csv"
    anio, trimestre, patron = clasificar_captura(url)
    assert anio == 2016
    assert trimestre is None
    assert patron == "anual_generico"


def test_clasificar_captura_patron_antiguo() -> None:
    url = "http://www.transparenciapresupuestaria.gob.mx/work/models/PTP/OPA/2015/Proyectos_OPA.csv"
    anio, trimestre, patron = clasificar_captura(url)
    assert (anio, trimestre, patron) == (2015, None, "anual_generico_antiguo")


def test_clasificar_captura_no_reconocido() -> None:
    anio, trimestre, patron = clasificar_captura("https://example.mx/algo/no/relacionado.pdf")
    assert (anio, trimestre, patron) == (None, None, "no_reconocido")


def _probe(anio: int, trimestre: int, fuente: str, patron: str = "trimestral_numerico") -> ResultadoProbe:
    return ResultadoProbe(
        fuente=fuente,
        url="x",
        metodo="HEAD",
        status=200,
        anio=anio,
        trimestre=trimestre,
        patron=patron,
        existe=True,
    )


def test_matriz_prioriza_vivo_sobre_wayback() -> None:
    resultados = [_probe(2017, 1, "wayback"), _probe(2017, 1, "vivo")]
    matriz = construir_matriz_trimestral(resultados, 2017, 2017)
    assert matriz[(2017, 1)] == "vivo"


def test_matriz_marca_hueco_sin_resultados() -> None:
    matriz = construir_matriz_trimestral([], 2017, 2017)
    assert all(v == "hueco" for v in matriz.values())
    assert len(matriz) == 4


def test_matriz_excluye_patron_anual_generico() -> None:
    resultados = [_probe(2017, None, "vivo", patron="anual_generico")]
    matriz = construir_matriz_trimestral(resultados, 2017, 2017)
    assert all(v == "hueco" for v in matriz.values())


def test_cobertura_anual_generica_solo_cuenta_patron_generico() -> None:
    resultados = [
        _probe(2017, None, "vivo", patron="anual_generico"),
        _probe(2018, 1, "vivo", patron="trimestral_numerico"),
    ]
    anual = construir_cobertura_anual_generica(resultados, 2017, 2018)
    assert anual[2017] == "vivo"
    assert anual[2018] == "hueco"  # el hit de 2018 es trimestral, no genérico


def test_calcular_recuperabilidad_completa() -> None:
    matriz = {(anio, t): "vivo" for anio in range(2016, 2025) for t in (1, 2, 3, 4)}
    recuperables, total, pct = calcular_recuperabilidad(matriz)
    assert (recuperables, total, pct) == (36, 36, 100.0)


def test_calcular_recuperabilidad_vacia() -> None:
    recuperables, total, pct = calcular_recuperabilidad({})
    assert (recuperables, total, pct) == (0, 36, 0.0)


def test_recomendar_umbral_alto() -> None:
    assert "completo" in recomendar(70.0)
    assert "completo" in recomendar(85.0)


def test_recomendar_umbral_medio() -> None:
    assert "parcial" in recomendar(50.0)
    assert "parcial" in recomendar(69.9)


def test_recomendar_umbral_bajo() -> None:
    assert "anual" in recomendar(49.9)
    assert "anual" in recomendar(0.0)


def test_resultado_probe_to_json_line_aplana_extra() -> None:
    r = ResultadoProbe(
        fuente="wayback",
        url="x",
        metodo="WAYBACK_CAPTURE",
        status=200,
        extra={"wayback_timestamp": "20190101000000"},
    )
    linea = r.to_json_line()
    assert '"wayback_timestamp": "20190101000000"' in linea
    assert '"extra"' not in linea


def test_cargar_resultados_es_inverso_de_to_json_line(tmp_path) -> None:
    original = ResultadoProbe(
        fuente="wayback",
        url="x",
        metodo="WAYBACK_CAPTURE",
        status=200,
        anio=2018,
        trimestre=3,
        extra={"wayback_timestamp": "20190101000000", "digest": "abc"},
    )
    ruta = tmp_path / "discovery.jsonl"
    ruta.write_text(original.to_json_line() + "\n", encoding="utf-8")

    (recuperado,) = cargar_resultados(ruta)

    assert recuperado.fuente == original.fuente
    assert recuperado.anio == 2018
    assert recuperado.trimestre == 3
    assert recuperado.extra == {"wayback_timestamp": "20190101000000", "digest": "abc"}


def test_es_error_de_conexion_distingue_ssl_de_negativo_real() -> None:
    assert _es_error_de_conexion("ConnectError: [SSL: CERTIFICATE_VERIFY_FAILED] ...") is True
    assert _es_error_de_conexion("dataset no encontrado con este id") is False
    assert _es_error_de_conexion(None) is False


def test_es_error_cadena_tls_detecta_caso_real_gob_mx() -> None:
    mensaje = (
        "ConnectError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: "
        "unable to get local issuer certificate (_ssl.c:1010)"
    )
    assert es_error_cadena_tls(mensaje) is True
    assert es_error_cadena_tls("ConnectTimeout: timed out") is False
    assert es_error_cadena_tls(None) is False


def test_parsear_respuesta_curl_toma_el_ultimo_bloque_tras_redireccion(tmp_path) -> None:
    ruta = tmp_path / "headers.txt"
    ruta.write_text(
        "HTTP/1.1 301 Moved Permanently\r\nLocation: https://x/y\r\n\r\n"
        "HTTP/2 200\r\nContent-Type: text/csv\r\nContent-Length: 42\r\n\r\n",
        encoding="utf-8",
    )
    status, headers = _parsear_respuesta_curl(ruta)
    assert status == 200
    assert headers["content-type"] == "text/csv"
    assert headers["content-length"] == "42"


def test_parsear_respuesta_curl_sin_archivo() -> None:
    assert _parsear_respuesta_curl(Path("/no/existe/nada.txt")) == (None, {})


def test_llamar_con_reintentos_no_reintenta_cadena_tls_incompleta() -> None:
    llamadas = []

    def falla_siempre():
        llamadas.append(1)
        raise httpx.HTTPError(
            "ConnectError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: "
            "unable to get local issuer certificate"
        )

    resultado, intentos, error = _llamar_con_reintentos(falla_siempre, max_intentos=3, backoff_base=0.01)
    assert resultado is None
    assert intentos == 1
    assert len(llamadas) == 1
    assert error is not None and "CERTIFICATE_VERIFY_FAILED" in error


def test_llamar_con_reintentos_si_reintenta_error_transitorio() -> None:
    llamadas = []

    def falla_dos_veces_y_luego_ok():
        llamadas.append(1)
        if len(llamadas) < 3:
            raise httpx.HTTPError("ConnectTimeout: timed out")
        return "ok"

    resultado, intentos, error = _llamar_con_reintentos(falla_dos_veces_y_luego_ok, max_intentos=3, backoff_base=0.01)
    assert resultado == "ok"
    assert intentos == 3
    assert error is None
