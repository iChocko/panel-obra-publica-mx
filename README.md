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

## Estado: Fase 0 — Reconocimiento (completa, 2026-08-05)

**Recuperabilidad trimestral 2016–2024: 4 / 36 (11.1%) → por debajo del 50%.**

**Recomendación: pivotar a panel anual** (Tomo VIII del PEF + OPA anual), complementado con SRFT
para la capa subnacional georreferenciada. Detalle completo en
[`reports/cobertura.md`](reports/cobertura.md).

Hallazgos clave de esta fase:

- **La hipótesis original era optimista en el detalle equivocado.** Los archivos con nombre de
  trimestre explícito (`proyectos_opa_01t2017.csv`, `reporteOPA3erTrimestre.xlsx`) casi no
  sobrevivieron: solo 4 de 36 trimestres 2016-2024 son recuperables por esa vía (vivo o Wayback).
  El patrón antiguo cuenta con la esperanza puesta ahí, y no se sostiene con datos reales.
- **Pero el archivo anual genérico sí es sólido 2015-2021**, vivo en el servidor de la SHCP hoy
  mismo (verificado, no solo inferido). Eso es exactamente el insumo que necesita un panel anual.
- **2022-2026 no responden bajo ningún patrón conocido** (404 limpios, no bloqueo). Sin investigar
  en esta fase si la sección se descontinuó o cambió de URL — es lo primero que resolver en Fase 1
  antes de dar por buena la cobertura anual hacia el presente.
- **El esquema cambia de forma importante entre 2015 y 2019/2021** (45 vs. 47 columnas, `CVE_PPI`
  vs. `CVE_CARTERA`, nombres de columna casi todos distintos). 2019 y 2021 comparten esquema.
- **`cve_cartera` no es el código numérico de 10-11 dígitos que asumía la arquitectura**: en 2019 y
  2021 aparecen valores como `'2151GYN0003` (0% cumple `^\d{10,11}$`). El contrato Pandera de la
  arquitectura (sección 6.1) necesita revisarse en Fase 2 con datos reales, no con la forma
  esperada.
- **El mirror de datos.gob.mx (CKAN, id `56b98e14-...`) ya no existe** en el catálogo actual: 404
  directo y 0 coincidencias reales buscando por nombre (la búsqueda por palabra suelta sí devuelve
  21 resultados, pero ninguno es OPA). `datamx.io` tampoco tiene referencia. La Fuente 2 no aportó
  cobertura -- Wayback y el servidor vivo son las únicas fuentes reales.
- **Wayback Machine sí archivó archivos de datos, no solo HTML**: 90 capturas con mimetype real
  (`text/csv`, `.xlsx`) entre 2016 y 2024, sin bloqueo ni rate-limit de la CDX API.

Ver [`reports/esquemas.md`](reports/esquemas.md) para el detalle columna por columna de las 3
muestras (2015, 2019, 2021).

## Cómo correr Fase 0

Requiere [`uv`](https://docs.astral.sh/uv/) y Python 3.12 (gestionado automáticamente por `uv`).

```bash
# UV_NO_EDITABLE evita un problema de instalación editable observado en algunos
# entornos sandbox (el .pth de instalación editable no se procesa). No hace
# falta en una máquina normal, pero tampoco estorba -- uv run vuelve a
# sincronizar el entorno en cada invocación, así que se exporta una sola vez.
export UV_NO_EDITABLE=1
uv sync

# Descubrimiento: prueba ~280 URLs candidatas contra la SHCP (a 1 req/2s, ≈25-30 min
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

## Alcance de esta sesión (Fase 0)

Solo reconocimiento: inventario de URLs, matriz de cobertura con números reales, e inspección de
esquemas de muestra. **No hay pipeline de ingesta, normalización ni modelos todavía** — eso
corresponde a las fases 1 en adelante, descritas en el documento de arquitectura.

## Licencia de los datos

Los datos de OPA están sujetos a los **Términos de Libre Uso MX** (datos.gob.mx/libreusomx) bajo
el "Decreto por el que se establece la regulación en materia de Datos Abiertos" (DOF 20/02/2015).
Toda redistribución debe citar: nombre del conjunto de datos, siglas de la dependencia (SHCP),
liga de los datos descargados y fecha de consulta en formato `AAAA-MM-DD`.
