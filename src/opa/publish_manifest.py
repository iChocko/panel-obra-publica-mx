"""Manifiesto de checksums del paquete publicado (Fase B del plan de alineación ATDT).

Escribe ``checksums.sha256`` en el formato estándar de ``sha256sum`` sobre todos los
archivos de un paquete de distribución ya exportado, para que su integridad sea
verificable con ``sha256sum -c checksums.sha256`` desde el directorio del paquete.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

TAMANO_CHUNK = 65536
NOMBRE_CHECKSUMS = "checksums.sha256"


class ErrorManifiesto(RuntimeError):
    """dir_paquete no existe o no tiene ningún archivo que sumar."""


def _sha256_archivo(ruta: Path) -> str:
    hasher = hashlib.sha256()
    with ruta.open("rb") as fh:
        for bloque in iter(lambda: fh.read(TAMANO_CHUNK), b""):
            hasher.update(bloque)
    return hasher.hexdigest()


def escribir_checksums(dir_paquete: Path) -> Path:
    """Calcula sha256 de cada archivo del paquete publicado y escribe checksums.sha256."""
    if not dir_paquete.is_dir():
        raise ErrorManifiesto(f"dir_paquete no existe o no es un directorio: {dir_paquete}")

    ruta_checksums = dir_paquete / NOMBRE_CHECKSUMS
    archivos = [
        p for p in dir_paquete.rglob("*") if p.is_file() and p != ruta_checksums
    ]
    if not archivos:
        raise ErrorManifiesto(f"dir_paquete no tiene ningún archivo que sumar: {dir_paquete}")

    rutas_relativas = sorted(p.relative_to(dir_paquete).as_posix() for p in archivos)
    lineas = [
        f"{_sha256_archivo(dir_paquete / ruta_rel)}  {ruta_rel}" for ruta_rel in rutas_relativas
    ]
    ruta_checksums.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return ruta_checksums
