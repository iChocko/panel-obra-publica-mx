"""Tests del manifiesto de checksums del paquete publicado (Fase B del plan ATDT).

Verifica el formato exacto de ``checksums.sha256`` (compatible con ``sha256sum -c``),
el orden determinista de sus líneas, la auto-exclusión en corridas repetidas, y que un
paquete vacío o inexistente falle ruidoso en vez de escribir un manifiesto vacío.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from opa import publish_manifest


def _sha256(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


def _crear_paquete(base: Path) -> dict[str, bytes]:
    contenidos = {
        "tabular/dim_ramo.csv": b"id_ramo,nombre\n1,Salud\n",
        "tabular/nivel2/nivel3/hoja.csv": b"col_a,col_b\n1,2\n",
        "geojson/ppi_2021.geojson": b'{"type": "FeatureCollection", "features": []}',
        "parquet/fct_ppi_observacion.parquet": b"\x00\x01contenido-binario-simulado\x02\x03",
    }
    for ruta_rel, contenido in contenidos.items():
        ruta = base / ruta_rel
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_bytes(contenido)
    return contenidos


def test_escribe_checksums_con_hashes_correctos(tmp_path: Path) -> None:
    contenidos = _crear_paquete(tmp_path)

    ruta_checksums = publish_manifest.escribir_checksums(tmp_path)

    assert ruta_checksums == tmp_path / "checksums.sha256"
    texto = ruta_checksums.read_text(encoding="utf-8")
    lineas = texto.splitlines()
    assert len(lineas) == len(contenidos)

    esperado_por_ruta = {
        ruta_rel: _sha256(contenido) for ruta_rel, contenido in contenidos.items()
    }
    for linea in lineas:
        hash_hex, separador, ruta_rel = linea.partition("  ")
        assert separador == "  "
        assert ruta_rel in esperado_por_ruta
        assert hash_hex == esperado_por_ruta[ruta_rel]
        assert "/" in ruta_rel or ruta_rel.count("/") == 0
        assert not ruta_rel.startswith("/")
        assert "\\" not in ruta_rel


def test_lineas_ordenadas_alfabeticamente(tmp_path: Path) -> None:
    _crear_paquete(tmp_path)

    ruta_checksums = publish_manifest.escribir_checksums(tmp_path)

    lineas = ruta_checksums.read_text(encoding="utf-8").splitlines()
    rutas = [linea.partition("  ")[2] for linea in lineas]
    assert rutas == sorted(rutas)


def test_segunda_corrida_no_se_autoincluye_y_es_estable(tmp_path: Path) -> None:
    _crear_paquete(tmp_path)

    publish_manifest.escribir_checksums(tmp_path)
    primera = (tmp_path / "checksums.sha256").read_text(encoding="utf-8")

    ruta_checksums = publish_manifest.escribir_checksums(tmp_path)
    segunda = ruta_checksums.read_text(encoding="utf-8")

    assert primera == segunda
    assert "checksums.sha256" not in segunda


def test_dir_paquete_vacio_levanta_excepcion(tmp_path: Path) -> None:
    (tmp_path / "vacio").mkdir()

    with pytest.raises(publish_manifest.ErrorManifiesto, match="ningún archivo"):
        publish_manifest.escribir_checksums(tmp_path / "vacio")


def test_dir_paquete_inexistente_levanta_excepcion(tmp_path: Path) -> None:
    with pytest.raises(publish_manifest.ErrorManifiesto, match="no existe"):
        publish_manifest.escribir_checksums(tmp_path / "no_existe")
