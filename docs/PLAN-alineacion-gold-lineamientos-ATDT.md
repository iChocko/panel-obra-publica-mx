# Plan: alinear la capa Gold a los Lineamientos de Datos Abiertos de la ATDT

**Fecha:** 2026-08-08
**Referencia normativa:** [Acuerdo DOF 11/09/2025](normativa/2025-09-11_ATDT_Lineamientos-Datos-Abiertos-APF.md)
(transcripción completa en este repo; PDF original en `docs/normativa/`).
**Estado:** Fase A completa (2026-08-08). Fases B, C, D pendientes.

---

## 1. Alcance honesto: qué aplica a este repo y qué no

Este repositorio **no es una Institución Publicante** (Art. 3-XIX): es un proyecto ciudadano de
portafolio que reconstruye y redistribuye datos públicos de la SHCP. Los Lineamientos obligan a la
APF, no a este repo. La alineación que este plan propone es **voluntaria y solo técnica**: adoptar
las características de los datos (Art. 5), los criterios de publicación (Art. 38), el proceso de
contexto/metadatos (Art. 39-III) y el estándar DCAT (Art. 3-XIV), porque son el estándar de calidad
correcto y porque deja el dataset listo para integrarse a la Plataforma Nacional si algún día un
actor institucional lo retoma (la vía formal existe: convenio de adhesión, Art. 4).

**Explícitamente fuera de alcance** (obligaciones institucionales sin equivalente aquí):
Área Coordinadora de Datos Abiertos (Arts. 12-15), Plan Institucional de Publicación (Arts. 34-37),
usuarios/perfiles de la Plataforma (Arts. 17-24), notificaciones a la Dirección General de
Inteligencia de Datos (Art. 39-IV). No se simula cumplimiento institucional que no corresponde.

**Restricción de diseño importante:** el **Manual Operativo** (Art. 9) -- donde la ATDT definirá
formatos y estructuras exactos -- **aún no se publica** (verificado 2026-08-08). Todo lo que este
plan produce debe ser regenerable desde `data/gold/panel_opa.duckdb` + configuración declarativa,
para poder realinearse al Manual cuando exista sin rehacer nada a mano.

## 2. Mapeo artículo → acción concreta

| Artículo | Requisito | Acción en este repo |
|---|---|---|
| Art. 5-I, III, IV, X | Accesibles, gratuitos, sin registro, libre uso citando fuente | Publicación en GitHub Releases + Hugging Face (ya previsto en ARQUITECTURA §7), sin login para descargar. Cita requerida ya documentada en README (Términos de Libre Uso MX) → se replica en los metadatos de cada distribución |
| Art. 5-II + Art. 3-XV | Integrales, con diccionario de datos | **Fase A**: diccionario de datos por tabla, generado desde `schema.yml` de dbt (fuente única de verdad) |
| Art. 5-V + Arts. 32-33 | Oportunos; periodo de actualización declarado y fundamentado | Declarar cadencia trimestral (sigue el calendario de publicación OPA de la SHCP) en los metadatos, con la advertencia estacional Q4→Q1 como nota técnica |
| Art. 5-VI | Permanentes, con identificadores adecuados | Versionado semántico de los paquetes de datos + DOI de Zenodo (ya en pendientes de la arquitectura) |
| Art. 5-VII | Primarios, máxima desagregación | Ya cumplido por diseño: `fct_ppi_observacion` conserva el grano observación por PPI por corte; `n_registros_agregados` declara la única agregación que existe (sub-filas multi-entidad, ver README) |
| Art. 5-VIII, IX + Art. 38-I/II/IV/V | Legibles por máquina, formatos abiertos, tabulares, estructurados, sin barreras | **Fase B**: exportador `opa publish` → CSV UTF-8 (formato base que piden los Lineamientos) + Parquet y GeoJSON como extras (§4) |
| Art. 3-XXII + Art. 39-III | Metadatos de contexto, captura, procesamiento, calidad | **Fase C**: metadatos por dataset, generados desde `data/manifest.jsonl` (procedencia real: URL, sha256, fecha) + `reports/calidad_silver.md` (calidad real medida) |
| Art. 3-XIV | DCAT para interoperabilidad de catálogos | **Fase C**: un `catalog.json` DCAT con un `dcat:Dataset` por tabla publicada y un `dcat:Distribution` por formato |
| Art. 38-VI | Datos personales anonimizados | **Fase D**: evaluación documentada (esperado: no aplica -- son proyectos de obra pública, no personas físicas -- pero se verifica contra datos reales, no se asume) |
| Art. 39-IV-c | Notas técnicas y aclaraciones acompañando los datos | **Fase D**: nota técnica de limitaciones conocidas (patrón estacional Q4→Q1, 2024-T1 corrupto en la fuente, cobertura parcial 2020 T1/T2, huecos 2016-2018, deflactación pendiente de INPC) |

## 3. Fases de ejecución

### Fase A -- Diccionario de datos (prerequisito de todo lo demás) -- COMPLETA (2026-08-08)

1. ✅ `dbt/models/marts/schema.yml` enriquecido: descripción por **cada columna** de las 8
   tablas publicables (`fct_ppi_observacion`, `fct_ppi_delta`, `fct_ppi_ciclo_vida`, `dim_ppi`,
   `dim_snapshot`, `dim_ramo`, `dim_entidad`, `dim_tipo_ppi`) -- de 10 a ~80 descripciones.
   Cada una dice unidad (pesos corrientes MXN salvo indicación contraria; avance 0-100),
   columna fuente SHCP cuando el nombre cambió, y advertencias reales verificadas contra el
   duckdb (no supuestas): `ejercido > modificado` en 18.5% de filas, `fase` solo poblada en
   2017-2018, montos verificados en magnitud contra Tren Maya (~1.67e11), etc.
2. ✅ `src/opa/diccionario.py` + comando `opa diccionario`: cruza `schema.yml` contra las
   columnas REALES de `data/gold/panel_opa.duckdb` (no solo contra lo declarado) y escribe
   `reports/diccionario/diccionario_datos_{tabla}.csv` (uno por tabla, formato tabular como
   pide el Art. 38 incluso para el diccionario mismo) + `DICCIONARIO.md` consolidado.
3. ✅ Criterio de aceptación cumplido de dos formas: (a) `opa diccionario` **falla ruidoso**
   (código 1, no advertencia) si una columna real no tiene descripción o si `schema.yml`
   documenta una columna que ya no existe -- deriva entre documentación y datos tratada igual
   que cualquier otro error del pipeline; (b) `tests/test_diccionario.py` incluye una guardia
   de CI (`test_schema_real_del_repo_no_tiene_columnas_sin_descripcion`) que corre sin
   necesitar el duckdb (no existe en CI), para atrapar el caso común de agregar una columna a
   `schema.yml` sin documentarla antes de que alguien intente generar el diccionario.

### Fase B -- Exportador de distribuciones (`opa publish`)

1. Nuevo comando CLI `opa publish`: lee `data/gold/panel_opa.duckdb`, escribe
   `data/publish/{version}/` con, por cada tabla publicable:
   - `{tabla}.csv` -- UTF-8, RFC 4180. **Formato base de los Lineamientos** (Art. 38: tabular).
   - `{tabla}.parquet` -- extra (§4).
   - `checksums.sha256` de todo el paquete (permanencia e integridad, Art. 5-VI).
2. GeoJSON (§4) para las tablas georreferenciadas.
3. Idempotente y determinista: mismo duckdb → mismos bytes (mismo criterio de rerun que Bronze).
4. `data/publish/` fuera de git, igual que bronze/silver/gold (ya cubierto por `.gitignore` de datos).

### Fase C -- Metadatos DCAT

1. `conf/dcat.yml`: lo declarativo que no se puede derivar (título, descripción, temas, licencia
   de datos -- Libre Uso MX --, cadencia declarada con su fundamentación, contacto).
2. Generador que combina `conf/dcat.yml` + `data/manifest.jsonl` (procedencia real) +
   `reports/calidad_silver.md` (calidad real) → `catalog.json` (DCAT, JSON-LD) dentro del paquete
   de `opa publish`. Un `dcat:Dataset` por tabla; un `dcat:Distribution` por formato (CSV, Parquet,
   GeoJSON), cada una con su media type, tamaño y checksum.
3. No inventar campos del "perfil mexicano": mientras no exista el Manual Operativo, usar DCAT
   estándar (W3C) + los campos que los propios Lineamientos nombran (Art. 3-XXII). Cuando la ATDT
   publique el Manual, el delta se aplica en `conf/dcat.yml` y el generador, no en los datos.

### Fase D -- Contexto, privacidad y empaquetado final

1. Evaluación de datos personales (Art. 38-VI) contra datos reales: revisar columnas de texto
   libre (`nombre_ppi`, `descripcion_ur`, `localizacion`) buscando nombres de personas físicas.
   Documentar el resultado en la nota técnica, sea cual sea.
2. `NOTA-TECNICA.md` dentro del paquete (Art. 39-IV-c): limitaciones conocidas y verificadas --
   patrón estacional Q4→Q1 (investigación 2026-08-08), 2024-T1 corrupto en la fuente, cobertura
   parcial 2020 T1/T2, huecos 2016/2017-T4/2018 (agotados por 4 vías, pendiente PNT/INAI),
   deflactación NULL hasta tener serie INPC, variantes de texto sin normalizar en
   `estatus_operacion`/`descripcion_tipo_ppi`.
3. Publicación: GitHub Release con el paquete versionado; después Hugging Face y DOI de Zenodo
   (identificador permanente, Art. 5-VI). El README gana una sección "Cómo citar".

## 4. El extra sobre los Lineamientos: Parquet y GeoJSON

Los Lineamientos piden formatos tabulares abiertos (Art. 38); CSV cumple el mínimo. Este repo
publica además:

- **Parquet** por tabla: mismo contenido que el CSV, con tipos preservados (fechas, decimales,
  nulls sin ambigüedad de comillas Excel), compresión columnar y lectura directa desde
  pandas/R/DuckDB sin re-parseo. Es también el formato interno de Silver, así que no introduce
  una conversión nueva -- solo expone lo que ya existe con calidad verificada.
- **GeoJSON** (RFC 7946) para lo georreferenciado: `fct_ppi_observacion` filtrado a coordenadas
  válidas (ya existe la validación de bbox de México en el contrato de Silver; los centinelas
  `(0,0)` ya se tratan como nulos). Un `FeatureCollection` por año de corte (para mantener
  archivos manejables), con las propiedades clave del PPI en cada `Feature`. Esto habilita uso
  directo en QGIS/Leaflet/Kepler sin ETL previo -- la capa que OPA ofrecía como visor pero nunca
  como descarga estructurada.
- Ambos aparecen como `dcat:Distribution` adicionales del mismo `dcat:Dataset` -- así el extra
  queda dentro del estándar, no al margen.

## 5. Orden y dependencias

```
Fase A (diccionario)  ──►  Fase B (opa publish)  ──►  Fase C (DCAT)  ──►  Fase D (empaquetado)
```

A es prerequisito real: sin descripciones en `schema.yml` no hay diccionario que exportar ni
metadatos honestos. B antes que C porque el `catalog.json` referencia archivos con tamaño y
checksum reales. D al final porque la nota técnica y la evaluación de privacidad describen el
paquete ya generado.

## 6. Criterios de aceptación globales

1. `opa publish` produce un paquete completo y determinista desde el duckdb, sin pasos manuales.
2. 0 columnas publicadas sin entrada en el diccionario (test en CI).
3. `catalog.json` valida contra el vocabulario DCAT (validación sintáctica JSON-LD en CI).
4. Cada distribución lista en el catálogo: formato, media type, bytes, sha256, licencia y cita.
5. La advertencia estacional Q4→Q1 y demás limitaciones viajan CON los datos (nota técnica dentro
   del paquete), no solo en el README del repo.
6. Nada del paquete contradice al Manual Operativo el día que se publique sin poder corregirse
   editando solo `conf/dcat.yml` y los generadores (los datos no se rehacen).
