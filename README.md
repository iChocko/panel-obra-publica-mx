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

## Estado: Fase 0 + Fase 1 — Reconocimiento y resolución del hueco 2022-2026 (2026-08-08)

**Recuperabilidad trimestral 2016–2024: 22 / 36 (61.1%) → por encima del 50%.**

**Recomendación: panel trimestral parcial**, con los huecos restantes documentados como *feature*
del reporte de calidad -- no el pivote a panel anual que había recomendado la primera corrida.
Detalle completo en [`reports/cobertura.md`](reports/cobertura.md).

> **Nota de transparencia metodológica:** la corrida original de Fase 0 (2026-08-05) midió 4/36
> (11.1%) y recomendó pivotar a panel anual. Fase 1 (2026-08-08) investigó por qué 2022-2026 no
> respondía bajo ningún patrón conocido y encontró que el portal había renombrado los archivos
> trimestrales, no descontinuado la sección -- esa corrección subió la cifra a 22/36. El número y
> la recomendación **vigentes son los de arriba**; se documenta el original por trazabilidad, no
> como estado actual.

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
- **La hipótesis de que OPA se fusionó con el Tomo VIII del PEF es falsa.** Tomo VIII sí tiene un
  CSV real y vivo 2022-2025 (`REPORTE_TOMO_VIII.csv`), pero es presupuesto ex-ante -- sin avance
  físico, monto ejercido ni geolocalización -- nunca pudo sustituir a OPA en granularidad. Son
  complementarios, no sucesores.
- **Los 14 trimestres que siguen como hueco (2016-2024) son reales, no un patrón sin descubrir
  todavía:** 2016 completo, partes de 2017-2018 y 2020, y 2019 completo -- este último usa una
  tercera nomenclatura irregular (`opa_trimestral.csv`, `OPASegundoTrimestre2019.csv`, etc.) que no
  se mapeó en esta fase. Quedan documentados como huecos en `reports/cobertura.md`.
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

# Descubrimiento: prueba ~470 URLs candidatas contra la SHCP (a 1 req/2s, ≈45-50 min
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

## Licencia de los datos

Los datos de OPA están sujetos a los **Términos de Libre Uso MX** (datos.gob.mx/libreusomx) bajo
el "Decreto por el que se establece la regulación en materia de Datos Abiertos" (DOF 20/02/2015).
Toda redistribución debe citar: nombre del conjunto de datos, siglas de la dependencia (SHCP),
liga de los datos descargados y fecha de consulta en formato `AAAA-MM-DD`.
