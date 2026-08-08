-- Tabla central del panel (arquitectura sección 4.3). Grano: (cve_cartera, snapshot_id) --
-- un renglón por PPI observado en un corte. Todo lo demás del modelo se deriva de esta tabla.
--
-- Fuente: int_ppi_observaciones_dedup, no stg_opa_snapshot directo -- (cve_cartera,
-- snapshot_id) no es único en los datos crudos (~1,124 pares tienen entre 2 y 33 filas,
-- ver la nota completa en int_ppi_observaciones_dedup.sql). n_registros_agregados > 1
-- marca cuáles PPI de este corte son en realidad la suma de varias sub-asignaciones.
with observaciones as (
    select
        o.cve_cartera,
        o.snapshot_id,
        o.anio as anio_corte,
        o.trimestre as trimestre_corte,
        o.n_registros_agregados,

        -- montos nominales, tal como se publicaron (sumados si n_registros_agregados > 1)
        o.aprobado,
        o.modificado,
        o.ejercido,
        o.monto_total_inversion,
        o.monto_operacion_mantenimiento,
        o.costo_total_inversion,
        o.ppef,
        o.pef,

        -- seguimiento
        o.avance_fisico,
        o.estatus_operacion,
        o.fase,

        -- clasificación y ubicación del corte (ver dim_ppi para el historial completo de
        -- cambios de estos mismos atributos a través de los cortes -- aquí solo el valor
        -- vigente en ESTE corte, y solo representativo si n_registros_agregados > 1)
        o.id_ramo,
        o.descripcion_ramo,
        o.descripcion_tipo_ppi,
        o.id_entidad_federativa,
        o.entidad_federativa,
        o.latitud,
        o.longitud
    from {{ ref('int_ppi_observaciones_dedup') }} o
)

select
    obs.*,
    -- Montos reales (pesos constantes del año base declarado en conf/deflactor_inpc.csv).
    -- Fórmula: nominal * (100 / inpc_del_periodo) -- asume convención estándar de INPC con
    -- base = 100 en el periodo base. NULL hasta que el CSV se llene con la serie oficial de
    -- Banxico SIE -- ver la nota completa en stg_deflactor_inpc.sql. No se aproxima con un
    -- supuesto de inflación genérico: sin la serie real, es mejor NULL explícito que un
    -- número que parece preciso y no lo es.
    obs.modificado * (100.0 / defl.inpc) as modificado_real,
    obs.ejercido * (100.0 / defl.inpc) as ejercido_real,
    obs.monto_total_inversion * (100.0 / defl.inpc) as monto_total_inversion_real,
    defl.anio_base as anio_base_deflactor
from observaciones obs
left join {{ ref('stg_deflactor_inpc') }} defl
    on defl.anio = obs.anio_corte
    and (defl.trimestre = obs.trimestre_corte or (defl.trimestre is null and obs.trimestre_corte is null))
