"""Tests de las funciones puras de manifest.py -- sin red."""

from __future__ import annotations

import hashlib
import io

import pandas as pd

from opa.manifest import (
    RegistroManifiesto,
    calcular_header_hash,
    calcular_sha256,
    cargar_manifiesto,
    claves_ya_ingeridas,
    construir_snapshot_id,
    inspeccionar_columnas,
    nombre_archivo_bronze,
    slug_desde_url,
)


def test_calcular_sha256_coincide_con_hashlib() -> None:
    contenido = b"CVE_CARTERA,NOMBRE_PPI\n123,Proyecto X\n"
    assert calcular_sha256(contenido) == hashlib.sha256(contenido).hexdigest()


def test_inspeccionar_columnas_csv() -> None:
    contenido = b"CVE_CARTERA,NOMBRE_PPI,CICLO\n123,Proyecto X,2019\n456,Proyecto Y,2019\n"
    columnas, encoding = inspeccionar_columnas(contenido, "csv")
    assert columnas == ["CVE_CARTERA", "NOMBRE_PPI", "CICLO"]
    # utf-8-sig se prueba primero y decodifica utf-8 sin BOM igual de bien -- correcto.
    assert encoding == "utf-8-sig"


def test_inspeccionar_columnas_csv_latin1() -> None:
    contenido = "CVE_CARTERA,DESCRIPCIÓN\n123,Región Sur\n".encode("latin-1")
    columnas, encoding = inspeccionar_columnas(contenido, "csv")
    assert columnas == ["CVE_CARTERA", "DESCRIPCIÓN"]
    assert encoding == "latin-1"


def test_inspeccionar_columnas_xlsx() -> None:
    buf = io.BytesIO()
    pd.DataFrame({"CVE_CARTERA": ["123"], "NOMBRE_PPI": ["Proyecto X"]}).to_excel(buf, index=False)
    columnas, encoding = inspeccionar_columnas(buf.getvalue(), "xlsx")
    assert columnas == ["CVE_CARTERA", "NOMBRE_PPI"]
    assert encoding is None  # binario, no aplica encoding de texto


def test_inspeccionar_columnas_extension_no_soportada() -> None:
    columnas, encoding = inspeccionar_columnas(b"cualquier cosa", "json")
    assert columnas is None
    assert encoding is None


def test_inspeccionar_columnas_binario_arbitrario_no_lanza() -> None:
    """Contrato clave: un binario real (no CSV/XLSX) nunca debe tumbar la ingesta de bronze --
    en el peor caso devuelve columnas "de la mejor manera posible" o None, nunca una excepción."""
    columnas, encoding = inspeccionar_columnas(b"\x00\x01\xff\xfe binario real, no es un csv valido", "csv")
    assert columnas is None or isinstance(columnas, list)
    assert encoding is not None  # latin-1 decodifica cualquier secuencia de bytes -- último recurso


def test_calcular_header_hash_es_deterministico() -> None:
    h1 = calcular_header_hash(["CVE_CARTERA", "NOMBRE_PPI"])
    h2 = calcular_header_hash(["CVE_CARTERA", "NOMBRE_PPI"])
    h3 = calcular_header_hash(["CVE_CARTERA", "NOMBRE_PPI", "CICLO"])
    assert h1 == h2
    assert h1 != h3


def test_calcular_header_hash_vacio_o_none_es_none() -> None:
    assert calcular_header_hash(None) is None
    assert calcular_header_hash([]) is None


def test_slug_desde_url() -> None:
    assert slug_desde_url("https://x.mx/work/models/PTP/OPA/2019/opa_concluidos.csv") == "opa_concluidos"
    assert slug_desde_url("https://x.mx/a/b/row-down-opa.json") == "row_down_opa"


def test_construir_snapshot_id_trimestral() -> None:
    assert construir_snapshot_id(2019, 3, "a3f91c02deadbeef") == "2019Q3_a3f91c02"


def test_construir_snapshot_id_anual() -> None:
    assert construir_snapshot_id(2015, None, "a3f91c02deadbeef") == "2015_anual_a3f91c02"


def test_construir_snapshot_id_auxiliar() -> None:
    snapshot_id = construir_snapshot_id(None, None, "a3f91c02deadbeef", slug="diccionario_opa")
    assert snapshot_id == "aux_diccionario_opa_a3f91c02"


def test_nombre_archivo_bronze_trimestral() -> None:
    assert nombre_archivo_bronze(2019, 3, "a3f91c02deadbeef", "csv") == "opa_2019_3_a3f91c02.csv"


def test_nombre_archivo_bronze_anual() -> None:
    assert nombre_archivo_bronze(2015, None, "a3f91c02deadbeef", "CSV") == "opa_2015_anual_a3f91c02.csv"


def test_nombre_archivo_bronze_auxiliar() -> None:
    nombre = nombre_archivo_bronze(None, None, "a3f91c02deadbeef", "xlsx", slug="diccionario_opa")
    assert nombre == "opa_aux_diccionario_opa_a3f91c02.xlsx"


def test_nombre_archivo_bronze_es_direccionable_por_contenido() -> None:
    """Mismo hash -> mismo nombre, sin importar la URL de origen -- eso es lo que hace que
    re-correr bronze sea idempotente sin lógica de dedupe aparte (regla dura: nunca se reescribe)."""
    a = nombre_archivo_bronze(2019, 3, "a3f91c02deadbeef", "csv")
    b = nombre_archivo_bronze(2019, 3, "a3f91c02deadbeef", "csv")
    assert a == b


def test_registro_manifiesto_roundtrip(tmp_path) -> None:
    registro = RegistroManifiesto(
        snapshot_id="2019Q3_a3f91c02",
        url="https://x.mx/OPA/2019/OPATercerTrimestre2019.csv",
        origen="vivo",
        fecha_descarga="2026-08-08",
        http_status=200,
        sha256="a3f91c02" * 8,
        bytes=1234,
        corte_declarado={"anio": 2019, "trimestre": 3},
        archivo_bronze="opa_2019_3_a3f91c02.csv",
        header_hash="7d2e" * 16,
        n_columnas=47,
        encoding_detectado="utf-8",
    )
    ruta = tmp_path / "manifest.jsonl"
    ruta.write_text(registro.to_json_line() + "\n", encoding="utf-8")

    recargados = cargar_manifiesto(ruta)
    assert len(recargados) == 1
    assert recargados[0] == registro


def test_cargar_manifiesto_archivo_inexistente_devuelve_vacio(tmp_path) -> None:
    assert cargar_manifiesto(tmp_path / "no_existe.jsonl") == []


def test_claves_ya_ingeridas() -> None:
    registros = [
        RegistroManifiesto(
            snapshot_id="2019Q3_a3f91c02",
            url="https://x.mx/a.csv",
            origen="vivo",
            fecha_descarga="2026-08-08",
            http_status=200,
            sha256="a" * 64,
            bytes=1,
            corte_declarado={"anio": 2019, "trimestre": 3},
            archivo_bronze="opa_2019_3_aaaaaaaa.csv",
        )
    ]
    claves = claves_ya_ingeridas(registros)
    assert claves == {("https://x.mx/a.csv", 2019, 3)}
    assert ("https://x.mx/a.csv", 2019, 4) not in claves
