# Comparación de esquemas — muestras de Fase 0

*Generado por `opa inspect` el 2026-08-05T05:51:05.617012+00:00.*

## antigua: `opa_2015_anual_antigua_vivo.csv` (2015 (anual/genérico))

- Fuente: **vivo** -- `https://www.transparenciapresupuestaria.gob.mx/work/models/PTP/OPA/2015/Proyectos_OPA.csv`
- Formato: csv
- Encoding detectado: utf-8-sig
- Separador: `,` / quotechar: `"`
- Filas: 3140
- Columna de cartera: **NO DETECTADA**
- PPI únicos: 3137
- Columnas (45): `CVE_PPI`, `NOMBRE`, `RAMO`, `DESC_RAMO`, `UNIDAD`, `DESC_UNIDAD`, `TIPO_PPI`, `DESCRIPCION`, `LOCALIZACION`, `CVE_ENTFED`, `ENT_FED`, `LATITUD_INICIAL`, `LONGITUD_INICIAL`, `FECHA_INI_CAL_FISCAL`, `FECHA_FIN_CAL_FISCAL`, `FECHA_INI_FF`, `FECHA_FIN_FF`, `ANIOS_HE`, `NOMBRE_ADMIN`, `AP_MATERNO_ADMIN`, `AP_PATERNO_ADMIN`, `CARGO_ADMIN`, `MAIL_ADMIN`, `TELEFONO_ADMIN`, `META_FISICA`, `META_BENEFICIOS`, `ID_PPI`, `APROBADO`, `MODIFICADO`, `EJERCIDO`, `AVANCE_FISICO`, `GRUPO_FUNCIONAL`, `FUNCION`, `MONTO_TOTAL_INVERSION`, `TOTAL_GASTO_OPERACION_HE`, `TOTAL_GASTO_NO_CONSID`, `COSTO_TOTAL_PPI`, `ANIO`, `MONTO_ASIGAUTACT`, `RECURSOS_ESTATALES`, `RECURSOS_MUNICIPALES`, `PRIVADOS`, `FIDEICOMISO`, `CICLO`, `TIPO_PROYECTO`

## reciente: `opa_2021_anual_reciente_vivo.csv` (2021 (anual/genérico))

- Fuente: **vivo** -- `https://www.transparenciapresupuestaria.gob.mx/work/models/PTP/DatosAbiertos/OPA/2021/proyectos_opa.csv`
- Formato: csv
- Encoding detectado: latin-1
- Separador: `,` / quotechar: `"`
- Filas: 1786
- Columna de cartera detectada: `CVE_CARTERA`
- PPI únicos: 1780
- Rango `cve_cartera`: '001 02 001 – '2151GYN0003
- Formato consistente (`^\d{10,11}$`): no (0.0% válido)
- Columnas (47): `CVE_CARTERA`, `NOMBRE_PPI`, `ID_RAMO`, `DESCRIPCION_RAMO`, `ID_UR`, `DESCRIPCION_UR`, `DESCRIPCION_TIPO_PPI`, `DESCRIPCION_PPI`, `LOCALIZACION`, `ID_ENTIDAD_FEDERATIVA`, `ENTIDAD_FEDERATIVA`, `LATITUD`, `LONGITUD`, `FECHA_INICIO_CAL_FF`, `FECHA_FIN_CAL_FF`, `ANIOS_HE`, `NOMBRE_ADMIN`, `APELLIDO_PATERNO_ADMIN`, `APELLIDO_MATERNO_ADMIN`, `CARGO_ADMIN`, `MAIL_ADMIN`, `MAIL_ALTERNO_ADMIN`, `TELEFONO_ADMIN`, `EXTENSION_ADMIN`, `META_FISICA`, `BENEFICIOS_ESPERADOS`, `ID_PPI`, `PPEF`, `PEF`, `APROBADO`, `MODIFICADO`, `EJERCIDO`, `AVANCE_FISICO`, `MONTO_TOTAL_INVERSION`, `MONTO_OPERACION_MANTENIMIENTO`, `OTROS_COSTOS`, `COSTO_TOTAL_INVERSION`, `ANIO`, `FISCAL`, `PROPIO`, `ESTATAL`, `MUNICIPAL`, `PRIVADA`, `FIDEICOMISO`, `OTROS`, `CICLO`, `ESTATUS_OPERACION`

## intermedia: `opa_2019_anual_intermedia_vivo.csv` (2019 (anual/genérico))

- Fuente: **vivo** -- `https://www.transparenciapresupuestaria.gob.mx/work/models/PTP/DatosAbiertos/OPA/2019/proyectos_opa.csv`
- Formato: csv
- Encoding detectado: utf-8-sig
- Separador: `,` / quotechar: `"`
- Filas: 2745
- Columna de cartera detectada: `CVE_CARTERA`
- PPI únicos: 2743
- Rango `cve_cartera`: '001 02 001 – '1953TVV0001
- Formato consistente (`^\d{10,11}$`): no (0.0% válido)
- Columnas (47): `CVE_CARTERA`, `NOMBRE_PPI`, `ID_RAMO`, `DESCRIPCION_RAMO`, `ID_UR`, `DESCRIPCION_UR`, `DESCRIPCION_TIPO_PPI`, `DESCRIPCION_PPI`, `LOCALIZACION`, `ID_ENTIDAD_FEDERATIVA`, `ENTIDAD_FEDERATIVA`, `LATITUD`, `LONGITUD`, `FECHA_INICIO_CAL_FF`, `FECHA_FIN_CAL_FF`, `ANIOS_HE`, `NOMBRE_ADMIN`, `APELLIDO_PATERNO_ADMIN`, `APELLIDO_MATERNO_ADMIN`, `CARGO_ADMIN`, `MAIL_ADMIN`, `MAIL_ALTERNO_ADMIN`, `TELEFONO_ADMIN`, `EXTENSION_ADMIN`, `META_FISICA`, `BENEFICIOS_ESPERADOS`, `ID_PPI`, `PPEF`, `PEF`, `APROBADO`, `MODIFICADO`, `EJERCIDO`, `AVANCE_FISICO`, `MONTO_TOTAL_INVERSION`, `MONTO_OPERACION_MANTENIMIENTO`, `OTROS_COSTOS`, `COSTO_TOTAL_INVERSION`, `ANIO`, `FISCAL`, `PROPIO`, `ESTATAL`, `MUNICIPAL`, `PRIVADA`, `FIDEICOMISO`, `OTROS`, `CICLO`, `ESTATUS_OPERACION`

## Comparación de columnas entre las 3 muestras

| Columna | antigua | reciente | intermedia |
|---|---|---|---|
| `CVE_PPI` | ✓ | — | — |
| `NOMBRE` | ✓ | — | — |
| `RAMO` | ✓ | — | — |
| `DESC_RAMO` | ✓ | — | — |
| `UNIDAD` | ✓ | — | — |
| `DESC_UNIDAD` | ✓ | — | — |
| `TIPO_PPI` | ✓ | — | — |
| `DESCRIPCION` | ✓ | — | — |
| `LOCALIZACION` | ✓ | ✓ | ✓ |
| `CVE_ENTFED` | ✓ | — | — |
| `ENT_FED` | ✓ | — | — |
| `LATITUD_INICIAL` | ✓ | — | — |
| `LONGITUD_INICIAL` | ✓ | — | — |
| `FECHA_INI_CAL_FISCAL` | ✓ | — | — |
| `FECHA_FIN_CAL_FISCAL` | ✓ | — | — |
| `FECHA_INI_FF` | ✓ | — | — |
| `FECHA_FIN_FF` | ✓ | — | — |
| `ANIOS_HE` | ✓ | ✓ | ✓ |
| `NOMBRE_ADMIN` | ✓ | ✓ | ✓ |
| `AP_MATERNO_ADMIN` | ✓ | — | — |
| `AP_PATERNO_ADMIN` | ✓ | — | — |
| `CARGO_ADMIN` | ✓ | ✓ | ✓ |
| `MAIL_ADMIN` | ✓ | ✓ | ✓ |
| `TELEFONO_ADMIN` | ✓ | ✓ | ✓ |
| `META_FISICA` | ✓ | ✓ | ✓ |
| `META_BENEFICIOS` | ✓ | — | — |
| `ID_PPI` | ✓ | ✓ | ✓ |
| `APROBADO` | ✓ | ✓ | ✓ |
| `MODIFICADO` | ✓ | ✓ | ✓ |
| `EJERCIDO` | ✓ | ✓ | ✓ |
| `AVANCE_FISICO` | ✓ | ✓ | ✓ |
| `GRUPO_FUNCIONAL` | ✓ | — | — |
| `FUNCION` | ✓ | — | — |
| `MONTO_TOTAL_INVERSION` | ✓ | ✓ | ✓ |
| `TOTAL_GASTO_OPERACION_HE` | ✓ | — | — |
| `TOTAL_GASTO_NO_CONSID` | ✓ | — | — |
| `COSTO_TOTAL_PPI` | ✓ | — | — |
| `ANIO` | ✓ | ✓ | ✓ |
| `MONTO_ASIGAUTACT` | ✓ | — | — |
| `RECURSOS_ESTATALES` | ✓ | — | — |
| `RECURSOS_MUNICIPALES` | ✓ | — | — |
| `PRIVADOS` | ✓ | — | — |
| `FIDEICOMISO` | ✓ | ✓ | ✓ |
| `CICLO` | ✓ | ✓ | ✓ |
| `TIPO_PROYECTO` | ✓ | — | — |
| `CVE_CARTERA` | — | ✓ | ✓ |
| `NOMBRE_PPI` | — | ✓ | ✓ |
| `ID_RAMO` | — | ✓ | ✓ |
| `DESCRIPCION_RAMO` | — | ✓ | ✓ |
| `ID_UR` | — | ✓ | ✓ |
| `DESCRIPCION_UR` | — | ✓ | ✓ |
| `DESCRIPCION_TIPO_PPI` | — | ✓ | ✓ |
| `DESCRIPCION_PPI` | — | ✓ | ✓ |
| `ID_ENTIDAD_FEDERATIVA` | — | ✓ | ✓ |
| `ENTIDAD_FEDERATIVA` | — | ✓ | ✓ |
| `LATITUD` | — | ✓ | ✓ |
| `LONGITUD` | — | ✓ | ✓ |
| `FECHA_INICIO_CAL_FF` | — | ✓ | ✓ |
| `FECHA_FIN_CAL_FF` | — | ✓ | ✓ |
| `APELLIDO_PATERNO_ADMIN` | — | ✓ | ✓ |
| `APELLIDO_MATERNO_ADMIN` | — | ✓ | ✓ |
| `MAIL_ALTERNO_ADMIN` | — | ✓ | ✓ |
| `EXTENSION_ADMIN` | — | ✓ | ✓ |
| `BENEFICIOS_ESPERADOS` | — | ✓ | ✓ |
| `PPEF` | — | ✓ | ✓ |
| `PEF` | — | ✓ | ✓ |
| `MONTO_OPERACION_MANTENIMIENTO` | — | ✓ | ✓ |
| `OTROS_COSTOS` | — | ✓ | ✓ |
| `COSTO_TOTAL_INVERSION` | — | ✓ | ✓ |
| `FISCAL` | — | ✓ | ✓ |
| `PROPIO` | — | ✓ | ✓ |
| `ESTATAL` | — | ✓ | ✓ |
| `MUNICIPAL` | — | ✓ | ✓ |
| `PRIVADA` | — | ✓ | ✓ |
| `OTROS` | — | ✓ | ✓ |
| `ESTATUS_OPERACION` | — | ✓ | ✓ |

