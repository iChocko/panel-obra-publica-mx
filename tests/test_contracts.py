"""Tests del contrato Pandera -- validados contra valores reales encontrados en Fase 2
(2026-08-08), no contra valores inventados a mano."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pandera.errors
import pytest

from opa.contracts import OPASnapshot, es_cve_cartera_valido, limpiar_cve_cartera


def test_limpiar_cve_cartera_quita_comilla_inicial() -> None:
    # Artefacto real de Excel "forzar texto", presente 2016-2026 (confirmado sobre datos reales).
    assert limpiar_cve_cartera("'1218T4L0013") == "1218T4L0013"


def test_limpiar_cve_cartera_2015_sin_comilla() -> None:
    # 2015 es el único año sin el artefacto -- debe pasar igual, sin romperse.
    assert limpiar_cve_cartera("14048120002") == "14048120002"


def test_limpiar_cve_cartera_normaliza_mayusculas() -> None:
    assert limpiar_cve_cartera("'1218t4l0013") == "1218T4L0013"


@pytest.mark.parametrize(
    "valor_real",
    [
        "'1218T4L0013",  # 2015-2026, muestra real (04 dígitos + 3 letras + 4 dígitos)
        "'14048120002",  # 11 dígitos puros
        "'1318TOQ0033",  # 4 dígitos + 3 letras + 4 dígitos
        "'1409J3D0002",  # 4 dígitos + letra + dígito + letra + 4 dígitos
        "'1411B010001",  # 4 dígitos + letra + 6 dígitos
        "14096500013",  # 2015, sin comilla, 11 dígitos
    ],
)
def test_es_cve_cartera_valido_acepta_formas_reales(valor_real: str) -> None:
    assert es_cve_cartera_valido(valor_real) is True


@pytest.mark.parametrize(
    "valor_anomalo",
    [
        "'001 02 001",  # sentinela/placeholder -- se repite idéntico entre 2015-2019+
        "'020 96 020",  # idem
        "'018 01 016",  # idem
        "8.36E+21",  # notación científica corrupta -- autocast de Excel, dato irrecuperable
        "'1306000",  # longitud corta anómala (7 caracteres)
    ],
)
def test_es_cve_cartera_valido_rechaza_basura_real_de_la_fuente(valor_anomalo: str) -> None:
    """Estos SON basura real encontrada en la fuente (Fase 2, 2026-08-08) -- el contrato
    debe rechazarlos a propósito, no ensancharse para que pasen."""
    assert es_cve_cartera_valido(valor_anomalo) is False


def _df_valido(**overrides) -> pd.DataFrame:
    base = {
        "cve_cartera": ["1218T4L0013", "1409J3D0002"],
        "anio": [2021.0, np.nan],  # anio nullable -- ~20% nulo incluso en datos reales
        "avance_fisico": [45.5, 100.0],
        "latitud": [19.43, 25.68],
        "longitud": [-99.13, -100.31],
        "monto_total_inversion": [1_000_000.0, 0.0],
    }
    base.update(overrides)
    return pd.DataFrame(base)


def test_opasnapshot_acepta_dataframe_valido() -> None:
    OPASnapshot.validate(_df_valido())  # no debe lanzar


def test_opasnapshot_rechaza_cve_cartera_numerico_de_10_11_digitos_puros_si_no_matchea() -> None:
    # Nota: 11 dígitos puros SÍ es una forma válida real (~34% de los casos) -- este test
    # cubre la forma que el dictamen ORIGINAL asumía como la única válida (10 dígitos exactos
    # sin letras) para confirmar que el contrato nuevo la sigue aceptando cuando es real.
    df = _df_valido(cve_cartera=["14048120002", "1409J3D0002"])
    OPASnapshot.validate(df)  # no debe lanzar -- 11 dígitos puros es una forma real válida


def test_opasnapshot_rechaza_cve_cartera_invalido() -> None:
    df = _df_valido(cve_cartera=["001 02 001", "1409J3D0002"])
    with pytest.raises(pandera.errors.SchemaError):
        OPASnapshot.validate(df)


def test_opasnapshot_rechaza_cve_cartera_nulo() -> None:
    df = _df_valido(cve_cartera=[None, "1409J3D0002"])
    with pytest.raises(pandera.errors.SchemaError):
        OPASnapshot.validate(df)


def test_opasnapshot_acepta_anio_nulo() -> None:
    # ~20% de nulos reales en anio -- no debe fallar solo por eso.
    OPASnapshot.validate(_df_valido(anio=[np.nan, np.nan]))


def test_opasnapshot_rechaza_avance_fisico_fuera_de_rango() -> None:
    df = _df_valido(avance_fisico=[150.0, 50.0])
    with pytest.raises(pandera.errors.SchemaError):
        OPASnapshot.validate(df)


def test_opasnapshot_rechaza_latitud_fuera_del_bbox_de_mexico() -> None:
    # Valor real encontrado en Fase 2: hasta 436117.0 en una fila con geocodificación rota.
    df = _df_valido(latitud=[436117.0, 25.68])
    with pytest.raises(pandera.errors.SchemaError):
        OPASnapshot.validate(df)


def test_opasnapshot_rechaza_monto_negativo() -> None:
    df = _df_valido(monto_total_inversion=[-1.0, 0.0])
    with pytest.raises(pandera.errors.SchemaError):
        OPASnapshot.validate(df)
