-- Serie de deflactores INPC (arquitectura sección 2.3: "INPC de Banxico SIE, con la serie
-- de deflactores versionada dentro del repo para garantizar reproducibilidad exacta").
--
-- PENDIENTE DE POBLAR (2026-08-08): conf/deflactor_inpc.csv solo tiene el encabezado, sin
-- filas. La API de Banxico SIE exige un token de acceso (autoservicio, gratuito, pero
-- registrarlo requiere una acción humana con datos de contacto reales que no corresponde
-- generar en automático) y no se encontró un endpoint público sin token con la serie
-- completa desde 2015. En vez de inventar valores de INPC (que romperían la trazabilidad
-- exacta que pide la arquitectura) se dejó el esquema listo y vacío -- fct_ppi_observacion
-- ya tiene las columnas de montos reales, simplemente salen NULL hasta que alguien con
-- acceso a un token de Banxico SIE llene este CSV con la serie oficial (columnas:
-- anio, trimestre, inpc, anio_base).
select *
from read_csv(
    '{{ var("ruta_deflactor_inpc") }}',
    header = true,
    columns = {'anio': 'INTEGER', 'trimestre': 'INTEGER', 'inpc': 'DOUBLE', 'anio_base': 'INTEGER'}
)
