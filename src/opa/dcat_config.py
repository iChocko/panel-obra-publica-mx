"""Carga y validación de conf/dcat.yml (Fase C del plan de alineación ATDT).

``conf/dcat.yml`` guarda lo declarativo de los metadatos DCAT que no se puede derivar de
otros archivos del repo (título, descripción, licencia, cadencia, contacto, fuente primaria).
Este módulo solo lee y valida ese archivo -- la construcción del ``catalog.json`` (que además
combina ``data/manifest.jsonl`` y ``reports/calidad_silver.md``) vive en otro módulo.

Misma filosofía que ``diccionario.py``: una configuración incompleta es un error de build, no
una advertencia -- se reportan TODAS las claves faltantes de una sola vez.
"""

from __future__ import annotations

from pathlib import Path

import yaml

# (ruta de claves anidadas, ruta legible con puntos) -- se valida presencia y no-vacío.
_CLAVES_REQUERIDAS: list[tuple[tuple[str, ...], str]] = [
    (("catalogo", "titulo"), "catalogo.titulo"),
    (("catalogo", "descripcion"), "catalogo.descripcion"),
    (("catalogo", "licencia", "nombre"), "catalogo.licencia.nombre"),
    (("catalogo", "licencia", "url"), "catalogo.licencia.url"),
    (("catalogo", "cadencia", "valor"), "catalogo.cadencia.valor"),
    (("catalogo", "fuente_primaria", "url"), "catalogo.fuente_primaria.url"),
]


class ErrorDcatConfig(RuntimeError):
    """conf/dcat.yml no existe, no es un mapeo válido, o le faltan claves requeridas."""


def _valor_en_ruta(config: dict, ruta: tuple[str, ...]) -> object | None:
    """Recorre ``ruta`` dentro de ``config``; regresa ``None`` si algún nivel falta o no es dict."""
    actual: object = config
    for clave in ruta:
        if not isinstance(actual, dict) or clave not in actual:
            return None
        actual = actual[clave]
    return actual


def cargar_dcat_config(ruta: Path) -> dict:
    """Lee y valida ``conf/dcat.yml``.

    Falla ruidoso con :class:`ErrorDcatConfig` listando TODAS las claves de nivel superior
    faltantes o vacías de una sola vez (no solo la primera que encuentra) -- si falta
    ``catalogo.titulo`` Y ``catalogo.licencia.url``, ambas aparecen en un solo mensaje.
    """
    if not ruta.is_file():
        raise ErrorDcatConfig(f"No existe el archivo de configuración DCAT: {ruta}")

    contenido = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    if not isinstance(contenido, dict):
        raise ErrorDcatConfig(
            f"{ruta}: el YAML raíz debe ser un mapeo con la clave 'catalogo', "
            f"se encontró {type(contenido).__name__}"
        )

    faltantes: list[str] = []
    for ruta_clave, nombre_legible in _CLAVES_REQUERIDAS:
        valor = _valor_en_ruta(contenido, ruta_clave)
        if valor is None or (isinstance(valor, str) and not valor.strip()):
            faltantes.append(nombre_legible)

    if faltantes:
        detalle = "\n  - ".join(faltantes)
        raise ErrorDcatConfig(
            f"{ruta}: faltan {len(faltantes)} clave(s) requerida(s) de conf/dcat.yml:\n  - {detalle}"
        )

    return contenido
