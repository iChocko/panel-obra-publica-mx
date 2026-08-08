-- Catálogo oficial congelado (arquitectura sección 4.3) -- de catalogos.xlsx, real, 11
-- tipos de programa/proyecto de inversión.
select id_tipo_ppi, descripcion_tipo_ppi
from {{ ref('dim_tipo_ppi_seed') }}
