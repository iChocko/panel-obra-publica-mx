"""Generador de NOTA-TECNICA.md para el paquete publicado (Fase D del plan ATDT).

Documenta las limitaciones conocidas del dataset conforme al Art. 39-IV-c de los
Lineamientos ATDT ("Añadir y/o adjuntar... información contextual en otros formatos como
notas técnicas, aclaraciones..."). Reutiliza resumen_procedencia() y resumen_calidad() de
opa.dcat_procedencia para los números reales -- ver docs/PLAN-alineacion-gold-lineamientos-ATDT.md
sección "Fase D".
"""

from __future__ import annotations

from pathlib import Path

from opa.dcat_procedencia import resumen_calidad, resumen_procedencia

VEREDICTO_PRIVACIDAD = (
    "Se evaluaron las 3 columnas de texto libre de dim_ppi (nombre_ppi: 11,119 valores "
    "distintos; descripcion_ur: 506; localizacion: 5,166) buscando datos personales de "
    "personas físicas identificables, conforme al Art. 38-VI de los Lineamientos ATDT. "
    "Metodología: 2 investigaciones independientes con enfoques distintos (barrido "
    "heurístico por patrón de nombre + honoríficos, y muestreo aleatorio con vocabulario de "
    "exclusión institucional sobre ~1,750 valores atípicos) más una verificación adversarial "
    "independiente que buscó específicamente huecos no cubiertos por las dos primeras "
    "(apellidos sueltos de una palabra, vocabulario de sucesión/propiedad personal, patrones "
    'tipo RFC/CURP, formato "C. Nombre Apellido"). Total: más de 1,300 valores distintos '
    "inspeccionados a mano. Resultado: CONFIRMADO -- no se encontró ningún nombre de persona "
    'física identificable en su carácter privado. Los patrones "Nombre Apellido" que sí '
    "aparecen corresponden siempre a nombres de instituciones/hospitales que honran a "
    "figuras históricas o públicas, nombres de calles, topónimos de municipios/localidades/"
    "rancherías (muchos con nombre de próceres históricos), o razones sociales de "
    "contratistas -- nunca a un particular actuando como tal (propietario de domicilio, "
    "etc.). Salvedad declarada: es una revisión por muestreo extenso, no un censo exhaustivo "
    "de los ~16,700 valores distintos combinados; no descarta con certeza absoluta un caso "
    "aislado fuera de las muestras revisadas."
)


def _seccion_evaluacion_privacidad() -> str:
    return f"## Evaluación de datos personales (Art. 38-VI)\n\n{VEREDICTO_PRIVACIDAD}\n"


def _seccion_patron_estacional() -> str:
    return (
        "## Patrón estacional Q4→Q1\n\n"
        "El corte del primer trimestre de cada año muestra sistemáticamente menos PPI que el "
        "trimestre anterior: el universo TOTAL del padrón (todos los ramos juntos) cae de "
        "forma sistemática entre 15% y 29% cada enero-marzo, verificado con datos reales de "
        "2022, 2023, 2025 y 2026. Es un patrón estacional estructural de la fuente SHCP -- "
        "probablemente porque los proyectos plurianuales vigentes se re-registran/reautorizan "
        "presupuestalmente antes de volver a aparecer en el reporte trimestral -- no un error "
        "de carga. Investigado el 2026-08-08 mediante consulta directa a "
        "`data/gold/panel_opa.duckdb`, con cada conclusión revisada por un segundo agente "
        "independiente con instrucción explícita de intentar refutarla. El test "
        "`dbt/tests/assert_conteo_ppi_por_ramo_estable.sql` excluye a propósito las "
        "transiciones trimestre=1 con trimestre_anterior=4 por esta razón; sigue activo para "
        "cualquier otra transición de trimestre, donde una caída de 70%+ sí sería inusual. Ver "
        "ese archivo para el detalle técnico completo.\n"
    )


def _seccion_calidad_conocida(calidad: dict) -> str:
    return (
        "## Cortes con calidad conocida y verificada\n\n"
        f"De los snapshots normalizados a parquet, **{calidad['snapshots_omitidos_corruptos']}** "
        "se omitieron por corrupción conocida en la fuente misma: los 3 productos de 2024 T1 "
        "(`ConsolidadoOPA1erTrimestre2024.csv`, `SeguimientoOPA1erTrimestre2024.csv`, "
        "`ConcluidosOPA1erTrimestre2024.csv`) llegan del servidor de la SHCP como un binario "
        "OLE2 (firma de Excel `.xls` antiguo) con extensión `.csv` y `Content-Type: "
        "text/csv`, truncado -- `xlrd` confirma que el stream interno declara más bytes de los "
        "que el archivo realmente tiene. El `Content-Length` del servidor coincide "
        "exactamente con lo descargado, así que no es un problema de la descarga, y no hay "
        "captura alterna en Wayback. `conf/schema_map.yml` los marca explícitamente en "
        "`snapshots_conocidos_corruptos` para que Silver los rechace ruidosamente en vez de "
        "intentar normalizarlos.\n\n"
        f"Del total de filas procesadas, **{calidad['pct_filas_validas']}%** "
        f"({calidad['filas_validas']:,} de {calidad['filas_totales']:,}) son válidas y se "
        f"escribieron a parquet; {calidad['filas_en_cuarentena']:,} filas quedaron en "
        "cuarentena por fallar el contrato Pandera y no se escribieron.\n"
    )


def _seccion_cobertura_parcial() -> str:
    return (
        "## Cobertura parcial en algunos cortes\n\n"
        '2020 T1 y T2 solo tienen disponible el producto "Concluido" de la fuente -- ni '
        "Consolidado ni Seguimiento se descubrieron para esos dos trimestres específicos. Eso "
        "significa que el universo de PPI de esos cortes NO es comparable al resto: son solo "
        "los proyectos que terminaron ese trimestre, no el universo completo vigente. "
        "`int_snapshot_canonico.sql` marca estos cortes con `cobertura_parcial_del_universo` "
        "para no confundir un hueco de cobertura con un hallazgo real. Cualquier comparación "
        "de conteos que cruce esos cortes con un corte de universo completo compara universos "
        "distintos por diseño de la fuente, no un cambio real -- ver "
        "`dbt/models/intermediate/int_snapshot_canonico.sql` para el detalle exacto.\n"
    )


def _seccion_huecos_historicos() -> str:
    return (
        "## Huecos históricos reales\n\n"
        "**7 trimestres siguen sin recuperarse: 2016 T1/T2/T4, 2017 T4, y 2018 T1/T2/T4.** No "
        "están inventados ni interpolados -- simplemente no existen bajo ninguna fuente "
        "conocida. Se agotaron 4 vías de descubrimiento independientes (manifiesto oficial, "
        "Wayback CDX dirigido por año, Common Crawl, variaciones de nomenclatura probadas en "
        "vivo) más una reclasificación en frío de capturas de Wayback ya recolectadas. El "
        "siguiente paso realista es una solicitud de acceso a la información (PNT/INAI) a la "
        "SHCP, no más automatización. Quedan documentados como huecos en "
        "`reports/cobertura.md`.\n"
    )


def _seccion_deflactacion() -> str:
    return (
        "## Deflactación pendiente\n\n"
        "`modificado_real`, `ejercido_real` y `monto_total_inversion_real` existen en "
        "`fct_ppi_observacion` pero son NULL hasta que alguien con acceso a un token de "
        "Banxico SIE llene `conf/deflactor_inpc.csv` con la serie real de INPC. No se "
        "aproximó con un supuesto de inflación genérico.\n"
    )


def _seccion_variantes_texto() -> str:
    return (
        "## Variantes de texto sin normalizar\n\n"
        "`estatus_operacion` y `descripcion_tipo_ppi` traen variantes de forma (mayúscula/"
        "minúscula, con/sin espacios, singular/plural) de 11 años de fuente sin normalizar. "
        "Los tests `accepted_values` en `dbt/models/marts/schema.yml` fijan el conjunto "
        "conocido hoy para detectar valores nuevos, no certifican que estén limpios.\n"
    )


def _seccion_pie(procedencia: dict) -> str:
    anio_min, anio_max = procedencia["rango_anios"]
    return (
        "---\n\n"
        f"Fecha de descarga más reciente: {procedencia['fecha_descarga_mas_reciente']}. "
        f"Rango de años cubierto por bronze: {anio_min}-{anio_max}. Este archivo se regenera "
        "con cada corrida de `opa publish` a partir de los insumos reales del pipeline -- no "
        "es una versión congelada a mano.\n"
    )


def escribir_nota_tecnica(
    dir_paquete: Path, ruta_manifest: Path, ruta_calidad_silver: Path
) -> Path:
    """Escribe ``dir_paquete/NOTA-TECNICA.md`` documentando las limitaciones conocidas del dataset."""
    procedencia = resumen_procedencia(ruta_manifest)
    calidad = resumen_calidad(ruta_calidad_silver)

    dir_paquete.mkdir(parents=True, exist_ok=True)

    secciones = [
        "# Nota técnica\n",
        (
            "Documenta las limitaciones conocidas de este dataset conforme al Art. 39-IV-c de "
            "los Lineamientos ATDT.\n"
        ),
        _seccion_evaluacion_privacidad(),
        _seccion_patron_estacional(),
        _seccion_calidad_conocida(calidad),
        _seccion_cobertura_parcial(),
        _seccion_huecos_historicos(),
        _seccion_deflactacion(),
        _seccion_variantes_texto(),
        _seccion_pie(procedencia),
    ]

    ruta_nota = dir_paquete / "NOTA-TECNICA.md"
    ruta_nota.write_text("\n".join(secciones), encoding="utf-8")
    return ruta_nota
