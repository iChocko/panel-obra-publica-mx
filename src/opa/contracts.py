"""Contratos Pandera -- frontera bronze -> silver.

Ver ARQUITECTURA-panel-obra-publica-mx.md sección 6.1 para el contrato original del
dictamen de viabilidad. Ese contrato asumía ``cve_cartera`` como un numérico de 10-11
dígitos (``^\\d{10,11}$``) -- Fase 0 ya había demostrado que eso es falso (0% de las 3
muestras de esa fase lo cumplían). Este módulo es la versión corregida con evidencia real:
valores muestreados de los 128 snapshots archivados en Bronze (Fase 1, 2026-08-08), no de
3 archivos.
"""

from __future__ import annotations

import re

import pandera.pandas as pa
from pandera.typing import Series

# 32,186 valores de cve_cartera muestreados en 2015-2026 (un año representativo por corte,
# excluyendo los 3 snapshots corruptos de 2024 T1 -- ver conf/schema_map.yml):
#   ~99.2% matchean este patrón tras quitar la comilla inicial de Excel (ver
#   limpiar_cve_cartera). El resto (~0.8%) es basura real de la fuente, no un patrón que
#   falte cubrir: valores tipo "020 96 020" (tres grupos de 3 dígitos separados por espacio
#   -- se repiten IDÉNTICOS entre años distintos, consistentes con un valor
#   sentinela/placeholder del sistema de origen, no con proyectos reales) y notación
#   científica corrupta tipo "8.36E+21" (típico de un autocast de Excel antes de exportar a
#   CSV -- el dato original ya se perdió, irrecuperable). Ambos deben fallar la validación
#   a propósito.
PATRON_CVE_CARTERA = re.compile(r"^[0-9A-Z]{10,11}$")


def limpiar_cve_cartera(valor: str) -> str:
    """Quita la comilla inicial de Excel y normaliza a mayúsculas -- limpieza mínima previa
    a validar, no una transformación de negocio.

    La comilla inicial (``'1218T4L0013``) es el artefacto de Excel "forzar texto": presente
    en 2016-2026, ausente en 2015 (confirmado sobre datos reales). No hace padding de ceros
    ni infiere el formato interno del código -- eso requeriría saber la posición exacta del
    componente numérico en cada variante histórica, que no está confirmado (ver
    conf/schema_map.yml, notas ``[inferido]``). Un valor que no matchea
    ``PATRON_CVE_CARTERA`` después de esta limpieza es responsabilidad del validador, no de
    esta función -- no se oculta aquí.
    """
    return valor.strip().lstrip("'").upper()


def es_cve_cartera_valido(valor: str) -> bool:
    return bool(PATRON_CVE_CARTERA.match(limpiar_cve_cartera(valor)))


class OPASnapshot(pa.DataFrameModel):
    """Contrato de un snapshot silver -- un renglón por PPI observado en un corte.

    Todos los campos de abajo están corregidos contra evidencia real de los 128 snapshots
    bronze (Fase 2, 2026-08-08), no contra la forma que asumía el dictamen de viabilidad:

    - ``cve_cartera``: alfanumérico de 10-11 caracteres (ver ``PATRON_CVE_CARTERA``), NO el
      numérico de 10-11 dígitos que asumía el dictamen original.
    - ``anio``: nullable -- ~20% de las filas lo traen vacío incluso en el esquema moderno
      (368/1786 filas verificado sobre un snapshot real de 2021). ``ciclo`` suele estar
      poblado cuando ``anio`` no lo está, pero no son intercambiables a ciegas (ver
      ``columnas_canonicas`` en ``conf/schema_map.yml``).
    - ``avance_fisico``: rango real observado -3.79 a 100.05 (196,910 filas de 2015-2026,
      esquema moderno y viejo combinados). El rango semántico correcto sigue siendo [0, 100]
      A PROPÓSITO: los excesos son ruido de captura/redondeo real que el contrato debe
      señalar, no silenciar ensanchando el rango para que todo pase.
    - ``latitud``/``longitud``: el bbox de México del dictamen original (14.5-32.8 /
      -118.5 a -86.7) sigue haciendo falta -- se confirmaron valores basura reales en la
      misma columna (latitud hasta 436117.0, longitud hasta -115,459,917.0) que romperían
      cualquier geocodificación aguas abajo si no se filtran aquí.
    - ``monto_total_inversion``: sin cambios respecto al dictamen original (``>= 0``,
      nullable) -- el máximo real observado (~1.7 billones de pesos) es consistente con un
      megaproyecto de infraestructura agregado, no con un error de unidades.
    """

    cve_cartera: Series[str] = pa.Field(str_matches=PATRON_CVE_CARTERA.pattern, nullable=False)
    anio: Series[float] = pa.Field(ge=2008, le=2030, nullable=True)
    avance_fisico: Series[float] = pa.Field(ge=0, le=100, nullable=True)
    latitud: Series[float] = pa.Field(ge=14.5, le=32.8, nullable=True)
    longitud: Series[float] = pa.Field(ge=-118.5, le=-86.7, nullable=True)
    monto_total_inversion: Series[float] = pa.Field(ge=0, nullable=True)

    class Config:
        strict = False  # el contrato valida un subconjunto de columnas; el resto pasa tal cual.
        coerce = True


# NOTA (Fase 2, 2026-08-08): el dictamen original proponía además un dataframe_check
# "ejercido <= modificado * 1.05" (tolerancia del 5%) como prueba de coherencia de montos.
# Se probó contra datos reales (opa_2021_anual_48a4c666.csv, 1499 filas evaluables con
# ambas columnas pobladas) y **falla en el 18.5% de las filas** (278/1499) -- varias por
# márgenes enormes, no por ruido de redondeo: ej. EJERCIDO=277,987,437 vs
# MODIFICADO=357,938 (777x, no 5%). No se incluye ese check en OPASnapshot todavía. Antes de
# activarlo hay que resolver una pregunta de semántica de campo, no de tolerancia numérica:
# si EJERCIDO es el acumulado desde el inicio del proyecto y MODIFICADO es el presupuesto
# del ciclo/corte vigente, compararlos directo no tiene sentido y el check está mal
# planteado, no los datos. Pendiente para Fase 3 -- no se adivina la respuesta aquí.
