-- Observaciones deduplicadas (ver int_ppi_observaciones_dedup.sql) limitadas a un snapshot
-- canónico por trimestre real (ver int_snapshot_canonico.sql) -- la base para todo lo que
-- necesita orden cronológico: dim_ppi (SCD2), fct_ppi_delta, fct_ppi_ciclo_vida.
select
    o.cve_cartera,
    o.snapshot_id,
    c.anio,
    c.trimestre,
    c.orden_corte,
    c.indice_trimestre,
    c.producto,
    c.cobertura_parcial_del_universo,
    o.n_registros_agregados,
    o.nombre_ppi,
    o.id_ramo,
    o.descripcion_ramo,
    o.descripcion_tipo_ppi,
    o.id_ur,
    o.descripcion_ur,
    o.localizacion,
    o.id_entidad_federativa,
    o.entidad_federativa,
    o.latitud,
    o.longitud,
    o.anios_he,
    o.aprobado,
    o.modificado,
    o.ejercido,
    o.monto_total_inversion,
    o.avance_fisico,
    o.estatus_operacion,
    o.fase
from {{ ref('int_ppi_observaciones_dedup') }} o
inner join {{ ref('int_snapshot_canonico') }} c using (snapshot_id)
