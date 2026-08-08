"""Manifiesto append-only de snapshots Bronze.

Ver ``ARQUITECTURA-panel-obra-publica-mx.md`` sección 4.1: bronze es el archivo original,
byte por byte, sin tocar. Cada descarga produce un renglón de manifiesto con procedencia
(hash, tamaño, URL, corte declarado) -- el manifiesto vive en git, bronze no.
"""

from __future__ import annotations

import hashlib
import io
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

_ENCODINGS_CSV = ("utf-8-sig", "utf-8", "latin-1")


@dataclass
class RegistroManifiesto:
    """Un renglón de ``data/manifest.jsonl`` -- procedencia completa de un snapshot bronze."""

    snapshot_id: str
    url: str
    origen: str  # "vivo" | "wayback" | "espejo"
    fecha_descarga: str  # AAAA-MM-DD, exigido por los Términos de Libre Uso MX
    http_status: int | None
    sha256: str
    bytes: int
    corte_declarado: dict[str, int | None]  # {"anio": ..., "trimestre": ... | None}
    archivo_bronze: str
    header_hash: str | None = None
    n_columnas: int | None = None
    encoding_detectado: str | None = None
    wayback_timestamp: str | None = None

    def to_json_line(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


def calcular_sha256(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


def _detectar_encoding_csv(contenido: bytes) -> str:
    for enc in _ENCODINGS_CSV:
        try:
            contenido.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
    return "latin-1"  # decodifica cualquier secuencia de bytes -- último recurso


def inspeccionar_columnas(contenido: bytes, ext: str) -> tuple[list[Any] | None, str | None]:
    """Lee solo el encabezado (nrows=0) -- nunca carga el archivo completo en memoria dos veces.

    Devuelve ``(columnas, encoding_detectado)``. El encoding es ``None`` para xlsx (binario).
    Si el archivo no se puede parsear (corrupto, formato inesperado), devuelve columnas=None
    sin lanzar -- un fallo de inspección no debe tumbar la ingesta de bronze.
    """
    ext = ext.lower().lstrip(".")
    if ext == "csv":
        encoding = _detectar_encoding_csv(contenido)
        try:
            df = pd.read_csv(io.BytesIO(contenido), dtype=str, nrows=0, encoding=encoding, engine="python", sep=None)
        except (pd.errors.ParserError, UnicodeDecodeError, ValueError):
            return None, encoding
        return list(df.columns), encoding
    if ext == "xlsx":
        try:
            df = pd.read_excel(io.BytesIO(contenido), nrows=0)
        except (ValueError, KeyError):
            return None, None
        return list(df.columns), None
    return None, None


def calcular_header_hash(columnas: list[Any] | None) -> str | None:
    """Hash del conjunto de columnas -- ver sección 5.3, es lo que detecta cambio de esquema.

    Algunos archivos (reportes con encabezado no estándar, ej. varias filas de título antes
    de la tabla real) hacen que pandas infiera nombres de columna no-string (enteros
    posicionales) -- se normaliza a str explícitamente en vez de asumir que ya lo son.
    """
    if not columnas:
        return None
    return hashlib.sha256(",".join(str(c) for c in columnas).encode("utf-8")).hexdigest()


def slug_desde_url(url: str) -> str:
    """Nombre base limpio a partir del archivo en la URL -- para snapshots sin año/trimestre
    (auxiliares), donde el hash solo no es suficientemente legible en el nombre del archivo."""
    nombre = url.rsplit("/", 1)[-1].split("?")[0]
    base = nombre.rsplit(".", 1)[0] if "." in nombre else nombre
    limpio = "".join(c if c.isalnum() else "_" for c in base).strip("_").lower()
    return limpio or "archivo"


def construir_snapshot_id(anio: int | None, trimestre: int | None, sha256: str, slug: str | None = None) -> str:
    sha8 = sha256[:8]
    if anio is not None and trimestre is not None:
        return f"{anio}Q{trimestre}_{sha8}"
    if anio is not None:
        return f"{anio}_anual_{sha8}"
    return f"aux_{slug or 'archivo'}_{sha8}"


def nombre_archivo_bronze(
    anio: int | None, trimestre: int | None, sha256: str, ext: str, slug: str | None = None
) -> str:
    """``bronze/opa_{anio}_{trimestre}_{sha8}.{ext}`` -- nombre determinista y con contenido
    direccionable: el mismo byte a byte siempre produce el mismo nombre (idempotente sin
    necesidad de lógica de deduplicación aparte)."""
    sha8 = sha256[:8]
    ext = ext.lower().lstrip(".")
    if anio is not None and trimestre is not None:
        return f"opa_{anio}_{trimestre}_{sha8}.{ext}"
    if anio is not None:
        return f"opa_{anio}_anual_{sha8}.{ext}"
    return f"opa_aux_{slug or 'archivo'}_{sha8}.{ext}"


def cargar_manifiesto(ruta: Path) -> list[RegistroManifiesto]:
    if not ruta.exists():
        return []
    registros: list[RegistroManifiesto] = []
    with ruta.open(encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if linea:
                datos: dict[str, Any] = json.loads(linea)
                registros.append(RegistroManifiesto(**datos))
    return registros


def claves_ya_ingeridas(registros: list[RegistroManifiesto]) -> set[tuple[str, int | None, int | None]]:
    """``(url, anio, trimestre)`` ya presentes en el manifiesto -- ingesta es "una vez por
    snapshot, nunca se vuelve a pedir" (sección 5.2), no por hash (eso solo se sabe post-descarga)."""
    return {
        (r.url, r.corte_declarado.get("anio"), r.corte_declarado.get("trimestre")) for r in registros
    }
