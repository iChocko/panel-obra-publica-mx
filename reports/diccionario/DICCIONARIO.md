# Diccionario de datos -- panel OPA (capa Gold)

Generado desde `dbt/models/marts/schema.yml` (fuente única) contra las columnas
reales de `data/gold/panel_opa.duckdb` -- no editar a mano, regenerar con
`opa diccionario`. Montos en pesos corrientes MXN salvo indicación contraria;
avance físico en puntos porcentuales 0-100.

## dim_entidad

Catálogo de entidades federativas. 32 estados del catálogo oficial + 3 códigos especiales de cobertura no-estatal (extranjero / no distribuible / nacional) que aparecen en programas de cobertura nacional -- ver dim_entidad.sql.

| # | Columna | Tipo | Descripción |
|---|---------|------|-------------|
| 1 | `id_entidad_federativa` | INTEGER | Clave INEGI de la entidad (1 = Aguascalientes ... 32 = Ciudad de México) más los códigos especiales de la fuente: 33 = en el extranjero, 34 = no distribuible geográficamente, 35 = cobertura nacional. |
| 2 | `entidad_federativa` | VARCHAR | Nombre de la entidad federativa o descripción del código especial. |
| 3 | `en_catalogo_oficial` | BOOLEAN | true para las 32 entidades del catálogo INEGI/SHCP; false para los 3 códigos especiales que solo existen en los datos del panel. |

## dim_ppi

SCD2 sobre atributos descriptivos del PPI (nombre, ramo, UR, tipo, localización, coordenadas) -- un renglón por periodo de vigencia, no por observación. Los montos viven en fct_ppi_observacion, no aquí.

| # | Columna | Tipo | Descripción |
|---|---------|------|-------------|
| 1 | `cve_cartera` | VARCHAR | Clave de cartera del PPI (ver fct_ppi_observacion.cve_cartera). |
| 2 | `version_ppi` | HUGEINT | Número de versión SCD2 del PPI (1 = primera combinación de atributos observada; sube cada vez que algún atributo descriptivo cambia entre cortes consecutivos). |
| 3 | `vigente_desde_corte` | INTEGER | Primer corte con esta versión de atributos, formato legible año*10+trimestre (ej. 20213 = 2021 T3). Solo para ordenar/mostrar, no para aritmética de brechas. |
| 4 | `vigente_hasta_corte` | INTEGER | Último corte observado con esta versión de atributos (mismo formato). |
| 5 | `snapshot_id_inicio` | VARCHAR | snapshot_id del primer corte de esta versión. FK informal a dim_snapshot. |
| 6 | `snapshot_id_fin` | VARCHAR | snapshot_id del último corte de esta versión. |
| 7 | `nombre_ppi` | VARCHAR | Nombre del PPI vigente en esta versión, textual de la fuente. Los renombramientos entre versiones son reales y frecuentes (ver fct_ppi_delta.bandera_renombramiento). |
| 8 | `id_ramo` | BIGINT | Ramo de esta versión. FK a dim_ramo. |
| 9 | `descripcion_ramo` | VARCHAR | Nombre del ramo tal como lo publicó la fuente en esta versión. |
| 10 | `descripcion_tipo_ppi` | VARCHAR | Tipo de PPI, texto libre de la fuente (mismas 29 variantes y advertencia que en fct_ppi_observacion). |
| 11 | `id_ur` | DOUBLE | Clave de la Unidad Responsable (dependencia/entidad ejecutora) dentro del ramo. Numérica en la fuente moderna; NULL donde el esquema fuente no la publica. |
| 12 | `descripcion_ur` | VARCHAR | Nombre de la Unidad Responsable, textual de la fuente. |
| 13 | `localizacion` | VARCHAR | Descripción textual libre de la ubicación (municipio, localidad, tramo carretero, etc.) tal como la capturó la dependencia -- sin normalizar, calidad heterogénea. |
| 14 | `id_entidad_federativa` | DOUBLE | Entidad federativa de esta versión (clave INEGI o código 33-35). FK a dim_entidad. |
| 15 | `entidad_federativa` | VARCHAR | Nombre de la entidad, textual de la fuente. |
| 16 | `latitud` | DOUBLE | Latitud en grados decimales de esta versión (mismo tratamiento que en fct_ppi_observacion). |
| 17 | `longitud` | DOUBLE | Longitud en grados decimales de esta versión. |
| 18 | `es_version_vigente` | BOOLEAN | true solo para la versión más reciente de cada PPI -- filtro directo para obtener "el estado actual conocido" sin ventana propia. |

## dim_ramo

Catálogo de ramos presupuestarios. 25 del catálogo oficial vigente (catalogos.xlsx) + 11 históricos que aparecen en el panel 2015-2018 pero ya no existen en el catálogo actual -- ver la nota completa en dim_ramo.sql.

| # | Columna | Tipo | Descripción |
|---|---------|------|-------------|
| 1 | `id_ramo` | INTEGER | Clave numérica del ramo presupuestario federal (ej. 9 = Infraestructura, Comunicaciones y Transportes; 12 = Salud). Incluye ramos históricos ya reorganizados (ej. 17 = PGR) y ramos nuevos que la fuente estrena antes de que el catálogo oficial los recoja (ej. 56 = IMSS-BIENESTAR, aparece en 2026 T1). |
| 2 | `descripcion_ramo` | VARCHAR | Nombre del ramo. Para ramos fuera del catálogo vigente, la descripción se tomó textual de la columna DESC_RAMO del propio panel, no se inventó. |
| 3 | `en_catalogo_oficial` | BOOLEAN | true si el ramo está en el catálogo oficial vigente de la SHCP (catalogos.xlsx); false para históricos y códigos que solo existen en los datos. |

## dim_snapshot

Metadatos de cada corte -- año, trimestre, origen, procedencia, conteo de PPI, y si llegó a Silver o quedó excluido (corrupto en la fuente / esquema desconocido).

| # | Columna | Tipo | Descripción |
|---|---------|------|-------------|
| 1 | `snapshot_id` | VARCHAR | Identificador único del corte: "{año}Q{trimestre}_{sha8}" (ej. 2021Q3_ae02c33e) o "{año}_anual_{sha8}" para archivos anuales sin trimestre declarado. El sufijo es el sha256 truncado del archivo fuente -- el mismo contenido produce siempre el mismo id (direccionable por contenido, ver data/manifest.jsonl). |
| 2 | `anio` | INTEGER | Año del corte declarado por la fuente (2015-2026). |
| 3 | `trimestre` | INTEGER | Trimestre del corte (1-4). NULL para snapshots anuales genéricos (proyectos_opa.csv sin trimestre en el nombre) cuyo vintage exacto la fuente no declara -- esos cortes se excluyen de los modelos cronológicos (ver int_snapshot_canonico.sql). |
| 4 | `origen` | VARCHAR | Vía por la que se recuperó el archivo: "vivo" (servidor actual de la SHCP) o "wayback" (captura del Wayback Machine para cortes que ya no existen en vivo). |
| 5 | `fecha_descarga` | DATE | Fecha en que este repo descargó el archivo (no la fecha de publicación original). |
| 6 | `url` | VARCHAR | URL exacta de la que se descargó el archivo fuente (procedencia, citable). |
| 7 | `sha256` | VARCHAR | Hash SHA-256 completo del archivo fuente tal como se descargó (integridad verificable). |
| 8 | `bytes` | BIGINT | Tamaño del archivo fuente en bytes. |
| 9 | `n_observaciones` | BIGINT | Filas del snapshot que pasaron el contrato de Silver. 0 si el snapshot quedó excluido (ver estado). |
| 10 | `n_ppi` | BIGINT | PPI distintos (cve_cartera únicos) en el snapshot normalizado. Menor o igual a n_observaciones porque un PPI puede traer varias sub-filas (ver n_registros_agregados en fct_ppi_observacion). |
| 11 | `estado` | VARCHAR | "normalizado" (llegó a Silver) o "excluido_de_silver" (el manifiesto lo conoce pero no se pudo normalizar -- ej. los 3 archivos de 2024 T1, corruptos en la fuente misma). Los excluidos se listan con conteos en cero para que la exclusión sea visible, no silenciosa. |

## dim_tipo_ppi

Catálogo oficial (catalogos.xlsx) de 11 tipos de programa/proyecto de inversión.

| # | Columna | Tipo | Descripción |
|---|---------|------|-------------|
| 1 | `id_tipo_ppi` | INTEGER | Clave numérica del tipo de PPI en el catálogo oficial de la SHCP. |
| 2 | `descripcion_tipo_ppi` | VARCHAR | Descripción oficial del tipo. OJO: fct_ppi_observacion.descripcion_tipo_ppi trae el texto libre de la fuente (29 variantes), no estas 11 -- no hay un id en los datos crudos que las una limpiamente (ver dim_tipo_ppi.sql). |

## fct_ppi_ciclo_vida

Un renglón por PPI: primer/último corte, sobrecosto %, duración, estatus terminal inferido -- ver la limitación metodológica declarada en el modelo (sección 2.2 de la arquitectura: "salida_no_explicada" puede ser un hueco de cobertura nuestro, no una salida real del universo de reporte).

| # | Columna | Tipo | Descripción |
|---|---------|------|-------------|
| 1 | `cve_cartera` | VARCHAR | Clave de cartera del PPI (ver fct_ppi_observacion.cve_cartera). Única aquí -- un renglón por PPI. |
| 2 | `nombre_ppi` | VARCHAR | Nombre del PPI en su PRIMERA observación (los renombramientos posteriores no lo actualizan aquí). |
| 3 | `primer_corte` | INTEGER | Primer corte en que se observó el PPI, formato año*10+trimestre. |
| 4 | `ultimo_corte` | INTEGER | Último corte en que se observó el PPI, mismo formato. |
| 5 | `trimestres_entre_primera_y_ultima_observacion` | INTEGER | Trimestres calendario entre la primera y la última observación (índice lineal). 0 = observado en un solo corte. |
| 6 | `snapshot_id_inicio` | VARCHAR | snapshot_id de la primera observación. |
| 7 | `snapshot_id_fin` | VARCHAR | snapshot_id de la última observación. |
| 8 | `n_observaciones` | BIGINT | Cortes canónicos en que se observó el PPI. Puede ser menor que la brecha de trimestres + 1 si el PPI cayó en huecos del panel. |
| 9 | `n_anios_observado` | BIGINT | Años calendario distintos con al menos una observación del PPI. |
| 10 | `alguna_observacion_con_cobertura_parcial` | BOOLEAN | true si al menos una observación proviene de un corte de cobertura parcial (2020 T1/T2) -- tratar sus fechas extremas y conteos con cautela. |
| 11 | `monto_inicial` | DOUBLE | Presupuesto modificado en la primera observación, pesos corrientes MXN. |
| 12 | `monto_final` | DOUBLE | Presupuesto modificado en la última observación, pesos corrientes MXN. |
| 13 | `sobrecosto_pct` | DOUBLE | (monto_final - monto_inicial) / monto_inicial * 100. NULL si monto_inicial <= 0. OJO doble: son pesos NOMINALES (parte del "sobrecosto" de proyectos largos es inflación) y compara modificado del ciclo, no monto total del proyecto -- interpretarlo como señal de arrastre, no como sobrecosto contable auditado. |
| 14 | `duracion_planeada_anios` | DOUBLE | Años de horizonte de ejecución declarados por la fuente en la primera observación (columna fuente ANIOS_HE). NULL donde el esquema fuente no la publica. |
| 15 | `duracion_observada_anios` | DOUBLE | trimestres_entre_primera_y_ultima_observacion / 4 -- años entre la primera y la última vez que ESTE PANEL vio el PPI, no la duración real de la obra (censura por los bordes y huecos del panel). |
| 16 | `avance_fisico_final` | DOUBLE | Avance físico en la última observación, puntos porcentuales 0-100. |
| 17 | `estatus_operacion_final` | VARCHAR | Estatus de operación en la última observación. |
| 18 | `estatus_terminal_inferido` | VARCHAR | Regla declarada de la arquitectura sección 2.2: "terminado_probable" (avance final >= 95), "vigente_ultimo_corte_disponible" (su última observación ES el último corte del panel -- no ha terminado de observarse), o "salida_no_explicada" (desapareció antes del final del panel sin avance >= 95: puede ser salida real O un hueco de cobertura nuestro -- indistinguibles con los datos abiertos disponibles). |

## fct_ppi_delta

Cambio contra el corte canónico inmediato anterior del mismo PPI. brecha_trimestres distingue un delta de un trimestre limpio de uno que cruza un hueco de cobertura real.

| # | Columna | Tipo | Descripción |
|---|---------|------|-------------|
| 1 | `cve_cartera` | VARCHAR | Clave de cartera del PPI (ver fct_ppi_observacion.cve_cartera). |
| 2 | `snapshot_id` | VARCHAR | Corte "actual" del delta. FK a dim_snapshot. |
| 3 | `snapshot_id_anterior` | VARCHAR | Corte anterior REALMENTE OBSERVADO de este PPI -- no necesariamente el trimestre calendario previo (el panel tiene huecos; ver brecha_trimestres). |
| 4 | `anio` | INTEGER | Año del corte actual. |
| 5 | `trimestre` | INTEGER | Trimestre del corte actual (1-4). |
| 6 | `orden_corte` | INTEGER | Corte actual en formato legible año*10+trimestre (solo ordenar/mostrar). |
| 7 | `brecha_trimestres` | INTEGER | Trimestres calendario entre la observación anterior y esta (índice lineal año*4+trimestre, cruza años sin romperse). 1 = delta trimestral limpio; >1 = el delta cruza un hueco de cobertura -- no interpretarlo igual (un salto de monto en brecha 3 no es un cambio trimestral). |
| 8 | `cobertura_parcial_del_universo` | BOOLEAN | true si el corte actual proviene de un producto que NO es el universo completo (ej. 2020 T1/T2 solo tienen "Concluido") -- los deltas contra/desde esos cortes comparan universos distintos por diseño de la fuente. |
| 9 | `modificado_anterior` | DOUBLE | Presupuesto modificado en el corte anterior, pesos corrientes MXN. |
| 10 | `modificado` | DOUBLE | Presupuesto modificado en el corte actual, pesos corrientes MXN. |
| 11 | `delta_modificado` | DOUBLE | modificado - modificado_anterior, pesos corrientes MXN (nominal: parte del cambio entre años es inflación, no decisión presupuestaria). |
| 12 | `ejercido_anterior` | DOUBLE | Monto ejercido en el corte anterior, pesos corrientes MXN. |
| 13 | `ejercido` | DOUBLE | Monto ejercido en el corte actual, pesos corrientes MXN. |
| 14 | `delta_ejercido` | DOUBLE | ejercido - ejercido_anterior, pesos corrientes MXN. Negativo entre ciclos fiscales es normal (el ejercido del año nuevo arranca en cero), no un reintegro. |
| 15 | `monto_total_inversion_anterior` | DOUBLE | Monto total de inversión en el corte anterior, pesos corrientes MXN. |
| 16 | `monto_total_inversion` | DOUBLE | Monto total de inversión en el corte actual, pesos corrientes MXN. |
| 17 | `delta_monto_total_inversion` | DOUBLE | Cambio del monto total de inversión, pesos corrientes MXN -- la señal cruda de re-dimensionamiento/sobrecosto entre cortes. |
| 18 | `avance_fisico_anterior` | DOUBLE | Avance físico en el corte anterior, puntos porcentuales 0-100. |
| 19 | `avance_fisico` | DOUBLE | Avance físico en el corte actual, puntos porcentuales 0-100. |
| 20 | `delta_avance_fisico` | DOUBLE | Cambio de avance físico en puntos porcentuales. |
| 21 | `avance_fisico_decrecio` | BOOLEAN | true si el avance físico BAJÓ entre cortes -- físicamente anómalo (una obra no se des-construye) pero real en la fuente: re-baselineos y correcciones de captura. Es la bandera que exige la arquitectura sección 6.2. |
| 22 | `estatus_operacion_anterior` | VARCHAR | Estatus de operación en el corte anterior (mismas variantes sin normalizar). |
| 23 | `estatus_operacion` | VARCHAR | Estatus de operación en el corte actual. |
| 24 | `cambio_estatus` | BOOLEAN | true si el estatus cambió entre cortes (NULL-seguro, is distinct from). |
| 25 | `bandera_renombramiento` | BOOLEAN | true si el nombre del PPI cambió entre cortes manteniendo la misma cve_cartera -- señal para no tratar el nombre como identificador y para auditar continuidad. |

## fct_ppi_observacion

Tabla central del panel (arquitectura sección 4.3). Un renglón por PPI observado en un corte. Ver la nota en el modelo sobre por qué la fuente NO es directamente stg_opa_snapshot -- (cve_cartera, snapshot_id) no es único en los datos crudos.

| # | Columna | Tipo | Descripción |
|---|---------|------|-------------|
| 1 | `cve_cartera` | VARCHAR | Clave de cartera del PPI asignada por la Unidad de Inversiones de la SHCP. Alfanumérica de 10-11 caracteres (ej. 2151GYN0003) tras limpiar la comilla inicial de Excel -- NO es numérica, 99.2% de cumplimiento medido sobre 32,186 valores reales. Es el identificador que permite seguir un PPI a través de cortes. |
| 2 | `snapshot_id` | VARCHAR | Corte en que se observó este renglón. FK a dim_snapshot. |
| 3 | `anio_corte` | DOUBLE | Año del corte (copiado de dim_snapshot para consulta directa). NULL en observaciones de snapshots anuales genéricos y en ~20% de filas del propio esquema fuente moderno (medido, no supuesto). |
| 4 | `trimestre_corte` | INTEGER | Trimestre del corte (1-4); NULL en snapshots anuales genéricos. |
| 5 | `n_registros_agregados` | BIGINT | Cuántas sub-filas del archivo fuente se colapsaron en esta observación. 1 = renglón directo; >1 = programa multi-entidad publicado como una fila por sub-asignación (hasta 33), cuyos montos aquí están SUMADOS y cuyos atributos descriptivos vienen de la sub-fila de mayor monto -- la pérdida de precisión geográfica queda declarada en esta columna, no escondida (ver int_ppi_observaciones_dedup.sql). |
| 6 | `aprobado` | DOUBLE | Presupuesto aprobado del ciclo fiscal del corte, pesos corrientes MXN (columna fuente APROBADO/MONTO_APROBADO según el año del esquema). |
| 7 | `modificado` | DOUBLE | Presupuesto modificado del ciclo fiscal del corte, pesos corrientes MXN. Es el monto contra el que la fuente reporta el ejercicio del año en curso. |
| 8 | `ejercido` | DOUBLE | Monto ejercido, pesos corrientes MXN. OJO (hallazgo real, Fase 2): en 18.5% de filas ejercido > modificado por márgenes de cientos de veces -- consistente con un EJERCIDO acumulado del proyecto contra un MODIFICADO del ciclo vigente. No asumir que son comparables directamente; pregunta abierta documentada. |
| 9 | `monto_total_inversion` | DOUBLE | Monto total de inversión del PPI completo (todos los años), pesos corrientes MXN. Verificado en magnitud contra megaproyectos conocidos (Tren Maya ~1.67e11). |
| 10 | `monto_operacion_mantenimiento` | DOUBLE | Monto de operación y mantenimiento asociado al PPI, pesos corrientes MXN. Solo existe en algunos esquemas fuente; NULL donde la fuente no lo publica. |
| 11 | `costo_total_inversion` | DOUBLE | Costo total (inversión + operación y mantenimiento) declarado por la fuente, pesos corrientes MXN. Solo en esquemas que lo publican; no se calcula aquí. |
| 12 | `ppef` | DOUBLE | Monto en el Proyecto de Presupuesto de Egresos de la Federación del ciclo, pesos corrientes MXN (columna fuente MONTO_PPEF, esquemas 2017-2018). |
| 13 | `pef` | DOUBLE | Monto en el Presupuesto de Egresos de la Federación aprobado del ciclo, pesos corrientes MXN. Solo en esquemas que lo publican. |
| 14 | `avance_fisico` | DOUBLE | Avance físico reportado, puntos porcentuales 0-100 (verificado: promedio 43.5, rango completo). En observaciones agregadas (n_registros_agregados > 1) es el máximo de las sub-filas, nunca su suma. |
| 15 | `estatus_operacion` | VARCHAR | Estatus del PPI en el sistema de la Unidad de Inversiones (esquema moderno, 2018+; NULL antes -- ver fase). OJO (hallazgo real, 2026-08-08): incluye variantes de texto de la misma fuente que no se normalizaron en Silver (ej. "Calendario Fiscal Concluido / Operación" con espacios vs. sin espacios; "En Proceso de Cancelación" vs. minúscula) -- pendiente de unificar en una futura pasada de Silver. El test aquí fija el conjunto conocido HOY para detectar valores genuinamente nuevos, no para validar que estén limpios. |
| 16 | `fase` | VARCHAR | Fase del PPI en el esquema viejo/transicional de la fuente (columna FASE, solo 2017-2018 -- verificado: 0 valores fuera de esos cortes). Cumple el rol que estatus_operacion tiene en el esquema moderno pero con vocabulario propio; se conserva como columna aparte a propósito, sin mapearla (ver conf/schema_map.yml). |
| 17 | `id_ramo` | BIGINT | Ramo presupuestario del PPI en este corte. FK a dim_ramo. |
| 18 | `descripcion_ramo` | VARCHAR | Nombre del ramo tal como lo publicó la fuente en este corte. |
| 19 | `descripcion_tipo_ppi` | VARCHAR | OJO: texto libre de 11 años de fuente, no el catálogo oficial de 11 valores de dim_tipo_ppi -- no hay un id_tipo_ppi numérico en los datos crudos que los una limpiamente (ver dim_tipo_ppi.sql). 29 valores distintos observados, con duplicados de forma (mayúscula/minúscula, singular/plural) sin normalizar. |
| 20 | `id_entidad_federativa` | DOUBLE | Entidad federativa del PPI en este corte (clave INEGI o código especial 33-35). FK a dim_entidad. En agregados multi-entidad es la de la sub-fila de mayor monto. |
| 21 | `entidad_federativa` | VARCHAR | Nombre de la entidad tal como lo publicó la fuente en este corte. |
| 22 | `latitud` | DOUBLE | Latitud del PPI en grados decimales (WGS84 implícito en la fuente). El centinela 0 del esquema viejo ya se trató como NULL en Silver -- (0,0) es imposible en México y era el 48.6% de 2015 (hallazgo real de Fase 2). Puede quedar algún punto fuera del territorio: la fuente publica errores de captura reales. |
| 23 | `longitud` | DOUBLE | Longitud del PPI en grados decimales (negativa en México). Mismo tratamiento de centinelas que latitud. |
| 24 | `modificado_real` | DOUBLE | modificado deflactado a pesos constantes del año base (ver anio_base_deflactor). NULL hasta que conf/deflactor_inpc.csv se llene con la serie oficial de Banxico SIE -- se prefirió NULL explícito a aproximar con inflación genérica. |
| 25 | `ejercido_real` | DOUBLE | ejercido deflactado a pesos constantes. NULL por la misma razón que modificado_real. |
| 26 | `monto_total_inversion_real` | DOUBLE | monto_total_inversion deflactado a pesos constantes. NULL por la misma razón. |
| 27 | `anio_base_deflactor` | INTEGER | Año base de la serie INPC usada para deflactar (columna anio_base de conf/deflactor_inpc.csv). NULL mientras el CSV siga vacío. |
