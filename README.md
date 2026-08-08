# Panel Histórico de Obra Pública Federal (México)

## Tesis

La SHCP publica cada trimestre una fotografía del universo de proyectos de inversión federal
(PPI) en su sección de **Obra Pública Abierta (OPA)**. Cada fotografía nueva sobreescribe a la
anterior: el visor y los archivos de nombre genérico solo muestran el corte más reciente. **La
fuente destruye su propia historia.** Este repositorio la reconstruye a partir de tres capas —
archivos vivos con nombre de trimestre, espejos en portales de datos abiertos, y capturas del
Internet Archive (Wayback Machine) — para publicar un panel longitudinal por clave de cartera
que hoy no existe públicamente en ningún otro lugar.

Ver [`viabilidad_tecnica`](viabilidad_tecnica) (dictamen de viabilidad) y
[`ARQUITECTURA-panel-obra-publica-mx.md`](ARQUITECTURA-panel-obra-publica-mx.md) (arquitectura
completa del proyecto) para el detalle.

## Estado: Fase 0 + Fase 1 — Reconocimiento y resolución de huecos (2026-08-08)

**Recuperabilidad trimestral 2016–2024: 29 / 36 (80.6%) → por encima del 70%.**

**Recomendación: panel trimestral completo, alcance original** -- no el pivote a panel anual que
había recomendado la primera corrida, ni siquiera el panel parcial de la segunda. Detalle completo
en [`reports/cobertura.md`](reports/cobertura.md).

> **Nota de transparencia metodológica:** la corrida original de Fase 0 (2026-08-05) midió 4/36
> (11.1%) y recomendó pivotar a panel anual. Fase 1 (2026-08-08) resolvió por qué 2022-2026 no
> respondía (cambio de nombre de archivo, no descontinuación) y subió la cifra a 22/36 (61.1%,
> panel parcial). Una segunda ronda de Fase 1 el mismo día resolvió además 2019 completo y 2020
> T3/T4, subiendo a 28/36 (77.8%). Al preparar Bronze se encontró que 76 capturas de Wayback ya
> recolectadas desde Fase 0 nunca se habían clasificado (su nombre de archivo no coincidía con
> ningún patrón conocido) -- una de ellas resultó ser 2016 T3 real (esquema viejo, `ANIO=2016`
> confirmado en el 99% de sus filas), subiendo a **29/36 (80.6%)**. Es decir: la declaración de
> "4 vías agotadas, huecos confirmados" de la ronda anterior no era del todo cierta -- ya
> teníamos evidencia sin cruzar en nuestros propios datos. El número y la recomendación
> **vigentes son los de arriba**; se documentan los intermedios por trazabilidad, no como estado
> actual.

Hallazgos clave:

- **El patrón de nombre de archivo cambió en 2022, no la disponibilidad de los datos.** El portal
  migró a una aplicación Next.js y renombró los trimestrales dentro de la MISMA carpeta que Fase 0
  ya recorría (`/work/models/PTP/DatosAbiertos/OPA/{año}/`): de
  `reporteOPA{trimestre}Trimestre.xlsx` a una familia nueva --
  `ConsolidadoOPA{trimestre}Trimestre{año}.csv` (maestro),
  `SeguimientoOPA{trimestre}Trimestre{año}.csv` (seguimiento trimestral) y
  `Concluido(s)OPA{trimestre}Trimestre{año}.csv` (concluidos ese trimestre -- la pluralización
  alterna sin regla clara por año, hay que probar ambas formas). Confirmado con GET real (no solo
  status HTTP) para los 17 trimestres 2022-2026T1, mismo esquema de columnas ya documentado en
  `reports/esquemas.md`. El portal expone también un manifiesto JSON propio
  (`/work/models/PTP/NPTP/api/page-config/opa/row-down-opa.json`, archivado en
  `data/auxiliares/`) con sus enlaces vigentes -- útil como referencia cruzada, aunque solo cubre
  el trimestre más reciente de cada archivo, no el histórico completo.
- **2019 completo y 2020 T3/T4 también se resolvieron, vía el mismo manifiesto oficial**, que
  etiqueta cada URL con su trimestre en texto plano (no solo por nombre de archivo) -- pero **esa
  etiqueta resultó no ser confiable sin verificar el contenido**: `opa_trimestral.csv` venía
  etiquetado "Primer trimestre 2019" y vive en la carpeta `/2019/`, pero al inspeccionarlo tiene
  `CICLO=2018` en el 100% de sus filas -- no es T1 2019, es un archivo de otro ciclo fiscal mal
  ubicado (o mal etiquetado) por el propio portal. El T1 2019 real es `OPAPrimerTrimestre2019.csv`
  (`CICLO=2019` confirmado en sus 1,513 filas), encontrado por analogía de patrón, no por el
  manifiesto. `opa_trimestral.csv` se conserva como auxiliar archivable (dato real, solo que de
  2018) en vez de usarse para llenar la celda de T1 2019. El resto son 5 URLs exactas con la misma
  nomenclatura irregular (`OPASegundoTrimestre2019.csv`, `OPATercerTrimestre2019.csv` -- el
  manifiesto trae un typo, `OPATerceTrimestre2019.csv`, que da 404 --, `OPA4toTrimestre2019.csv`, y
  `OPA3er4toTrimestre2020.csv`). Este último cubre T3 y T4 de 2020 en un solo archivo -- se
  verificó que **no trae ninguna columna que distinga fila por trimestre** (`CICLO` es un único
  valor, `2020`, en las 1,549 filas), así que se cuenta como el corte combinado oficial de ese
  periodo tal como lo publicó la SHCP, no como dos trimestres verificables por separado a nivel de
  fila. Todas documentadas como `casos_especiales` en `conf/sources.yml` en vez de forzarlas al
  mecanismo de patrones parametrizados.
- **La hipótesis de que OPA se fusionó con el Tomo VIII del PEF es falsa.** Tomo VIII sí tiene un
  CSV real y vivo 2022-2025 (`REPORTE_TOMO_VIII.csv`), pero es presupuesto ex-ante -- sin avance
  físico, monto ejercido ni geolocalización -- nunca pudo sustituir a OPA en granularidad. Son
  complementarios, no sucesores.
- **2016 T3 se resolvió aparte, al preparar Bronze** -- no por una nueva búsqueda, sino por
  reclasificar en frío 76 capturas de Wayback que Fase 0 ya tenía recolectadas pero nunca
  clasificó (nombre de archivo sin patrón reconocido: `Proyectos_OPA_3t.csv`, esquema viejo
  `CVE_PPI`). Sigue viva hoy en el servidor. Se probó la misma convención (`Proyectos_OPA_{n}t.csv`)
  para 1t/2t/4t de 2016 y las 4 combinaciones de 2017-2018 -- todas 404, no es un patrón amplio,
  es un archivo suelto. `clasificar_captura()` se actualizó para que una futura corrida de
  Wayback lo reconozca automáticamente.
- **Los 7 trimestres que siguen como hueco son reales**, agotados por 4 vías independientes
  (manifiesto oficial, Wayback CDX dirigido por año, Common Crawl, variaciones de nomenclatura
  probadas en vivo) más la reclasificación en frío de arriba: 2016 T1/T2/T4, 2017 T4, y 2018
  T1/T2/T4. El siguiente paso realista es una solicitud de acceso a la información (PNT/INAI) a
  la SHCP, no más descubrimiento automatizado. Quedan documentados como huecos en
  `reports/cobertura.md`.
- **El esquema cambia de forma importante entre 2015 y 2019/2021** (45 vs. 47 columnas, `CVE_PPI`
  vs. `CVE_CARTERA`, nombres de columna casi todos distintos). 2019 y 2021 comparten esquema.
- **`cve_cartera` no es el código numérico de 10-11 dígitos que asumía la arquitectura**: en 2019 y
  2021 aparecen valores como `'2151GYN0003` (0% cumple `^\d{10,11}$`). El contrato Pandera de la
  arquitectura (sección 6.1) necesita revisarse en Fase 2 con datos reales, no con la forma
  esperada.
- **El mirror de datos.gob.mx (CKAN, id `56b98e14-...`) ya no existe** en el catálogo actual --
  reconfirmado en Fase 1: 0 de 54 datasets de la organización `secretaria_hacienda` corresponden a
  OPA/obra pública/inversión. `datamx.io` tampoco tiene referencia. Wayback y el servidor vivo
  siguen siendo las únicas fuentes reales.
- **Wayback Machine sí archivó archivos de datos, no solo HTML**: 90 capturas con mimetype real
  (`text/csv`, `.xlsx`) entre 2016 y 2024, sin bloqueo ni rate-limit de la CDX API.

Ver [`reports/esquemas.md`](reports/esquemas.md) para el detalle columna por columna de las 3
muestras (2015, 2019, 2021), y [`reports/cobertura.md`](reports/cobertura.md) para la matriz
completa año × trimestre.

## Bronze — snapshots archivados (2026-08-08)

**128 archivos únicos (215 MB), byte por byte tal como los sirvió la fuente**, hasheados y con
procedencia completa en [`data/manifest.jsonl`](data/manifest.jsonl) -- 89 desde el servidor vivo
de la SHCP, 53 solo recuperables vía Wayback Machine. Cubre 2015-2026 completo salvo los 7
trimestres documentados como hueco real (2016 T1/T2/T4, 2017 T4, 2018 T1/T2/T4) -- **no
inventados, no interpolados, simplemente no existen bajo ninguna fuente conocida** (ver la nota
de transparencia metodológica arriba).

**Regla dura del proyecto (ver `ARQUITECTURA-panel-obra-publica-mx.md` sección 4.1): bronze nunca
se reescribe.** El nombre de cada archivo incluye los primeros 8 caracteres de su sha256
(`opa_{año}_{trimestre}_{sha8}.{ext}`), así que es direccionable por contenido -- volver a correr
la ingesta es idempotente por diseño, no por una bandera de "--skip-existentes".

`data/bronze/` **no está en git** (demasiado pesado para el repo -- ver la sección "Almacenamiento
de datos pesados" de la arquitectura, pendiente de subir a un bucket). `data/manifest.jsonl` **sí
está versionado**: es pequeño, es la prueba de procedencia, y satisface el requisito de cita de
los Términos de Libre Uso MX (liga + fecha de descarga). Cualquiera puede reproducir bronze
completo corriendo `uv run opa bronze` -- vuelve a descargar los mismos bytes (mismo hash) de las
mismas URLs que ya están documentadas en `reports/discovery.jsonl`.

**Un hallazgo de calidad de datos real, encontrado al inspeccionar los archivos ya archivados:**
los 3 productos de **2024 T1** (`ConsolidadoOPA1erTrimestre2024.csv`,
`SeguimientoOPA1erTrimestre2024.csv`, `ConcluidosOPA1erTrimestre2024.csv`) están **corruptos en
la fuente misma** -- el servidor sirve un binario OLE2 (firma de Excel `.xls` antiguo) con
extensión `.csv` y `Content-Type: text/csv`, truncado (`xlrd` confirma que el stream interno
declara más bytes de los que el archivo realmente tiene). El `Content-Length` del servidor
coincide exactamente con lo descargado -- no es un problema de nuestra descarga -- y no hay
captura alterna en Wayback. Discovery (Fase 0/1) no lo detecta porque solo valida status HTTP y
Content-Type, no contenido; por eso 2024 T1 sigue contando como "vivo" en `reports/cobertura.md`.
Bronze lo preservó tal cual (es evidencia, no se borra) y `conf/schema_map.yml` lo marca
explícitamente en `snapshots_conocidos_corruptos` para que Silver lo rechace ruidosamente en vez
de intentar normalizarlo.

## Silver — schema_map.yml y el contrato Pandera de cve_cartera (2026-08-08)

**El desorden histórico que la arquitectura anticipaba (sección 4.2: "aquí es donde vive el
trabajo real y donde aparecerán las sorpresas") resultó ser más desordenado de lo que la muestra
de 3 archivos de Fase 0 alcanzaba a mostrar.** Inspeccionando columna por columna los 128
archivos bronze reales (no una muestra), aparecieron **11 esquemas distintos**, no 2:

- **2019-2026 es un esquema único y estable** (79 de 128 archivos, sin cambios en 7 años) --
  buena noticia, es lo que van a seguir usando todos los cortes futuros.
- **2015-2018 tiene 9 variantes reales**, no una sola "forma vieja": la nomenclatura de columnas
  cambia varias veces dentro del mismo año (`RAMO` vs `ID_RAMO`, con y sin `CICLO`), hay columnas
  que aparecen y desaparecen según el corte (`MODIFICADO`/`EJERCIDO`/`AVANCE_FISICO` faltan por
  completo en un snapshot de 2016 -- no es un null, la columna no existía todavía), y **dos bugs
  reales de la fuente**: el anual de 2018 tiene una columna llamada `CVE_PPI` dos veces (donde la
  segunda debería decir `NOMBRE`), y uno de los snapshots de 2016 repite `RAMO` donde debería
  decir `DESC_RAMO`. `conf/schema_map.yml` documenta cada variante con su `header_hash`, el
  mapeo columna por columna a nombres canónicos, y marca con `[inferido]` los mapeos que son
  un juicio semántico razonado, no una confirmación oficial de la SHCP.

**El contrato Pandera original del dictamen de viabilidad tenía tres supuestos que no
sobrevivieron el contacto con datos reales** (`src/opa/contracts.py`, `OPASnapshot`):

- `cve_cartera` **no es un numérico de 10-11 dígitos** (dictamen original: `^\d{10,11}$`, 0% de
  cumplimiento ya confirmado desde Fase 0). Es **alfanumérico de 10-11 caracteres** una vez que
  se quita una comilla inicial que trae el propio archivo (artefacto de Excel "forzar texto",
  presente 2016-2026 pero no en 2015) -- confirmado sobre 32,186 valores reales, ~99.2% de
  cumplimiento con `^[0-9A-Z]{10,11}$`. El ~0.8% restante es basura real de la fuente que el
  contrato rechaza a propósito: valores centinela tipo `'020 96 020'` (se repiten idénticos entre
  años, no son proyectos reales) y notación científica corrupta tipo `'8.36E+21'` (autocast de
  Excel, dato irrecuperable).
- `anio` **no siempre está presente incluso en el esquema moderno** -- ~20% de las filas lo traen
  vacío (368/1786 verificado sobre un snapshot real de 2021), contra el supuesto original de que
  siempre está poblado. `ciclo` suele tener valor cuando `anio` no lo tiene, pero no son
  intercambiables sin más.
- El *check* de coherencia `ejercido <= modificado * 1.05` del dictamen original **falla en 18.5%
  de las filas reales** (278/1499 en un snapshot de 2021), varias por márgenes de cientos de veces,
  no de redondeo -- probable mezcla de un campo acumulado desde el inicio del proyecto
  (`EJERCIDO`) contra uno del ciclo vigente (`MODIFICADO`). **No se incluyó ese check en el
  contrato**: comparar directo puede no tener sentido semántico, y forzar la tolerancia solo para
  que pase ocultaría el problema real en vez de resolverlo. Queda documentado como pregunta
  abierta para Fase 3, no adivinado.

`latitud`/`longitud` sí necesitaban el bbox de México del dictamen original (confirmado: hay
valores basura reales, latitud hasta 436117.0) y `monto_total_inversion >= 0` se mantiene sin
cambios (el máximo real, ~1.7 billones de pesos, es consistente con un megaproyecto agregado, no
un error de unidades).

Probado de punta a punta contra un archivo bronze real completo (2021, 1786 filas): el contrato
detecta correctamente los 13 valores `cve_cartera` centinela y 11 puntos fuera del bbox, sin
falsos positivos en el resto.

### `normalize.py` -- bronze → parquet canónico

`uv run opa normalize` corrió sobre los 91 snapshots únicos con corte declarado (128 archivos
menos duplicados de contenido y los 3 corruptos de 2024 T1): **88 normalizados, 0 con esquema
desconocido, 0 con error de lectura.** De 179,179 filas procesadas, **98.9% pasaron el contrato
(177,245)** -- el resto quedó en cuarentena (excluido del parquet, no descartado en silencio: el
motivo exacto por archivo está en `reports/calidad_silver.md`).

**El primer intento dio 78.0% de filas válidas, no 98.9% -- la diferencia fue un hallazgo real,
no un ajuste cosmético del contrato.** Casi todo el rechazo inicial (43,341 de 196,910 filas) caía
en `latitud`/`longitud` fuera del bbox de México, concentrado casi por completo en los esquemas
de 2015-2018. La causa: **`'0'` es un centinela real de "sin coordenadas" en el esquema viejo**
-- 48.6% de `LATITUD_INICIAL` en 2015 es literalmente `0` (verificado), y (0°N, 0°E) es
geográficamente imposible en México de cualquier forma. El esquema moderno no usa esa convención
(0 apariciones en 2021). `normalize.py` ahora trata `0` como nulo en `latitud`/`longitud` antes de
validar -- documentado en `conf/schema_map.yml`. También se encontraron **4 formatos de fecha
distintos** en el corpus (`2003-01-01 00:00:00`, `01/12/2002`, `mar-06`, `Enero/2001`), todos de
precisión de mes -- ni el formato moderno `DD/MM/YYYY` tiene día real, siempre trae `01`
(verificado sobre 2021 completo). `parsear_fecha_mes()` reconoce las 4; un quinto formato no
reconocido se cuenta y reporta, no se adivina.

Parquet, un archivo por snapshot, en `data/silver/` (78 MB, fuera de git igual que `data/bronze/`).
Nombre de archivo = `snapshot_id` (ej. `2021Q3_ae02c33e.parquet`).

## Gold — el panel (`dbt/`, DuckDB, 2026-08-08)

`dbt build` transforma los 88 parquet de Silver en el modelo dimensional completo que describe
la arquitectura (sección 4.3): `fct_ppi_observacion` (tabla central, grano
`(cve_cartera, snapshot_id)`), `dim_ppi` (SCD2 sobre nombre/ramo/UR/tipo/localización/coordenadas),
`fct_ppi_delta` (cambio contra el corte anterior), `fct_ppi_ciclo_vida` (un renglón por PPI:
sobrecosto %, duración, estatus terminal inferido), `dim_snapshot`, y 3 catálogos congelados
(`dim_ramo`, `dim_entidad`, `dim_tipo_ppi`). Vive en `data/gold/panel_opa.duckdb` (36 MB, fuera de
git -- ver "Almacenamiento de datos pesados" en la arquitectura: Gold se empaqueta y publica
aparte, no directo en el repo). **40 de 40 tests pasan.**

**El hallazgo más importante de esta fase: `(cve_cartera, snapshot_id)` -- el grano que la
arquitectura asume como llave de la observación (sección 2.1) -- no es único en los datos crudos.**
99.35% de los pares sí tienen una sola fila, pero ~1,124 pares tienen entre 2 y 33 filas para el
mismo PPI en el mismo corte. Se investigaron dos casos reales: los montos (`MODIFICADO`,
`EJERCIDO`) son valores genuinamente distintos entre filas del mismo grupo que suman a un total
coherente, mientras que `avance_fisico` se repite igual en todas -- consistente con un "Programa"
de cobertura multi-entidad exportado como una fila por sub-asignación, con un solo `cve_cartera`
padre, no con filas repetidas por error. `int_ppi_observaciones_dedup.sql` sí resuelve esto:
monetarios se **suman** (recupera el total real), `avance_fisico` se toma como **máximo** (es un
porcentaje, sumarlo estaría mal), y los atributos descriptivos vienen de la sub-fila con el monto
más grande -- lo cual pierde precisión geográfica real para un programa nacional, declarado vía
`n_registros_agregados > 1` en vez de escondido.

Otros hallazgos reales de esta fase:

- **Un mismo trimestre puede tener 3 archivos complementarios, no duplicados** (Consolidado =
  universo completo, Seguimiento = solo vigentes, Concluido = solo lo que terminó ese trimestre --
  ver Fase 1). `int_snapshot_canonico.sql` elige uno por trimestre para los modelos que necesitan
  orden cronológico, prefiriendo Consolidado. **2020 T1 y T2 solo tienen "Concluido" disponible**
  -- su universo de PPI no es comparable al resto y queda marcado
  (`cobertura_parcial_del_universo`) para no confundir un hueco de cobertura con un hallazgo real.
- **`id_ramo` e `id_entidad_federativa` traían 11 y 3 códigos que no están en el catálogo oficial
  vigente** (`catalogos.xlsx`) -- ramos de gobiernos anteriores ya reorganizados (ej. `13` =
  Marina, `17` = Procuraduría General de la República) y códigos especiales de cobertura no
  estatal (`33` = en el extranjero, `34` = no distribuible geográficamente, `35` = nacional). Las
  descripciones se tomaron directo de la columna correspondiente del propio panel, no se
  inventaron -- `dim_ramo`/`dim_entidad` quedaron ampliados con `en_catalogo_oficial` para
  distinguir cuáles vienen del catálogo SHCP vigente.
- **`estatus_operacion` y `descripcion_tipo_ppi` traen variantes de texto sin normalizar** de 11
  años de fuente (`"Calendario Fiscal Concluido / Operación"` vs. `"...Concluido/Operación"` sin
  espacios; `"En Proceso de Cancelación"` vs. `"En proceso de cancelación"`) -- 11 y 29 valores
  distintos respectivamente. No hay un `id_tipo_ppi` numérico en los datos crudos que una
  limpiamente contra el catálogo oficial de 11 valores. Los tests `accepted_values` fijan el
  conjunto conocido hoy (para detectar valores *nuevos*, no para certificar que estén limpios) --
  normalizar esto es trabajo pendiente, declarado, no una limpieza de Silver que ya se hizo.
- **El test de "coherencia de montos" del dictamen original (`ejercido <= modificado * 1.05`)
  tampoco se pudo usar aquí** para el singular de "estabilidad por ramo y corte" que pide la
  arquitectura (sección 6.2) -- se probó contra datos reales y la suma de montos por ramo tiene
  demasiado ruido legítimo (medianas de 0% pero swings normales de cientos de %) para detectar
  cargas truncadas de forma confiable. Se implementó sobre **conteo de PPI por ramo** en su lugar
  (más estable en condiciones normales), con `severity: warn`.
- **Hallazgo real sobre el conteo de PPI por ramo (2026-08-08): la transición Q4→Q1 de cada año
  es un patrón estacional estructural de la fuente SHCP, no una carga truncada.** El test de
  estabilidad por ramo marcó 5 caídas ≥70% en un mismo build; se investigaron las 5 con datos
  reales (consulta directa a `data/gold/panel_opa.duckdb`, cada conclusión revisada por un
  segundo agente independiente con instrucción explícita de intentar refutarla). Resultado: el
  universo TOTAL del padrón (todos los ramos juntos, no solo los marcados) cae de forma
  sistemática entre 15% y 29% cada enero-marzo -- verificado en 2022, 2023, 2025 y 2026 --
  probablemente porque los proyectos plurianuales vigentes se re-registran/reautorizan
  presupuestalmente antes de volver a aparecer en el reporte trimestral. Ninguno de los 5 casos
  fue un archivo incompleto sin explicación: 2 fueron ese mismo patrón estacional (con parte de
  los proyectos "desaparecidos" reapareciendo intactos 1-2 trimestres después, mismo avance
  físico), 1 fue una reorganización administrativa real -- Entidades no Sectorizadas perdió 31
  de 41 proyectos porque IMSS-BIENESTAR obtuvo su propio ramo presupuestal (`id_ramo=56`, nuevo
  en 2026 T1), ya dado de alta en `dim_ramo_seed.csv` -- y 1 fue probable depuración real de
  estudios de preinversión estancados en 0% de avance (Turismo, 2025 T1). El test
  (`assert_conteo_ppi_por_ramo_estable.sql`) se ajustó para excluir a propósito las
  transiciones Q4→Q1 (fuente casi exclusiva de falsos positivos ya explicados por el ciclo
  fiscal); sigue activo para cualquier otra transición de trimestre. Esto también le da un
  mecanismo concreto a la alta volatilidad trimestral que motivó la consideración del panel
  anual en Fase 0 -- no es ruido aleatorio, es el ciclo de reautorización de inicio de año.
- **Deflactación (INPC de Banxico SIE, arquitectura sección 2.3) queda sin datos reales.** La API
  de Banxico exige un token de autoservicio que no corresponde generar en automático, y no se
  encontró un endpoint público sin token con la serie completa desde 2015. `conf/deflactor_inpc.csv`
  tiene el esquema correcto (columnas `anio, trimestre, inpc, anio_base`) pero vacío --
  `modificado_real`/`ejercido_real`/`monto_total_inversion_real` en `fct_ppi_observacion` existen
  y funcionan, simplemente salen `NULL` hasta que alguien con acceso a un token de Banxico SIE
  llene el CSV con la serie oficial. No se aproximó con un supuesto de inflación genérico.

## Alineación a los Lineamientos de Datos Abiertos de la ATDT (`docs/`, 2026-08-08)

El 11/09/2025 la Agencia de Transformación Digital y Telecomunicaciones (ATDT) publicó en el
DOF los ["Lineamientos en materia de Datos Abiertos de la Administración Pública
Federal"](docs/normativa/2025-09-11_ATDT_Lineamientos-Datos-Abiertos-APF.md) (PDF original
también en `docs/normativa/`) -- el estándar técnico vigente para datos abiertos federales en
México (DCAT, diccionario de datos, metadatos de procedencia y calidad). **Este repo no es una
Institución Publicante** (los Lineamientos obligan a la APF, no a un proyecto ciudadano), pero
el plan documentado en
[`docs/PLAN-alineacion-gold-lineamientos-ATDT.md`](docs/PLAN-alineacion-gold-lineamientos-ATDT.md)
adopta voluntariamente la parte técnica -- porque es el estándar de calidad correcto y porque
deja el dataset listo para integrarse a la Plataforma Nacional de Datos Abiertos si algún actor
institucional lo retoma. Verificado en vivo contra la API de `datos.gob.mx` (2026-08-08): el
panel OPA/PPI **no está duplicado** en la plataforma nacional -- 0 resultados para "Obra
Pública Abierta" o "programas y proyectos de inversión", y no existe ninguna organización de
Hacienda/SHCP entre las 25 registradas en el catálogo (reconstruido por la ATDT entre
septiembre y diciembre de 2025).

**Fase A -- Diccionario de datos, completa.** `dbt/models/marts/schema.yml` es ahora la fuente
única de las ~80 columnas publicables de las 8 tablas de Gold (antes 10 documentadas, el resto
sin descripción). `opa diccionario` cruza ese schema contra las columnas REALES del duckdb y
**falla ruidoso** (no advierte, se detiene) si aparece una columna sin descripción o una
descripción de una columna que ya no existe -- la deriva entre documentación y datos es un
error, igual que el resto de este pipeline. Escribe `reports/diccionario/` (versionado en git,
igual que el resto de `reports/`): un `diccionario_datos_{tabla}.csv` por tabla y un
`DICCIONARIO.md` consolidado.

**Fase B -- Exportador de distribuciones, completa.** `opa publish` escribe
`data/publish/{version}/` (fuera de git, mismo criterio que bronze/silver/gold) con las 8
tablas en CSV (RFC 4180, formato base que exigen los Lineamientos) y Parquet, más GeoJSON
(RFC 7946, un `FeatureCollection` por año de corte) como el extra de este proyecto sobre las
tablas georreferenciadas, y `checksums.sha256` verificable con `shasum -a 256 -c`. Construida
con 3 módulos independientes vía workflow multi-agente (implementación + revisión adversarial
por módulo, que encontró y corrigió 2 bugs reales: CSV sin CRLF pese a prometer RFC 4180, y
checksums ordenados por hash en vez de por ruta) e integrada a mano en el CLI. El GeoJSON viene
enriquecido con `nombre_ppi`/`descripcion_ur`/`localizacion` (de `dim_ppi`, unido por el rango
de vigencia SCD2 -- no la versión más reciente) más `trimestre_corte`, `fase` y los montos
`aprobado`/`ppef`/`pef`: 96.4% de los puntos de 2021 traen nombre real de proyecto. Verificado
contra el duckdb real: 30 archivos, checksums en verde, y una segunda corrida produce bytes
**idénticos** a la primera -- el determinismo se comprobó, no se asumió.

**Fase C -- Catálogo DCAT, completa.** `opa publish` ahora también escribe
`data/publish/{version}/catalog.json`, un catálogo DCAT (JSON-LD, vocabulario W3C estándar
`dcat:`/`dct:`/`foaf:`/`spdx:` -- ver `conf/dcat.yml` para lo declarativo) con un
`dcat:Dataset` por tabla y un `dcat:Distribution` por archivo real (tamaño y sha256
calculados sobre el archivo, no inventados). Los 13 GeoJSON se adjuntan al dataset
`fct_ppi_observacion`, de donde se derivan, en vez de aparecer como datasets sueltos.
También incluye `x-procedencia` y `x-calidad` -- resúmenes reales de `data/manifest.jsonl` y
`reports/calidad_silver.md` bajo un prefijo `x-` explícito, porque no son vocabulario DCAT
oficial (el Manual Operativo de la ATDT sigue sin publicarse). Construida con 4 agentes
coordinados en 2 etapas (dos módulos independientes en paralelo + revisión adversarial cada
uno, luego el generador que depende de ambos + su propia revisión) e integrada a mano en el
CLI, con `checksums.sha256` corriendo al final para cubrir también `catalog.json`. Verificado
contra el paquete real: 8 datasets, 15 distribuciones en `fct_ppi_observacion`, checksums en
verde, y el paquete completo produce bytes idénticos en una segunda corrida.

Pendiente del plan: **Fase D** (evaluación de datos personales + nota técnica de limitaciones
empaquetada con los datos).

## Cómo correr Fase 0 + Bronze + Silver + Gold

Requiere [`uv`](https://docs.astral.sh/uv/) y Python 3.12 (gestionado automáticamente por `uv`).

```bash
# UV_NO_EDITABLE evita un problema de instalación editable observado en algunos
# entornos sandbox (el .pth de instalación editable no se procesa). No hace
# falta en una máquina normal, pero tampoco estorba -- uv run vuelve a
# sincronizar el entorno en cada invocación, así que se exporta una sola vez.
export UV_NO_EDITABLE=1
uv sync

# Descubrimiento: prueba ~480 URLs candidatas contra la SHCP (a 1 req/2s, ≈45-50 min
# en la práctica), consulta el mirror CKAN de datos.gob.mx y la CDX API de Wayback.
# Escribe reports/discovery.jsonl y reports/cobertura.md.
uv run opa discover

# Descarga 3 snapshots representativos (más antiguo, ~2019-2020, más reciente)
# a data/muestras/ e inspecciona sus esquemas en reports/esquemas.md.
uv run opa inspect

# Bronze: descarga completa (no solo metadatos) de todo lo que discover encontró con
# existe=True y extensión de datos real (csv/xlsx/json) -- ~164 candidatas, ≈10 min a 1
# req/2s. Escribe data/bronze/ (crudo, fuera de git) y data/manifest.jsonl (procedencia,
# versionado). Idempotente: correrlo de nuevo solo descarga lo que falte.
uv run opa bronze

# Silver: normaliza cada snapshot con esquema conocido (conf/schema_map.yml) a parquet
# canónico -- sin red, todo local. Escribe data/silver/*.parquet (fuera de git) y
# reports/calidad_silver.md. Sale con código 1 si aparece un esquema no mapeado o un
# error de lectura (falla ruidoso a propósito, ver ARQUITECTURA sección 5.3).
uv run opa normalize

# Gold: seeds + modelos dbt + tests, todo en un solo comando. Escribe
# data/gold/panel_opa.duckdb (fuera de git). --project-dir y --profiles-dir son
# necesarios porque dbt/ no es la raíz del repo.
dbt build --project-dir dbt --profiles-dir dbt

# Diccionario de datos (Fase A de la alineación a Lineamientos ATDT, ver arriba). Falla
# ruidoso si hay columnas reales sin documentar en dbt/models/marts/schema.yml. Escribe
# reports/diccionario/ (versionado en git).
uv run opa diccionario

# Publicación de distribuciones (Fase B) + catálogo DCAT (Fase C). CSV + Parquet + GeoJSON +
# catalog.json (DCAT) + checksums.sha256 (cubre también catalog.json) en
# data/publish/{version}/ (fuera de git) -- version por defecto = corte más reciente del
# duckdb (ej. 2026T1), o pasa --version explícito.
uv run opa publish
```

Reportes producidos:

| Archivo | Contenido |
|---|---|
| `reports/discovery.jsonl` | Un renglón por URL/consulta probada, con resultado crudo |
| `reports/cobertura.md` | Matriz año × trimestre (vivo / espejo / wayback / hueco) y recomendación |
| `reports/esquemas.md` | Comparación de columnas y calidad entre las 3 muestras descargadas |
| `data/manifest.jsonl` | Un renglón por snapshot bronze: url, origen, sha256, corte declarado, header_hash |
| `reports/calidad_silver.md` | Un renglón por snapshot normalizado: filas válidas/rechazadas y por qué |
| `data/gold/panel_opa.duckdb` | Base DuckDB con el modelo dimensional completo -- consultable con cualquier cliente SQL de DuckDB |

## Alcance de esta sesión (Fase 0 + Fase 1 + Bronze + Silver + Gold)

Reconocimiento completo (inventario de URLs, matriz de cobertura, inspección de esquemas), Bronze
(todos los snapshots recuperables descargados completos, hasheados y con procedencia
documentada), Silver (`conf/schema_map.yml`, `src/opa/contracts.py`, `src/opa/normalize.py` --
98.9% de las filas reales validadas), y Gold (`dbt/`: `fct_ppi_observacion`, `dim_ppi` SCD2,
`fct_ppi_delta`, `fct_ppi_ciclo_vida`, catálogos, 39/40 tests). **Pendiente para una sesión
futura:** la serie real de INPC de Banxico SIE para deflactación (requiere un token que no
corresponde generar en automático -- ver la sección de Gold arriba), normalizar las variantes de
texto de `estatus_operacion`/`descripcion_tipo_ppi`, y la capa de publicación (MkDocs,
DuckDB-WASM, servidor MCP, Zenodo/Hugging Face) descrita en la arquitectura.

## Licencia

El código de este repositorio está bajo licencia [MIT](LICENSE).

Los **datos** de OPA son un conjunto separado, sujeto a los **Términos de Libre Uso MX**
(datos.gob.mx/libreusomx) bajo el "Decreto por el que se establece la regulación en materia de
Datos Abiertos" (DOF 20/02/2015). Toda redistribución debe citar: nombre del conjunto de datos,
siglas de la dependencia (SHCP), liga de los datos descargados y fecha de consulta en formato
`AAAA-MM-DD`.
