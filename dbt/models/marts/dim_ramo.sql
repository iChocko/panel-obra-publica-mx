-- Catálogo congelado (arquitectura sección 4.3). Base: catalogos.xlsx, el catálogo oficial
-- que la propia SHCP publica junto a OPA (25 ramos vigentes, archivado como auxiliar en
-- Fase 1). Ampliado (Gold, 2026-08-08) con 11 ramos que aparecen en el panel 2015-2018 pero
-- ya no existen en el catálogo vigente (reorganizaciones de gobierno, ej. id_ramo=13
-- "Marina", 17 "Procuraduría General de la República") -- la descripción de esos 11 sale
-- del propio panel (columna DESCRIPCION_RAMO de la fuente), no se inventó. en_catalogo_oficial
-- distingue cuáles vienen del catálogo SHCP vigente y cuáles se completaron así.
select id_ramo, descripcion_ramo, en_catalogo_oficial
from {{ ref('dim_ramo_seed') }}
