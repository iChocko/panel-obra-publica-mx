-- Arquitectura sección 6.2: "ningún PPI puede tener avance físico decreciente entre cortes
-- sin bandera". fct_ppi_delta ya calcula avance_fisico_decrecio directo de la comparación
-- (no es un cálculo aparte que se pueda desincronizar), así que este test es más una
-- verificación de integridad del propio modelo que un descubrimiento -- pero es exactamente
-- lo que pide la arquitectura, y una regresión futura en la lógica de fct_ppi_delta sí lo
-- haría fallar de verdad.
select cve_cartera, snapshot_id, avance_fisico, avance_fisico_anterior, avance_fisico_decrecio
from {{ ref('fct_ppi_delta') }}
where avance_fisico < avance_fisico_anterior
  and not avance_fisico_decrecio
