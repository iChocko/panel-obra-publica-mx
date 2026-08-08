-- Un renglón por PPI (arquitectura sección 4.3): primer y último corte, monto inicial vs.
-- final, sobrecosto %, duración observada, estatus terminal inferido.
--
-- estatus_terminal_inferido usa las reglas EXPLÍCITAS de la sección 2.2 (identidad y
-- desaparición), con una tercera categoría que la arquitectura no nombra pero que la lógica
-- exige: un PPI cuyo último corte observado ES el último corte disponible en todo el panel
-- simplemente no ha terminado de observarse todavía -- no es una "salida", es que el panel
-- corta ahí. Tratarlo como salida_no_explicada sería un falso positivo garantizado en cada
-- corrida (el corte más reciente siempre parece "recién desaparecido").
--
-- LIMITACIÓN A DECLARAR (no esconder, arquitectura sección 2.2): "salida_no_explicada"
-- puede significar que el proyecto de verdad dejó de reportarse, O que cayó en uno de los 7
-- trimestres que este panel no pudo recuperar (2016 T1/T2/T4, 2017 T4, 2018 T1/T2/T4, ver
-- README) -- los datos abiertos no permiten distinguir ambos casos limpiamente.
with vida as (
    select
        cve_cartera,
        min(orden_corte) as primer_corte,
        max(orden_corte) as ultimo_corte,
        max(indice_trimestre) - min(indice_trimestre) as trimestres_entre_primera_y_ultima_observacion,
        arg_min(snapshot_id, orden_corte) as snapshot_id_inicio,
        arg_max(snapshot_id, orden_corte) as snapshot_id_fin,
        arg_min(nombre_ppi, orden_corte) as nombre_ppi,
        arg_min(modificado, orden_corte) as monto_inicial,
        arg_max(modificado, orden_corte) as monto_final,
        arg_max(avance_fisico, orden_corte) as avance_fisico_final,
        arg_max(estatus_operacion, orden_corte) as estatus_operacion_final,
        arg_min(anios_he, orden_corte) as anios_he_declarado,
        count(*) as n_observaciones,
        count(distinct anio) as n_anios_observado,
        bool_or(cobertura_parcial_del_universo) as alguna_observacion_con_cobertura_parcial
    from {{ ref('int_ppi_observaciones_canonicas') }}
    group by cve_cartera
),

ultimo_corte_panel as (
    select max(orden_corte) as valor from {{ ref('int_snapshot_canonico') }}
)

select
    v.cve_cartera,
    v.nombre_ppi,
    v.primer_corte,
    v.ultimo_corte,
    v.trimestres_entre_primera_y_ultima_observacion,
    v.snapshot_id_inicio,
    v.snapshot_id_fin,
    v.n_observaciones,
    v.n_anios_observado,
    v.alguna_observacion_con_cobertura_parcial,

    v.monto_inicial,
    v.monto_final,
    case
        when v.monto_inicial > 0 then round((v.monto_final - v.monto_inicial) / v.monto_inicial * 100, 2)
        else null
    end as sobrecosto_pct,

    v.anios_he_declarado as duracion_planeada_anios,
    round(v.trimestres_entre_primera_y_ultima_observacion / 4.0, 2) as duracion_observada_anios,

    v.avance_fisico_final,
    v.estatus_operacion_final,
    case
        when v.avance_fisico_final >= 95 then 'terminado_probable'
        when v.ultimo_corte < p.valor then 'salida_no_explicada'
        else 'vigente_ultimo_corte_disponible'
    end as estatus_terminal_inferido
from vida v
cross join ultimo_corte_panel p
