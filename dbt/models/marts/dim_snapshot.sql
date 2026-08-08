-- Metadatos del corte + conteo de PPI + bandera de calidad (arquitectura sección 4.3).
--
-- "estado" distingue snapshots que sí llegaron a Silver de los que el manifiesto conoce
-- pero se excluyeron (corruptos en la fuente o esquema todavía no mapeado, ver
-- conf/schema_map.yml) -- se listan de todas formas, con conteos en cero, para que la
-- exclusión sea visible en vez de que el snapshot simplemente desaparezca sin explicación.
with conteos as (
    select
        snapshot_id,
        count(*) as n_observaciones,
        count(distinct cve_cartera) as n_ppi
    from {{ ref('stg_opa_snapshot') }}
    group by snapshot_id
)

select
    s.snapshot_id,
    s.anio,
    s.trimestre,
    s.origen,
    s.fecha_descarga,
    s.url,
    s.sha256,
    s.bytes,
    coalesce(c.n_observaciones, 0) as n_observaciones,
    coalesce(c.n_ppi, 0) as n_ppi,
    case when c.snapshot_id is null then 'excluido_de_silver' else 'normalizado' end as estado
from {{ ref('stg_snapshots') }} s
left join conteos c using (snapshot_id)
