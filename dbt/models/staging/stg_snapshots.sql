-- Metadatos de procedencia por snapshot, desde data/manifest.jsonl -- no desde el parquet
-- de Silver (que solo tiene los datos, no de dónde salieron ni cuándo se descargaron).
--
-- El manifiesto puede tener más de un renglón con el mismo snapshot_id (el mismo contenido
-- descubierto por más de una fuente, ej. vivo y Wayback a la vez -- caso real:
-- Proyectos_OPA.csv de 2015, ver src/opa/normalize.py). Se prioriza "vivo" sobre "wayback"
-- sobre "espejo" para quedarse con un solo renglón por snapshot_id, igual que hace la
-- matriz de cobertura de Fase 0/1 (ver src/opa/discovery.py LEGEND_PRIORIDAD).
with manifiesto as (
    select
        snapshot_id,
        url,
        origen,
        fecha_descarga,
        try_cast(corte_declarado.anio as integer) as anio,
        try_cast(corte_declarado.trimestre as integer) as trimestre,
        header_hash,
        sha256,
        bytes,
        case origen when 'vivo' then 1 when 'espejo' then 2 when 'wayback' then 3 else 4 end as prioridad_fuente,
        -- Un mismo (anio, trimestre) puede tener 3 archivos DISTINTOS y complementarios --
        -- no duplicados -- desde que el portal se renombró en 2022 (ver Fase 1):
        -- Consolidado (universo completo, vigentes+concluidos+suspendidos), Seguimiento
        -- (solo vigentes ese trimestre) y Concluido(s) (solo lo que terminó ese trimestre).
        -- "producto" identifica cuál es cuál a partir del nombre real del archivo en la URL.
        case
            when url ilike '%Consolidado%' then 'consolidado'
            when url ilike '%Seguimiento%' then 'seguimiento'
            when url ilike '%Concluido%' then 'concluido'
            when trimestre is null then 'anual_generico'
            else 'otro'
        end as producto
    from read_json_auto('{{ var("ruta_manifest") }}')
    where corte_declarado.anio is not null
),

deduplicado as (
    select *, row_number() over (partition by snapshot_id order by prioridad_fuente) as rn
    from manifiesto
)

select snapshot_id, url, origen, fecha_descarga, anio, trimestre, producto, header_hash, sha256, bytes
from deduplicado
where rn = 1
