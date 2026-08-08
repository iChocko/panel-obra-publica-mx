-- Hallazgo real (2026-08-08): (cve_cartera, snapshot_id) NO es una llave única dentro de
-- Silver -- 99.35% de los pares sí tienen una sola fila, pero ~1,124 pares tienen entre 2 y
-- 33 filas para el MISMO PPI en el MISMO corte. Esto rompe el supuesto de grano de la
-- arquitectura (sección 2.1: "(cve_cartera, snapshot_id)" como llave de la observación) tal
-- cual viene de la fuente -- hay que agregar antes de que cualquier modelo aguas abajo
-- asuma una fila por PPI por corte.
--
-- Evidencia de qué son estas filas "duplicadas" (dos casos reales inspeccionados,
-- 21092110011 en 2024 T2 y 23092100003 en 2024 T3): los montos (MODIFICADO, EJERCIDO) NO
-- son iguales entre filas del mismo grupo -- son valores genuinamente distintos que suman a
-- un total coherente (ej. 6,253,261,959 repartido en sub-montos de 4,525M / 11M / 71M / ...).
-- avance_fisico, en cambio, SÍ se repite igual en todas las filas del grupo. Esto es
-- consistente con un "Programa" de cobertura nacional/multi-entidad exportado como una fila
-- por sub-asignación (posiblemente por entidad federativa o componente), con un solo
-- cve_cartera padre -- no con un error de captura ni con filas realmente repetidas.
--
-- Por eso: los montos se SUMAN (recupera el total real del programa), avance_fisico se
-- toma como MAX (es un porcentaje, no una cantidad -- sumarlo estaría mal), y los atributos
-- descriptivos (nombre, ubicación, ramo...) se toman de la sub-fila con el monto MODIFICADO
-- más grande, como representante -- para un programa multi-entidad esto pierde precisión
-- geográfica real (una sola entidad_federativa no puede describir un programa nacional), lo
-- cual se declara aquí, no se esconde: n_registros_agregados > 1 marca exactamente cuáles.
with base as (
    select
        o.*,
        s.anio,
        s.trimestre,
        s.producto
    from {{ ref('stg_opa_snapshot') }} o
    inner join {{ ref('stg_snapshots') }} s using (snapshot_id)
    where o.cve_cartera is not null
),

representante as (
    -- La sub-fila con el MODIFICADO más grande de cada grupo -- de ahí salen los atributos
    -- descriptivos cuando hay más de una fila por (cve_cartera, snapshot_id).
    select *, row_number() over (partition by cve_cartera, snapshot_id order by modificado desc nulls last) as rn
    from base
)

select
    cve_cartera,
    snapshot_id,
    any_value(anio) as anio,
    any_value(trimestre) as trimestre,
    any_value(producto) as producto,
    count(*) as n_registros_agregados,

    sum(aprobado) as aprobado,
    sum(modificado) as modificado,
    sum(ejercido) as ejercido,
    sum(monto_total_inversion) as monto_total_inversion,
    sum(monto_operacion_mantenimiento) as monto_operacion_mantenimiento,
    sum(costo_total_inversion) as costo_total_inversion,
    sum(ppef) as ppef,
    sum(pef) as pef,

    max(avance_fisico) as avance_fisico,

    max(r.nombre_ppi) filter (where r.rn = 1) as nombre_ppi,
    max(r.id_ramo) filter (where r.rn = 1) as id_ramo,
    max(r.descripcion_ramo) filter (where r.rn = 1) as descripcion_ramo,
    max(r.descripcion_tipo_ppi) filter (where r.rn = 1) as descripcion_tipo_ppi,
    max(r.id_ur) filter (where r.rn = 1) as id_ur,
    max(r.descripcion_ur) filter (where r.rn = 1) as descripcion_ur,
    max(r.localizacion) filter (where r.rn = 1) as localizacion,
    max(r.id_entidad_federativa) filter (where r.rn = 1) as id_entidad_federativa,
    max(r.entidad_federativa) filter (where r.rn = 1) as entidad_federativa,
    max(r.latitud) filter (where r.rn = 1) as latitud,
    max(r.longitud) filter (where r.rn = 1) as longitud,
    max(r.anios_he) filter (where r.rn = 1) as anios_he,
    max(r.estatus_operacion) filter (where r.rn = 1) as estatus_operacion,
    max(r.fase) filter (where r.rn = 1) as fase
from representante r
group by cve_cartera, snapshot_id
