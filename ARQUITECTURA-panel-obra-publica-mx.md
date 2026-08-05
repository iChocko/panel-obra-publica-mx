# Panel Histórico de Obra Pública Federal (México)
## Arquitectura del proyecto

**Repo propuesto:** `panel-obra-publica-mx`
**Dataset publicado:** `panel-ppi-mx`
**Autor:** José Luis Rosas Mora (`@iChocko`)
**Estado:** diseño — previo a Fase 0

---

## 1. Tesis del proyecto

> La SHCP publica cada trimestre una fotografía del universo de proyectos de inversión federal. Cada fotografía nueva reemplaza a la anterior. **La fuente destruye su propia historia.** Este repositorio la reconstruye.

De ahí se deriva toda la arquitectura: el objeto de valor no es un archivo, es **la serie de archivos**. Cada snapshot es un hecho inmutable con fecha; el panel es la unión ordenada de esos hechos. Esto obliga a un diseño de *event sourcing* sobre datos públicos, no a un ETL convencional.

**Contribución diferenciada frente a lo existente:** México Evalúa, IMCO y otros analizan casos y agregados. Nadie publica la trayectoria trimestral por clave de cartera. Ese es el hueco.

---

## 2. Modelo conceptual

### 2.1 Grano y llaves

| Concepto | Definición | Llave |
|---|---|---|
| **Snapshot** | Un archivo publicado por la SHCP, con su corte declarado | `snapshot_id` = `{anio}Q{trim}_{sha8}` |
| **PPI** | Un programa o proyecto de inversión registrado en cartera | `cve_cartera` |
| **Observación** | Estado de un PPI en un snapshot | `(cve_cartera, snapshot_id)` |

El grano base del panel es la **observación**. Todo lo demás se deriva.

### 2.2 El problema difícil: identidad y desaparición

Tres patologías que hay que resolver explícitamente y **documentar como limitación metodológica**, no esconder:

1. **Re-registro.** Un proyecto cancelado y vuelto a registrar recibe clave nueva. La continuidad se pierde. → Mitigación: tabla de enlaces candidatos por similitud de nombre + ramo + UR + coordenadas, marcada como `inferido`, nunca aplicada silenciosamente al panel base.
2. **Desaparición ≠ cancelación.** Un PPI que deja de aparecer pudo terminarse, cancelarse, o salir del universo de reporte. → Mitigación: campo `estatus_inferido` con reglas explícitas (avance físico ≥ 95% en último corte → `terminado_probable`; avance < 95% y desaparición abrupta → `salida_no_explicada`).
3. **Cambio de alcance vs. sobrecosto.** Un incremento de monto puede reflejar más obra, no ineficiencia. Los datos abiertos **no permiten separarlos limpiamente**. → Mitigación: reportar sobrecosto junto con Δ de meta física cuando exista, y declarar la ambigüedad en el README y en cada notebook.

### 2.3 Deflactación

Todo análisis de sobrecosto en pesos nominales es ruido. El panel incorpora una capa de deflactación con **INPC de Banxico (SIE)** a pesos constantes de un año base declarado, con la serie de deflactores versionada dentro del repo para garantizar reproducibilidad exacta.

---

## 3. Estructura del repositorio

```
panel-obra-publica-mx/
├── README.md                     # tesis, cobertura, cómo usar, cita
├── LICENSE                       # MIT (código)
├── LICENSE-DATA.md               # Términos de Libre Uso MX (datos)
├── CITATION.cff
├── CHANGELOG.md                  # SemVer del dataset
├── METODOLOGIA.md                # reglas de identidad, deflactación, limitaciones
├── pyproject.toml                # gestionado con uv
│
├── .github/workflows/
│   ├── discover.yml              # barrido de URLs candidatas (mensual)
│   ├── ingest.yml                # descarga de cortes nuevos (trimestral + manual)
│   ├── build.yml                 # dbt build + tests (en cada push)
│   ├── release.yml               # empaqueta y publica assets + Zenodo
│   └── docs.yml                  # MkDocs → GitHub Pages
│
├── conf/
│   ├── sources.yml               # patrones de URL conocidos por año/trimestre
│   ├── schema_map.yml            # columna histórica → columna canónica
│   ├── catalogos/                # ramo, UR, entidad, tipo PPI (congelados)
│   └── settings.toml
│
├── src/opa/
│   ├── discovery.py              # enumera URLs vivas + consulta CDX de Wayback
│   ├── fetch.py                  # descarga con UA identificable, retry, backoff
│   ├── manifest.py               # registro append-only de snapshots
│   ├── normalize.py              # crudo → parquet canónico
│   ├── contracts.py              # esquemas Pandera
│   ├── deflactor.py              # INPC Banxico SIE
│   └── cli.py                    # Typer: opa discover|fetch|normalize|build
│
├── dbt/                          # dbt-duckdb
│   ├── models/staging/           # stg_opa_snapshot
│   ├── models/intermediate/      # int_ppi_deltas, int_ppi_identidad
│   ├── models/marts/             # fct_*, dim_*
│   ├── seeds/                    # catálogos
│   └── tests/                    # tests singulares
│
├── data/
│   ├── manifest.jsonl            # ✅ versionado en git (trazabilidad total)
│   ├── bronze/                   # ❌ fuera de git → R2 / HF
│   ├── silver/
│   └── gold/
│
├── notebooks/                    # 01_cobertura … 05_geografia
├── docs/                         # MkDocs Material + DuckDB-WASM
└── mcp/                          # servidor MCP sobre el .duckdb
```

---

## 4. Capas de datos (medallion)

### 4.1 Bronze — snapshots inmutables

El archivo original, **byte por byte, sin tocar**. Nombre determinista:

```
bronze/opa_{anio}_{trimestre}_{sha8}.{ext}
```

Cada descarga escribe un renglón en `data/manifest.jsonl` (append-only, versionado en git):

```json
{
  "snapshot_id": "2019Q3_a3f91c02",
  "url": "https://www.transparenciapresupuestaria.gob.mx/work/models/PTP/DatosAbiertos/OPA/2019/proyectos_opa.csv",
  "origen": "wayback",
  "wayback_timestamp": "20191118143022",
  "fecha_descarga": "2026-08-04",
  "http_status": 200,
  "sha256": "a3f91c02...",
  "bytes": 4821904,
  "corte_declarado": {"anio": 2019, "trimestre": 3},
  "header_hash": "7d2e...",
  "n_columnas": 39,
  "encoding_detectado": "latin-1"
}
```

El manifiesto vive en git porque es pequeño, es la prueba de procedencia, y satisface el requisito de cita de los Términos de Libre Uso MX (liga + fecha `AAAA-MM-DD`).

**Regla dura:** bronze nunca se reescribe. Si la SHCP corrige un archivo, entra como snapshot nuevo con hash distinto.

### 4.2 Silver — canónico

Parquet, un archivo por snapshot, esquema unificado. Aquí se resuelve el desorden histórico:

- Encoding normalizado a UTF-8 (los cortes viejos vienen en `latin-1`)
- Nombres de columna mapeados vía `schema_map.yml` (el esquema cambió entre años; el mapeo es explícito y auditable)
- Tipos forzados: montos a `decimal`, fechas a `date`, coordenadas a `float64`
- `cve_cartera` normalizada (padding de ceros, sin espacios)
- Columna `snapshot_id` añadida a cada renglón
- Validación Pandera antes de escribir

### 4.3 Gold — el panel

| Modelo | Grano | Contenido |
|---|---|---|
| `fct_ppi_observacion` | `(cve_cartera, snapshot_id)` | Panel largo. Montos nominales y reales, avance físico, estatus. **Tabla central.** |
| `dim_ppi` | `cve_cartera` + vigencia | SCD2 sobre atributos que cambian: nombre, ramo, UR, tipo, localización, coordenadas |
| `fct_ppi_delta` | `(cve_cartera, snapshot_id)` | Cambio contra el corte inmediato anterior: Δmonto nominal y real, Δavance, cambio de estatus, bandera de re-nombramiento |
| `fct_ppi_ciclo_vida` | `cve_cartera` | Un renglón por PPI: primer y último corte, monto inicial vs. final, sobrecosto %, duración planeada vs. observada, estatus terminal inferido |
| `dim_snapshot` | `snapshot_id` | Metadatos del corte, conteo de PPI, banderas de calidad |
| `dim_ramo`, `dim_entidad`, `dim_tipo_ppi` | — | Catálogos congelados |

**Por qué SCD2 en `dim_ppi` y no en el fact:** los montos cambian cada trimestre por diseño (eso es la señal, va al fact). Los atributos descriptivos cambian rara vez y esos cambios son en sí mismos informativos — un PPI que cambia de nombre o de coordenadas merece una fila nueva con vigencia.

---

## 5. Ingesta y descubrimiento

### 5.1 Estrategia en cascada

```
1. URLs vivas        →  patrones conocidos × años × trimestres, HEAD requests
2. Mirrors           →  datos.gob.mx, datamx.io (cobertura 2016–2018)
3. Wayback CDX       →  huecos donde el nombre genérico fue sobreescrito
4. Registro de fallo →  hueco documentado en dim_snapshot, no silenciado
```

`discovery.py` genera el producto cartesiano de patrones (`proyectos_opa.csv`, `proyectos_opa_0Nt{anio}.csv/.xlsx`, `reporteOPA{1er..4to}Trimestre*.xlsx`, patrón antiguo `/PTP/OPA/{anio}/Proyectos_OPA.csv`), prueba cada uno, y escribe un reporte de cobertura antes de descargar nada.

Para Wayback, consulta CDX (que debe ejecutarse desde entorno sin bloqueo):

```
http://web.archive.org/cdx/search/cdx
  ?url=transparenciapresupuestaria.gob.mx/work/models/PTP/DatosAbiertos/OPA*
  &output=json&collapse=digest
  &fl=original,timestamp,statuscode,mimetype,length
  &filter=statuscode:200&filter=!mimetype:text/html
```

`collapse=digest` es clave: colapsa capturas idénticas y deja solo los cortes que realmente cambiaron. Eso convierte el ruido del archivo web en la serie de snapshots.

### 5.2 Higiene de scraping

El sitio bloquea bots vía `robots.txt`. La postura del proyecto:

- User-Agent identificable con URL del repo y correo de contacto — transparencia, no evasión
- Rate limit conservador (1 req cada 2 s), backoff exponencial
- Descarga única por snapshot: una vez en bronze con su hash, nunca se vuelve a pedir
- El volumen total es de decenas de archivos, no de un crawl masivo

### 5.3 Detección de cambio de esquema

`header_hash` se compara contra el conjunto de esquemas conocidos en `schema_map.yml`. Si aparece uno nuevo:

1. El pipeline **falla ruidosamente** (no adivina el mapeo)
2. Abre un issue automático con el diff de columnas
3. El snapshot queda en bronze, marcado como `pendiente_mapeo`

Esto es lo que separa un pipeline serio de un script: la fuente va a cambiar y el sistema tiene que decirlo, no tragárselo.

---

## 6. Calidad de datos

### 6.1 Contratos Pandera (frontera bronze → silver)

```python
class OPASnapshot(pa.DataFrameModel):
    cve_cartera: Series[str] = pa.Field(str_matches=r"^\d{10,11}$", nullable=False)
    anio: Series[int] = pa.Field(ge=2008, le=2030)
    avance_fisico: Series[float] = pa.Field(ge=0, le=100, nullable=True)
    latitud: Series[float] = pa.Field(ge=14.5, le=32.8, nullable=True)   # bbox MX
    longitud: Series[float] = pa.Field(ge=-118.5, le=-86.7, nullable=True)
    monto_total_inversion: Series[float] = pa.Field(ge=0, nullable=True)

    @pa.dataframe_check
    def montos_coherentes(cls, df):
        return df["ejercido"] <= df["modificado"] * 1.05  # tolerancia
```

### 6.2 Tests dbt

- `unique` en `(cve_cartera, snapshot_id)`
- `relationships` de fact a `dim_ramo`, `dim_entidad`, `dim_snapshot`
- `accepted_values` en `estatus_operacion`, `tipo_ppi`
- Singular: ningún PPI puede tener avance físico decreciente entre cortes sin bandera
- Singular: la suma de montos por ramo y corte debe ser estable ±X% contra el corte previo (detecta cargas truncadas)

### 6.3 Reporte de calidad publicado

Página autogenerada en el sitio de docs, con:
- Matriz de cobertura año × trimestre (verde = vivo, ámbar = Wayback, rojo = hueco)
- % de nulos por campo y por año
- Conteo de PPI por corte con detección de saltos anómalos
- Log de cambios de esquema

**Este reporte es parte del producto, no un anexo.** Publicar los huecos honestamente es lo que hace citable el dataset.

---

## 7. Orquestación

| Workflow | Trigger | Función |
|---|---|---|
| `discover.yml` | cron mensual | Barre URLs candidatas, actualiza reporte de cobertura, abre issue si aparece corte nuevo |
| `ingest.yml` | cron trimestral (día 25 del mes posterior al cierre) + `workflow_dispatch` | Descarga cortes nuevos, valida, escribe bronze + manifest |
| `build.yml` | push a `main` | `dbt build` completo con tests; falla el PR si algún test rompe |
| `release.yml` | tag `v*` | Empaqueta CSV/Parquet/GeoParquet/`.duckdb`, publica en GitHub Releases + HF, dispara Zenodo |
| `docs.yml` | push a `main` | MkDocs → GitHub Pages |

**Todo corre en GitHub Actions.** Costo cero, y el runner público es en sí una demostración de reproducibilidad: cualquiera puede ver el log completo de cómo se construyó cada versión.

### Almacenamiento de datos pesados

Git no aguanta decenas de snapshots. Distribución:

- **`data/manifest.jsonl`** → git (KB, es la trazabilidad)
- **Bronze completo** → Cloudflare R2 (egress gratis) como archivo de procedencia
- **Gold empaquetado** → GitHub Releases (assets versionados) + **Hugging Face Datasets** como espejo primario de consumo

---

## 8. Publicación

### Formatos por release

| Formato | Para quién |
|---|---|
| `panel_ppi.csv.gz` | Compatibilidad universal, Excel, R base |
| `panel_ppi.parquet` | Analítico — pandas, polars, DuckDB |
| `panel_ppi.geoparquet` | QGIS, GeoPandas, análisis espacial |
| `panel_ppi.duckdb` | **SQL inmediato, cero setup** — el formato estrella |
| `diccionario.md` + `.xlsx` | Documentación, autogenerado desde dbt docs |

### Versionado

- **MAJOR** — ruptura de esquema o cambio de metodología de identidad
- **MINOR** — trimestre nuevo incorporado, o hueco histórico rellenado
- **PATCH** — corrección de bug sin cambio de esquema

`CHANGELOG.md` documenta, por versión, qué snapshots entraron y qué reglas cambiaron.

### Citabilidad

- `CITATION.cff` en la raíz → GitHub genera el botón "Cite this repository"
- Integración Zenodo con GitHub Releases → **DOI por versión**, citable en papers
- El README incluye la cita a la fuente en el formato exacto que exigen los Términos de Libre Uso MX: nombre del conjunto, siglas de la dependencia, liga y fecha de consulta `AAAA-MM-DD`

---

## 9. Capa de consumo

### 9.1 Sitio de documentación

MkDocs Material en GitHub Pages:
- Tesis y cobertura real (con la matriz de huecos visible)
- Diccionario de datos navegable
- Metodología: reglas de identidad, deflactación, limitaciones
- Recetario: 10 consultas SQL listas para copiar

### 9.2 Consola SQL en el navegador (DuckDB-WASM)

Página estática que carga el Parquet desde R2 mediante *range requests* de `httpfs`. El visitante escribe SQL y obtiene resultados **sin backend, sin costo de servidor, sin descargar el dataset completo**.

Es el detalle que convierte un repo de datos en un producto, y es exactamente el tipo de decisión de arquitectura que se nota en un portafolio.

### 9.3 Servidor MCP

Sobre el `.duckdb`, con herramientas acotadas:

| Herramienta | Función |
|---|---|
| `buscar_ppi` | Por nombre, clave, ramo, entidad |
| `serie_ppi` | Trayectoria trimestral completa de un PPI |
| `ranking_sobrecosto` | Top N por desviación real, con filtros |
| `cobertura_panel` | Qué trimestres existen y cuáles son huecos |
| `query_sql` | Escape hatch de solo lectura |

---

## 10. Capa analítica — el gancho

Cinco preguntas priorizadas. **Cada notebook es reproducible end-to-end desde el `.duckdb` publicado.**

| # | Pregunta | Método | Por qué importa |
|---|---|---|---|
| **P1** | ¿Cuánto crece el costo real de un PPI entre su primer y último registro? | Distribución de sobrecosto deflactado por tipo de PPI y ramo; medianas y colas | Es la métrica que México no tiene sistematizada |
| **P2** | ¿Cuánto se desliza el calendario? | Fecha fin planeada vs. permanencia efectiva en cartera; supervivencia (Kaplan-Meier) | Complementa P1: el costo del tiempo |
| **P3** | ¿Los PPI evaluados con ACB se desvían menos que los de ACE? | Comparación por `tipo_ppi`, controlando monto, ramo y sexenio | **Tu terreno.** Es una pregunta sobre si la evaluación socioeconómica sirve |
| **P4** | ¿Dónde se concentra la inversión y coincide con la demanda? | Análisis espacial; para el subconjunto carretero, cruce con TDPA de `Datos-Viales-SICT` | Enlaza tus dos repos — nadie más puede hacer ese cruce |
| **P5** | ¿Qué pasó con la cartera en los cambios de administración 2018 y 2024? | Event study sobre tasas de cancelación y reprogramación | Pregunta de economía política con evidencia dura |

**Advertencia metodológica obligatoria en todos:** solo se observan proyectos que llegaron a cartera. Hay selección. Los resultados describen el universo registrado, no el universo de necesidades.

---

## 11. Roadmap con criterios de decisión

### Fase 0 — Reconocimiento (2–3 días)
Ejecutar `discovery.py`. Producir la matriz de cobertura. **No escribir nada de pipeline todavía.**

**Puerta de decisión (según el dictamen):**

| Recuperabilidad 2016–2024 | Decisión |
|---|---|
| **≥ 70%** | Panel trimestral completo. Alcance original. |
| **50–70%** | Panel trimestral parcial, con huecos documentados como *feature* del reporte de calidad. |
| **< 50%** | **Pivotar a panel anual** (Tomo VIII + OPA anual, mucho más robusto) + SRFT para la capa subnacional georreferenciada. |

### Fase 1 — Bronze (1 semana)
Ingesta, manifiesto, almacenamiento. Al final: todos los snapshots recuperables, hasheados y archivados. Esta fase es irreversible en el buen sentido: aunque la SHCP retire el portal mañana, los datos ya están preservados.

### Fase 2 — Silver + contratos (1 semana)
`schema_map.yml` completo, Pandera, parquet canónico. Aquí es donde vive el trabajo real y donde aparecerán las sorpresas.

### Fase 3 — Gold + dbt (1–2 semanas)
Modelos dimensionales, SCD2, reglas de identidad, deflactación, suite de tests.

### Fase 4 — Publicación (3–4 días)
Release `v1.0.0`, Zenodo, HF, MkDocs, DuckDB-WASM, MCP.

### Fase 5 — Análisis (continuo)
P1 y P3 primero — son los de mayor densidad de hallazgo por hora invertida. P1 da el titular; P3 da la credibilidad técnica.

---

## 12. Riesgos y mitigaciones

| Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|
| Wayback no archivó los CSV, solo el HTML | Media | **Alto** — mata el alcance trimestral | Puerta de decisión de Fase 0; plan B anual ya definido |
| La SHCP retira o rediseña la sección | Media | Medio | Bronze preservado desde Fase 1; el repo se vuelve *más* valioso, no menos |
| Esquema cambia entre años más de lo previsto | **Alta** | Medio | `schema_map.yml` explícito + falla ruidosa; presupuestar tiempo extra en Fase 2 |
| Re-registro de claves corrompe el análisis de ciclo de vida | Media | Medio | Enlaces marcados como inferidos, nunca aplicados al panel base |
| Sobrecosto confundido con cambio de alcance | **Alta** | Medio | Reportar junto con Δ meta física; declarar la limitación en README, METODOLOGIA y cada notebook |
| Bloqueo por robots/rate limiting | Baja | Bajo | UA identificable, ritmo conservador, descarga única por snapshot |

---

## 13. Stack

| Capa | Herramienta | Por qué |
|---|---|---|
| Entorno | **uv** | Reproducibilidad y velocidad; lockfile en el repo |
| CLI | **Typer** | Cada fase del pipeline es un comando invocable |
| Ingesta | **httpx** | Async, retries, timeouts |
| Contratos | **Pandera** | Validación declarativa en la frontera |
| Transformación | **dbt-duckdb** | Linaje, tests y docs gratis; SQL auditable |
| Motor | **DuckDB** | Todo el panel cabe en memoria; sin infraestructura |
| Geo | **GeoPandas + GeoParquet** | Salida directa a QGIS |
| Orquestación | **GitHub Actions** | Costo cero, log público = reproducibilidad demostrable |
| Docs | **MkDocs Material** | Rápido, buen buscador, GitHub Pages nativo |
| Distribución | **GitHub Releases + Hugging Face + Zenodo** | Versionado, alcance y DOI |

**Nota sobre lo que NO está aquí:** ni Airflow, ni Dagster, ni Postgres, ni Docker. El dataset cabe en un DuckDB de pocos cientos de MB y se actualiza cuatro veces al año. Meter orquestación pesada sería sobre-ingeniería, y en un portafolio la sobre-ingeniería se lee como falta de criterio. GitHub Actions con cron es la respuesta correcta al problema real.

---

## 14. Primer commit

```bash
uv init panel-obra-publica-mx && cd panel-obra-publica-mx
uv add httpx pandas pyarrow duckdb pandera typer geopandas
uv add --dev dbt-core dbt-duckdb pytest ruff mkdocs-material

mkdir -p src/opa conf data/{bronze,silver,gold} dbt notebooks docs .github/workflows
touch data/manifest.jsonl
```

Y lo primero que se escribe es `src/opa/discovery.py`. Nada más, hasta tener la matriz de cobertura.

---

*Documento de arquitectura — v0.1*
