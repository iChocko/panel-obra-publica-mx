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

Esto sigue siendo descubrimiento -- **no hay pipeline de ingesta, normalización ni modelos
todavía**, eso corresponde a Bronze (la Fase 1 formal del roadmap de arquitectura) en adelante.

## Cómo correr Fase 0

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
```

Reportes producidos:

| Archivo | Contenido |
|---|---|
| `reports/discovery.jsonl` | Un renglón por URL/consulta probada, con resultado crudo |
| `reports/cobertura.md` | Matriz año × trimestre (vivo / espejo / wayback / hueco) y recomendación |
| `reports/esquemas.md` | Comparación de columnas y calidad entre las 3 muestras descargadas |

## Alcance de esta sesión (Fase 0 + Fase 1: descubrimiento)

Solo reconocimiento: inventario de URLs (incluida la resolución del cambio de patrón 2022-2026),
matriz de cobertura con números reales, e inspección de esquemas de muestra. **No hay pipeline de
ingesta, normalización ni modelos todavía** — eso corresponde a Bronze y las fases siguientes,
descritas en el documento de arquitectura.

## Licencia

El código de este repositorio está bajo licencia [MIT](LICENSE).

Los **datos** de OPA son un conjunto separado, sujeto a los **Términos de Libre Uso MX**
(datos.gob.mx/libreusomx) bajo el "Decreto por el que se establece la regulación en materia de
Datos Abiertos" (DOF 20/02/2015). Toda redistribución debe citar: nombre del conjunto de datos,
siglas de la dependencia (SHCP), liga de los datos descargados y fecha de consulta en formato
`AAAA-MM-DD`.
