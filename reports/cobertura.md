# Matriz de cobertura — Obra Pública Abierta (OPA)

*Generado por `opa discover` el 2026-08-08T17:49:18.375274+00:00.*

## Leyenda

- 🟢 **vivo** — responde en el servidor actual de la SHCP
- 🔵 **espejo** — declarado en un mirror (datos.gob.mx / datamx.io)
- 🟡 **wayback** — únicamente recuperable vía Internet Archive
- ⚪ **hueco** — no se encontró en ninguna fuente

## Matriz año × trimestre (patrones con trimestre explícito en el nombre)

| Año | Q1 | Q2 | Q3 | Q4 |
|---|---|---|---|---|
| 2015 | ⚪ hueco | ⚪ hueco | ⚪ hueco | ⚪ hueco |
| 2016 | ⚪ hueco | ⚪ hueco | 🟢 vivo | ⚪ hueco |
| 2017 | 🟢 vivo | 🟢 vivo | 🟢 vivo | ⚪ hueco |
| 2018 | ⚪ hueco | ⚪ hueco | 🟢 vivo | ⚪ hueco |
| 2019 | 🟢 vivo | 🟢 vivo | 🟢 vivo | 🟢 vivo |
| 2020 | 🟢 vivo | 🟢 vivo | 🟢 vivo | 🟢 vivo |
| 2021 | 🟢 vivo | 🟢 vivo | 🟢 vivo | 🟢 vivo |
| 2022 | 🟢 vivo | 🟢 vivo | 🟢 vivo | 🟢 vivo |
| 2023 | 🟢 vivo | 🟢 vivo | 🟢 vivo | 🟢 vivo |
| 2024 | 🟢 vivo | 🟢 vivo | 🟢 vivo | 🟢 vivo |
| 2025 | 🟢 vivo | 🟢 vivo | 🟢 vivo | 🟢 vivo |
| 2026 | 🟢 vivo | ⚪ hueco | ⚪ hueco | ⚪ hueco |

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

> ℹ️ **2022–2026 salen como hueco en este patrón genérico específico** (sin trimestre en el nombre), con 404 limpios -- pero **no es un hueco de datos real**: la matriz trimestral de arriba sí tiene cobertura para estos años bajo otro nombre de archivo (investigado en Fase 1, ver README). El portal retiró este nombre genérico a favor de archivos con trimestre explícito en el nombre.

## Puerta de decisión (2016–2024, 36 trimestres)

- Trimestres recuperables: **29 / 36 (80.6%)**
- Recomendación: **Panel trimestral completo, alcance original.**

## Wayback — detalle de la pregunta clave

- `transparenciapresupuestaria.gob.mx/work/models/PTP/DatosAbiertos/OPA`: 45 capturas únicas (respuesta válida, `collapse=digest`)
- `transparenciapresupuestaria.gob.mx/work/models/PTP/OPA`: 45 capturas únicas (respuesta válida, `collapse=digest`)

- Total de capturas de **archivos de datos** (no HTML): **90**
- Rango de fechas: 20160417180503 – 20240921105347
- Mimetypes encontrados: application/javascript, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, image/png, text/csv
- De esas, **15** declaran trimestre explícito en el nombre (las únicas que cuentan para la puerta de decisión).

## Fuente 2 — Espejos: resultado

- `API+CURL` `https://www.datos.gob.mx/api/3/action/package_show?id=56b98e14-41ba-4edd-b8a8-c96d5008b071`: ❌ no encontrado -- dataset no encontrado con este id
- `API+CURL` `https://www.datos.gob.mx/api/3/action/package_search?q=Obra Pública Abierta`: ❌ no encontrado -- 22 resultados por palabra suelta, ninguno es realmente OPA
- `API` `https://datamx.io`: ❌ no encontrado

