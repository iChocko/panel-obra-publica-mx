"""Tests de normalize.py -- hermético, sin depender de data/bronze/ real (no está en git)."""

from __future__ import annotations

import pandas as pd
import pytest

from opa.manifest import RegistroManifiesto
from opa.normalize import (
    ejecutar_normalizacion,
    normalizar_snapshot,
    parsear_fecha_mes,
)

# --------------------------------------------------------------------------
# parsear_fecha_mes -- las 4 formas reales encontradas en el corpus bronze
# --------------------------------------------------------------------------


def test_parsear_fecha_iso_con_hora() -> None:
    # xlsx con fecha nativa de Excel leída como texto (2018 T3).
    assert parsear_fecha_mes("2003-01-01 00:00:00") == pd.Timestamp(2003, 1, 1)


def test_parsear_fecha_dmy_moderno() -> None:
    # El "día" en DD/MM/YYYY es siempre "01" en datos reales -- no se inventa un día distinto.
    assert parsear_fecha_mes("01/12/2002") == pd.Timestamp(2002, 12, 1)


def test_parsear_fecha_mes_abreviado_anio_2_digitos() -> None:
    # 2016: "mar-06".
    assert parsear_fecha_mes("mar-06") == pd.Timestamp(2006, 3, 1)


def test_parsear_fecha_mes_completo_anio_4_digitos() -> None:
    # 2015/2017/2018: "Enero/2001".
    assert parsear_fecha_mes("Enero/2001") == pd.Timestamp(2001, 1, 1)
    assert parsear_fecha_mes("octubre/2011") == pd.Timestamp(2011, 10, 1)


def test_parsear_fecha_nulo_o_vacio() -> None:
    assert parsear_fecha_mes(None) is None
    assert parsear_fecha_mes(float("nan")) is None
    assert parsear_fecha_mes("") is None
    assert parsear_fecha_mes("nan") is None


def test_parsear_fecha_formato_no_reconocido_no_se_adivina() -> None:
    assert parsear_fecha_mes("hace como dos años") is None
    assert parsear_fecha_mes("2020") is None


# --------------------------------------------------------------------------
# normalizar_snapshot -- fixtures sintéticos que imitan esquemas reales
# --------------------------------------------------------------------------

SCHEMA_MAP_PRUEBA = {
    "esquemas": {
        "hash_moderno": {
            "columnas": {
                "CVE_CARTERA": "cve_cartera",
                "ANIO": "anio",
                "AVANCE_FISICO": "avance_fisico",
                "LATITUD": "latitud",
                "LONGITUD": "longitud",
                "MONTO_TOTAL_INVERSION": "monto_total_inversion",
            },
        },
        "hash_viejo_sin_seguimiento": {
            # Imita la variante real de 2016 sin MODIFICADO/EJERCIDO/AVANCE_FISICO.
            "columnas": {
                "CVE_PPI": "cve_cartera",
                "ANIO": "anio",
                "LATITUD_INICIAL": "latitud",
                "LONGITUD_INICIAL": "longitud",
                "MONTO_TOTAL_INVERSION": "monto_total_inversion",
            },
        },
    },
    "snapshots_conocidos_corruptos": [
        {"archivo_bronze": "corrupto.csv", "url": "https://x.mx/corrupto.csv", "razon": "prueba"},
    ],
}


def _registro(
    archivo_bronze: str, header_hash: str, anio: int = 2021, trimestre: int | None = None
) -> RegistroManifiesto:
    return RegistroManifiesto(
        snapshot_id=f"{anio}_{trimestre or 'anual'}_prueba",
        url=f"https://x.mx/{archivo_bronze}",
        origen="vivo",
        fecha_descarga="2026-08-08",
        http_status=200,
        sha256="a" * 64,
        bytes=100,
        corte_declarado={"anio": anio, "trimestre": trimestre},
        archivo_bronze=archivo_bronze,
        header_hash=header_hash,
        encoding_detectado="utf-8",
    )


def test_normalizar_snapshot_esquema_desconocido(tmp_path) -> None:
    registro = _registro("no_mapeado.csv", "hash_que_no_existe")
    resultado = normalizar_snapshot(registro, SCHEMA_MAP_PRUEBA, dir_bronze=tmp_path, dir_silver=tmp_path)
    assert resultado.estado == "esquema_desconocido"


def test_normalizar_snapshot_corrupto_conocido(tmp_path) -> None:
    registro = _registro("corrupto.csv", "hash_moderno")
    resultado = normalizar_snapshot(registro, SCHEMA_MAP_PRUEBA, dir_bronze=tmp_path, dir_silver=tmp_path)
    assert resultado.estado == "corrupto_conocido"


def test_normalizar_snapshot_archivo_faltante(tmp_path) -> None:
    registro = _registro("no_existe_en_disco.csv", "hash_moderno")
    resultado = normalizar_snapshot(registro, SCHEMA_MAP_PRUEBA, dir_bronze=tmp_path, dir_silver=tmp_path)
    assert resultado.estado == "error"
    assert "no existe" in resultado.detalle_error


def test_normalizar_snapshot_esquema_moderno_valido(tmp_path) -> None:
    (tmp_path / "moderno.csv").write_text(
        "CVE_CARTERA,ANIO,AVANCE_FISICO,LATITUD,LONGITUD,MONTO_TOTAL_INVERSION\n"
        "'1218T4L0013,2021,45.5,19.43,-99.13,1000000\n"
        "'1409J3D0002,2021,100.0,25.68,-100.31,0\n",
        encoding="utf-8",
    )
    registro = _registro("moderno.csv", "hash_moderno")
    resultado = normalizar_snapshot(registro, SCHEMA_MAP_PRUEBA, dir_bronze=tmp_path, dir_silver=tmp_path)

    assert resultado.estado == "ok"
    assert resultado.filas_totales == 2
    assert resultado.filas_validas == 2
    assert resultado.filas_rechazadas == 0
    assert resultado.ruta_parquet.exists()

    df = pd.read_parquet(resultado.ruta_parquet)
    assert df["cve_cartera"].tolist() == ["1218T4L0013", "1409J3D0002"]  # comilla quitada
    assert (df["snapshot_id"] == registro.snapshot_id).all()


def test_normalizar_snapshot_coordenada_cero_se_trata_como_nula_no_como_basura(tmp_path) -> None:
    """Hallazgo real (Fase 2): 48.6% de LATITUD_INICIAL en 2015 es literalmente '0' -- un
    centinela de "sin coordenadas", no un valor real fuera del bbox de México. Si se coerciona
    a 0.0 y se valida tal cual, rechaza masivamente filas que en realidad solo no tienen
    geocodificación."""
    (tmp_path / "viejo.csv").write_text(
        "CVE_PPI,ANIO,LATITUD_INICIAL,LONGITUD_INICIAL,MONTO_TOTAL_INVERSION\n"
        "14048120002,2016,0,0,500000\n"  # sin coordenadas -- no debe rechazarse por eso
        "14096500013,2016,19.43,-99.13,750000\n",
        encoding="utf-8",
    )
    registro = _registro("viejo.csv", "hash_viejo_sin_seguimiento", anio=2016)
    resultado = normalizar_snapshot(registro, SCHEMA_MAP_PRUEBA, dir_bronze=tmp_path, dir_silver=tmp_path)

    assert resultado.estado == "ok"
    assert resultado.filas_rechazadas == 0
    df = pd.read_parquet(resultado.ruta_parquet)
    assert df["latitud"].isna().sum() == 1
    assert df["longitud"].isna().sum() == 1


def test_normalizar_snapshot_columnas_faltantes_del_esquema_viejo_se_agregan_vacias(tmp_path) -> None:
    """El esquema hash_viejo_sin_seguimiento no tiene avance_fisico -- el contrato lo exige,
    así que debe agregarse como columna vacía (nula), no fallar por columna ausente."""
    (tmp_path / "viejo2.csv").write_text(
        "CVE_PPI,ANIO,LATITUD_INICIAL,LONGITUD_INICIAL,MONTO_TOTAL_INVERSION\n14048120002,2016,19.43,-99.13,500000\n",
        encoding="utf-8",
    )
    registro = _registro("viejo2.csv", "hash_viejo_sin_seguimiento", anio=2016)
    resultado = normalizar_snapshot(registro, SCHEMA_MAP_PRUEBA, dir_bronze=tmp_path, dir_silver=tmp_path)

    assert resultado.estado == "ok"
    df = pd.read_parquet(resultado.ruta_parquet)
    assert "avance_fisico" in df.columns
    assert df["avance_fisico"].isna().all()


def test_normalizar_snapshot_rechaza_cve_cartera_basura_sin_tumbar_el_resto(tmp_path) -> None:
    (tmp_path / "mixto.csv").write_text(
        "CVE_CARTERA,ANIO,AVANCE_FISICO,LATITUD,LONGITUD,MONTO_TOTAL_INVERSION\n"
        "'001 02 001,2021,50,19.43,-99.13,1000\n"  # centinela real, debe rechazarse
        "'1218T4L0013,2021,50,19.43,-99.13,1000\n",  # válido
        encoding="utf-8",
    )
    registro = _registro("mixto.csv", "hash_moderno")
    resultado = normalizar_snapshot(registro, SCHEMA_MAP_PRUEBA, dir_bronze=tmp_path, dir_silver=tmp_path)

    assert resultado.filas_totales == 2
    assert resultado.filas_validas == 1
    assert resultado.filas_rechazadas == 1
    df = pd.read_parquet(resultado.ruta_parquet)
    assert df["cve_cartera"].tolist() == ["1218T4L0013"]


# --------------------------------------------------------------------------
# ejecutar_normalizacion -- orquestación + deduplicación por snapshot_id
# --------------------------------------------------------------------------


def test_ejecutar_normalizacion_deduplica_mismo_snapshot_id(tmp_path) -> None:
    """Caso real: el mismo contenido (mismo sha256) descubierto por 'vivo' y 'wayback' a la
    vez produce dos renglones de manifiesto con el mismo snapshot_id -- no debe procesarse
    dos veces."""
    (tmp_path / "moderno.csv").write_text(
        "CVE_CARTERA,ANIO,AVANCE_FISICO,LATITUD,LONGITUD,MONTO_TOTAL_INVERSION\n'1218T4L0013,2021,50,19.43,-99.13,1000\n",
        encoding="utf-8",
    )
    ruta_schema_map = tmp_path / "schema_map.yml"
    import yaml

    ruta_schema_map.write_text(yaml.dump(SCHEMA_MAP_PRUEBA), encoding="utf-8")

    ruta_manifest = tmp_path / "manifest.jsonl"
    r1 = _registro("moderno.csv", "hash_moderno")
    r2 = _registro("moderno.csv", "hash_moderno")  # mismo snapshot_id, otra "fuente"
    ruta_manifest.write_text(r1.to_json_line() + "\n" + r2.to_json_line() + "\n", encoding="utf-8")

    resultados = ejecutar_normalizacion(
        ruta_manifest=ruta_manifest, ruta_schema_map=ruta_schema_map, dir_bronze=tmp_path, dir_silver=tmp_path
    )
    assert len(resultados) == 1


def test_ejecutar_normalizacion_omite_auxiliares_sin_anio(tmp_path) -> None:
    ruta_schema_map = tmp_path / "schema_map.yml"
    import yaml

    ruta_schema_map.write_text(yaml.dump(SCHEMA_MAP_PRUEBA), encoding="utf-8")

    registro_aux = RegistroManifiesto(
        snapshot_id="aux_diccionario_aaaaaaaa",
        url="https://x.mx/diccionario.xlsx",
        origen="vivo",
        fecha_descarga="2026-08-08",
        http_status=200,
        sha256="b" * 64,
        bytes=10,
        corte_declarado={"anio": None, "trimestre": None},
        archivo_bronze="diccionario.xlsx",
    )
    ruta_manifest = tmp_path / "manifest.jsonl"
    ruta_manifest.write_text(registro_aux.to_json_line() + "\n", encoding="utf-8")

    resultados = ejecutar_normalizacion(
        ruta_manifest=ruta_manifest, ruta_schema_map=ruta_schema_map, dir_bronze=tmp_path, dir_silver=tmp_path
    )
    assert resultados == []


@pytest.fixture(autouse=True)
def _sin_advertencias_pandas():
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        yield
