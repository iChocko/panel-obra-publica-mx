-- Lee todos los parquet de Silver (un archivo por snapshot, ver src/opa/normalize.py) y
-- los une por nombre de columna: distintos esquemas históricos (2015-2018) tienen distintos
-- subconjuntos de columnas canónicas -- ver conf/schema_map.yml. union_by_name rellena con
-- NULL las columnas que un esquema dado no tenía, en vez de fallar por columnas dispares.
select *
from read_parquet('{{ var("ruta_silver_glob") }}', union_by_name = true)
