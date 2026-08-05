# Matriz de cobertura — Obra Pública Abierta (OPA)

*Generado por `opa discover` el 2026-08-05T05:50:04.176131+00:00.*

## Leyenda

- 🟢 **vivo** — responde en el servidor actual de la SHCP
- 🔵 **espejo** — declarado en un mirror (datos.gob.mx / datamx.io)
- 🟡 **wayback** — únicamente recuperable vía Internet Archive
- ⚪ **hueco** — no se encontró en ninguna fuente

## Matriz año × trimestre (patrones con trimestre explícito en el nombre)

| Año | Q1 | Q2 | Q3 | Q4 |
|---|---|---|---|---|
| 2015 | ⚪ hueco | ⚪ hueco | ⚪ hueco | ⚪ hueco |
| 2016 | ⚪ hueco | ⚪ hueco | ⚪ hueco | ⚪ hueco |
| 2017 | 🟢 vivo | 🟢 vivo | 🟢 vivo | ⚪ hueco |
| 2018 | ⚪ hueco | ⚪ hueco | 🟢 vivo | ⚪ hueco |
| 2019 | ⚪ hueco | ⚪ hueco | ⚪ hueco | ⚪ hueco |
| 2020 | ⚪ hueco | ⚪ hueco | ⚪ hueco | ⚪ hueco |
| 2021 | ⚪ hueco | ⚪ hueco | ⚪ hueco | ⚪ hueco |
| 2022 | ⚪ hueco | ⚪ hueco | ⚪ hueco | ⚪ hueco |
| 2023 | ⚪ hueco | ⚪ hueco | ⚪ hueco | ⚪ hueco |
| 2024 | ⚪ hueco | ⚪ hueco | ⚪ hueco | ⚪ hueco |
| 2025 | ⚪ hueco | ⚪ hueco | ⚪ hueco | ⚪ hueco |
| 2026 | ⚪ hueco | ⚪ hueco | ⚪ hueco | ⚪ hueco |

## Cobertura anual (patrón genérico `proyectos_opa.csv` / `.xlsx`)

> Nota metodológica: el archivo genérico no declara trimestre en el nombre; representa "el corte vigente al momento de la consulta", que es ambiguo una vez sobreescrito por publicaciones posteriores. Por rigor, **no se asigna a ningún trimestre específico** en la matriz anterior -- se reporta aparte como respaldo.

| Año | Cobertura |
|---|---|
| 2015 | 🟢 vivo |
| 2016 | 🟢 vivo |
| 2017 | 🟢 vivo |
| 2018 | 🟢 vivo |
| 2019 | 🟢 vivo |
| 2020 | 🟢 vivo |
| 2021 | 🟢 vivo |
| 2022 | ⚪ hueco |
| 2023 | ⚪ hueco |
| 2024 | ⚪ hueco |
| 2025 | ⚪ hueco |
| 2026 | ⚪ hueco |

> ⚠️ **2022–2026 salen todos como hueco** en el patrón genérico conocido, con 404 limpios (no error de red -- ver detalle crudo). Dos hipótesis quedan abiertas y **sin investigar en esta fase**: (a) la SHCP descontinuó OPA en ese punto, o (b) cambió a un patrón de URL no incluido en `sources.yml`. No se concluye descontinuación sin antes buscar un patrón nuevo -- eso es trabajo de Fase 1.

## Puerta de decisión (2016–2024, 36 trimestres)

- Trimestres recuperables: **4 / 36 (11.1%)**
- Recomendación: **Pivotar a panel anual (Tomo VIII del PEF + OPA anual) y usar SRFT para la capa subnacional georreferenciada.**

## Wayback — detalle de la pregunta clave

- `transparenciapresupuestaria.gob.mx/work/models/PTP/DatosAbiertos/OPA`: 45 capturas únicas (respuesta válida, `collapse=digest`)
- `transparenciapresupuestaria.gob.mx/work/models/PTP/OPA`: 45 capturas únicas (respuesta válida, `collapse=digest`)

- Total de capturas de **archivos de datos** (no HTML): **90**
- Rango de fechas: 20160417180503 – 20240921105347
- Mimetypes encontrados: application/javascript, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, image/png, text/csv
- De esas, **2** declaran trimestre explícito en el nombre (las únicas que cuentan para la puerta de decisión).

## Fuente 2 — Espejos: resultado

- `API+CURL` `https://www.datos.gob.mx/api/3/action/package_show?id=56b98e14-41ba-4edd-b8a8-c96d5008b071`: ❌ no encontrado -- dataset no encontrado con este id
- `API+CURL` `https://www.datos.gob.mx/api/3/action/package_search?q=Obra Pública Abierta`: ❌ no encontrado -- 21 resultados por palabra suelta, ninguno es realmente OPA
- `API` `https://datamx.io`: ❌ no encontrado

