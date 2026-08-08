-- SCD2 sobre atributos descriptivos que cambian rara vez (arquitectura sección 4.3): un
-- renglón por periodo de vigencia, no por observación. Los montos NO viven aquí -- esos
-- cambian cada trimestre por diseño, esa es la señal, va en fct_ppi_observacion.
--
-- Patrón "gaps and islands": se marca cada observación que trae algún atributo distinto a
-- la observación inmediatamente anterior del mismo PPI, se acumula esa marca para formar
-- grupos de vigencia consecutivos, y se colapsa cada grupo a un solo renglón.
with observaciones as (
    select * from {{ ref('int_ppi_observaciones_canonicas') }}
),

con_cambio as (
    select
        *,
        case
            when
                nombre_ppi is distinct from lag(nombre_ppi) over w
                or id_ramo is distinct from lag(id_ramo) over w
                or descripcion_tipo_ppi is distinct from lag(descripcion_tipo_ppi) over w
                or id_ur is distinct from lag(id_ur) over w
                or localizacion is distinct from lag(localizacion) over w
                or id_entidad_federativa is distinct from lag(id_entidad_federativa) over w
                or latitud is distinct from lag(latitud) over w
                or longitud is distinct from lag(longitud) over w
            then 1
            else 0
        end as es_cambio
    from observaciones
    window w as (partition by cve_cartera order by orden_corte)
),

con_grupo as (
    select
        *,
        sum(es_cambio) over (partition by cve_cartera order by orden_corte rows unbounded preceding) as grupo_vigencia
    from con_cambio
)

select
    cve_cartera,
    grupo_vigencia as version_ppi,
    min(orden_corte) as vigente_desde_corte,
    max(orden_corte) as vigente_hasta_corte,
    arg_min(snapshot_id, orden_corte) as snapshot_id_inicio,
    arg_max(snapshot_id, orden_corte) as snapshot_id_fin,
    arg_min(nombre_ppi, orden_corte) as nombre_ppi,
    arg_min(id_ramo, orden_corte) as id_ramo,
    arg_min(descripcion_ramo, orden_corte) as descripcion_ramo,
    arg_min(descripcion_tipo_ppi, orden_corte) as descripcion_tipo_ppi,
    arg_min(id_ur, orden_corte) as id_ur,
    arg_min(descripcion_ur, orden_corte) as descripcion_ur,
    arg_min(localizacion, orden_corte) as localizacion,
    arg_min(id_entidad_federativa, orden_corte) as id_entidad_federativa,
    arg_min(entidad_federativa, orden_corte) as entidad_federativa,
    arg_min(latitud, orden_corte) as latitud,
    arg_min(longitud, orden_corte) as longitud,
    row_number() over (partition by cve_cartera order by grupo_vigencia desc) = 1 as es_version_vigente
from con_grupo
group by cve_cartera, grupo_vigencia
