-- Catálogo congelado (arquitectura sección 4.3). Base: catalogos.xlsx, 32 entidades
-- federativas oficiales. Ampliado (Gold, 2026-08-08) con 3 códigos especiales que sí
-- aparecen en el panel para programas de cobertura no-estatal (33 "en el extranjero", 34
-- "no distribuible geográficamente", 35 "nacional") -- la descripción sale del propio panel
-- (columna ENTIDAD_FEDERATIVA de la fuente), no se inventó. en_catalogo_oficial distingue
-- las 32 entidades reales de estos 3 códigos especiales.
select id_entidad_federativa, entidad_federativa, en_catalogo_oficial
from {{ ref('dim_entidad_seed') }}
