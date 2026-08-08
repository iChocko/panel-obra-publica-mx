-- Arquitectura sección 6.2: "la suma de montos por ramo y corte debe ser estable ±X%
-- contra el corte previo (detecta cargas truncadas)".
--
-- Se implementó sobre CONTEO de PPI por ramo, no sobre la suma de montos -- se probó ambas
-- formas contra datos reales (2026-08-08) y los montos nominales tienen demasiado ruido
-- real (mediana 0%, pero swings de cientos o miles de % son normales entre trimestres por
-- altas/bajas de proyectos grandes) para ser una señal útil de "carga truncada". El conteo
-- de PPI es más estable en condiciones normales y es justo la señal que detecta una carga
-- accidentalmente incompleta (un ramo que de golpe reporta 5% de sus proyectos usuales).
--
-- Se excluyen a propósito las comparaciones que cruzan un corte con cobertura_parcial_del_
-- universo=true (ver int_snapshot_canonico.sql -- ej. 2020 T1/T2, que solo tienen
-- "Concluido" disponible, no el universo completo) en cualquiera de los dos lados: comparar
-- el conteo de "solo concluidos" contra "universo completo" del trimestre vecino es
-- comparar cosas distintas por diseño de la fuente, no una carga truncada.
--
-- severity=warn (no error): con datos reales, hasta con este filtro quedan caídas grandes
-- que parecen legítimas (fin de ciclo de programas de gran volumen) -- bloquear el build
-- completo por esto sería más ruido que señal. Sirve para que aparezca en el reporte, no
-- para tumbar el build.
--
-- ACTUALIZACIÓN 2026-08-08: investigación multi-agente (5 casos que esta prueba marcó,
-- cada uno con una segunda revisión adversarial independiente contra los datos reales)
-- confirmó que la transición de Q4 a Q1 de cada año es un patrón ESTACIONAL ESTRUCTURAL de
-- la fuente SHCP, no una carga incompleta: el universo TOTAL del padrón (todos los ramos
-- juntos) cae de forma sistemática entre 15% y 29% cada enero-marzo, verificado con datos
-- reales de 2022, 2023, 2025 y 2026 -- probablemente porque los proyectos plurianuales
-- vigentes se re-registran/reautorizan presupuestalmente antes de volver a aparecer en el
-- reporte. De los 5 casos marcados, ninguno era un archivo truncado sin explicación: 2
-- fueron ese mismo patrón estacional (con parte del hueco reapareciendo intacto 1-2
-- trimestres después), 1 fue una reorganización administrativa real (Entidades no
-- Sectorizadas perdió proyectos porque IMSS-BIENESTAR obtuvo su propio ramo presupuestal
-- en 2026 T1) y 1 fue probable depuración real de estudios de preinversión estancados en
-- 0% de avance (Turismo, 2025 T1) -- ver README, sección "Gold", para el detalle de cada
-- caso. Por eso esta prueba EXCLUYE a propósito las transiciones Q4->Q1: son la fuente casi
-- exclusiva de falsos positivos aquí y ya están explicadas por el ciclo fiscal. Sigue activa
-- para cualquier otra transición de trimestre, donde una caída de 70%+ sí sería inusual.
{{ config(severity = 'warn') }}

with por_ramo_corte as (
    select
        c.id_ramo,
        c.snapshot_id,
        c.orden_corte,
        c.trimestre,
        c.cobertura_parcial_del_universo,
        count(distinct c.cve_cartera) as n_ppi
    from {{ ref('int_ppi_observaciones_canonicas') }} c
    where c.id_ramo is not null
    group by 1, 2, 3, 4, 5
),

con_anterior as (
    select
        *,
        lag(n_ppi) over w as n_ppi_anterior,
        lag(trimestre) over w as trimestre_anterior,
        lag(cobertura_parcial_del_universo) over w as cobertura_parcial_anterior
    from por_ramo_corte
    window w as (partition by id_ramo order by orden_corte)
)

select
    id_ramo,
    snapshot_id,
    orden_corte,
    n_ppi_anterior,
    n_ppi,
    round((n_ppi - n_ppi_anterior) / n_ppi_anterior::double * 100, 1) as pct_cambio
from con_anterior
where n_ppi_anterior is not null
  and n_ppi_anterior >= 5  -- ramos muy chicos son ruidosos por diseño, no por carga truncada
  and not cobertura_parcial_del_universo
  and not cobertura_parcial_anterior
  and not (trimestre = 1 and trimestre_anterior = 4)  -- patrón estacional Q4->Q1, ver nota arriba
  and (n_ppi - n_ppi_anterior) / n_ppi_anterior::double <= -0.70
