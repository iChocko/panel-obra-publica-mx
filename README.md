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

## Estado: Fase 0 — Reconocimiento

_Pendiente de ejecución. Esta sección se actualiza al final de la Fase 0 con la recuperabilidad
real medida y la recomendación resultante de la puerta de decisión._

## Cómo correr Fase 0

Requiere [`uv`](https://docs.astral.sh/uv/) y Python 3.12 (gestionado automáticamente por `uv`).

```bash
# UV_NO_EDITABLE evita un problema de instalación editable observado en algunos
# entornos sandbox (el .pth de instalación editable no se procesa). No hace
# falta en una máquina normal, pero tampoco estorba -- uv run vuelve a
# sincronizar el entorno en cada invocación, así que se exporta una sola vez.
export UV_NO_EDITABLE=1
uv sync

# Descubrimiento: prueba ~280 URLs candidatas contra la SHCP (a 1 req/2s, ≈10-18 min),
# consulta el mirror CKAN de datos.gob.mx y la CDX API del Wayback Machine.
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
