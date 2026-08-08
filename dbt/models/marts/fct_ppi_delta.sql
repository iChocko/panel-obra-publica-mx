-- Cambio contra el corte canónico inmediato anterior del mismo PPI (arquitectura sección
-- 4.3): Δmonto nominal, Δavance, cambio de estatus, bandera de re-nombramiento. Grano:
-- (cve_cartera, snapshot_id), igual que fct_ppi_observacion -- pero solo donde existe un
-- corte anterior real que comparar (el primer corte de un PPI no tiene delta).
--
-- "Anterior" es el corte anterior que SÍ observamos, no necesariamente el trimestre
-- calendario inmediato -- el panel tiene huecos reales (2016 T1/T2/T4, 2017 T4, 2018
-- T1/T2/T4, ver README). brecha_trimestres dice cuántos trimestres de calendario pasaron
-- entre una observación y la siguiente; brecha_trimestres > 1 significa que el delta cruza
-- un hueco, no un cambio trimestral limpio -- no tratarlo igual que un delta de 1 trimestre
-- al interpretar sobrecostos o avances.
with con_anterior as (
    select
        *,
        lag(snapshot_id) over w as snapshot_id_anterior,
        lag(indice_trimestre) over w as indice_trimestre_anterior,
        lag(modificado) over w as modificado_anterior,
        lag(ejercido) over w as ejercido_anterior,
        lag(monto_total_inversion) over w as monto_total_inversion_anterior,
        lag(avance_fisico) over w as avance_fisico_anterior,
        lag(estatus_operacion) over w as estatus_operacion_anterior,
        lag(nombre_ppi) over w as nombre_ppi_anterior
    from {{ ref('int_ppi_observaciones_canonicas') }}
    window w as (partition by cve_cartera order by orden_corte)
)

select
    cve_cartera,
    snapshot_id,
    snapshot_id_anterior,
    anio,
    trimestre,
    orden_corte,
    indice_trimestre - indice_trimestre_anterior as brecha_trimestres,
    cobertura_parcial_del_universo,

    modificado_anterior,
    modificado,
    modificado - modificado_anterior as delta_modificado,

    ejercido_anterior,
    ejercido,
    ejercido - ejercido_anterior as delta_ejercido,

    monto_total_inversion_anterior,
    monto_total_inversion,
    monto_total_inversion - monto_total_inversion_anterior as delta_monto_total_inversion,

    avance_fisico_anterior,
    avance_fisico,
    avance_fisico - avance_fisico_anterior as delta_avance_fisico,
    -- Bandera literal de la arquitectura (sección 6.2, test singular): "ningún PPI puede
    -- tener avance físico decreciente entre cortes sin bandera" -- aquí está la bandera.
    avance_fisico < avance_fisico_anterior as avance_fisico_decrecio,

    estatus_operacion_anterior,
    estatus_operacion,
    estatus_operacion is distinct from estatus_operacion_anterior as cambio_estatus,

    nombre_ppi_anterior is not null and nombre_ppi is distinct from nombre_ppi_anterior as bandera_renombramiento
from con_anterior
where indice_trimestre_anterior is not null
