-- Un snapshot_id canónico por (anio, trimestre) real -- lo que necesitan los modelos que
-- comparan "el corte inmediato anterior" (dim_ppi SCD2, fct_ppi_delta,
-- fct_ppi_ciclo_vida). Sin esto, un PPI que aparece en Consolidado Y Seguimiento del mismo
-- trimestre generaría dos "observaciones" al mismo tiempo y rompería cualquier comparación
-- cronológica.
--
-- Se excluyen a propósito los snapshots "anual_generico" (vintage ambiguo -- mismo criterio
-- que la matriz de cobertura de Fase 0/1: "no se asigna a ningún trimestre específico").
-- Cuando hay más de un producto para el mismo trimestre se prefiere Consolidado (universo
-- completo: vigentes + concluidos + suspendidos) sobre Seguimiento (solo vigentes) sobre
-- Concluido (solo lo que terminó ese trimestre) -- ver stg_snapshots.sql.
select
    snapshot_id,
    anio,
    trimestre,
    producto,
    -- Para ordenar y para mostrar (legible: 2022 T1 -> 20221) -- NO para restar y sacar una
    -- brecha en trimestres, un salto de año rompe la aritmética (2020 T4 -> 2021 T1 da
    -- 20211-20204 = 7, no 1). Para eso existe indice_trimestre abajo.
    anio * 10 + trimestre as orden_corte,
    -- Lineal a propósito (anio*4+trimestre): 2020 T4 -> 2021 T1 da 8084 -> 8085, brecha
    -- correcta de 1. Lo usa fct_ppi_delta para calcular cuántos trimestres reales pasaron
    -- desde la observación anterior de un PPI.
    anio * 4 + trimestre as indice_trimestre,
    -- OJO real (2026-08-08): 2020 T1 y T2 solo tienen "Concluido" disponible -- ni
    -- Consolidado ni Seguimiento se descubrieron para esos dos trimestres específicos (ver
    -- reports/discovery.jsonl). Eso significa que el universo de PPI de esos dos cortes NO
    -- es comparable al resto: son solo los proyectos que terminaron ESE trimestre, no el
    -- universo completo vigente. Cualquier salto raro en fct_ppi_delta/dim_ppi alrededor de
    -- 2020 T1-T2 hay que revisarlo con esto en mente antes de asumir que es un hallazgo real.
    producto != 'consolidado' and producto != 'anual_generico' as cobertura_parcial_del_universo
from (
    select
        snapshot_id,
        anio,
        trimestre,
        producto,
        row_number() over (
            partition by anio, trimestre
            order by case producto
                when 'consolidado' then 1
                when 'seguimiento' then 2
                when 'concluido' then 3
                else 4
            end
        ) as rn
    from {{ ref('stg_snapshots') }}
    where trimestre is not null
)
where rn = 1
