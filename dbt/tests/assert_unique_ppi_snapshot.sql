-- Arquitectura sección 6.2: "unique en (cve_cartera, snapshot_id)". Un test dbt genérico
-- `unique` no cubre combinaciones de columnas sin el paquete dbt_utils (no instalado a
-- propósito -- ver README, "sin dependencias que no hagan falta"), así que es un singular.
-- Debe devolver 0 filas -- si int_ppi_observaciones_dedup hace su trabajo, nunca debería
-- haber más de una fila por PPI por snapshot en fct_ppi_observacion.
select cve_cartera, snapshot_id, count(*) as n
from {{ ref('fct_ppi_observacion') }}
group by cve_cartera, snapshot_id
having count(*) > 1
