"""Tests de la carga y validación de conf/dcat.yml (Fase C del plan ATDT).

Construye YAML de prueba en ``tmp_path`` -- no depende del ``conf/dcat.yml`` real del repo,
porque este test valida la FUNCIÓN de carga, no el contenido real.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from opa.dcat_config import ErrorDcatConfig, cargar_dcat_config

_YAML_VALIDO = """
catalogo:
  titulo: "Panel Histórico de Obra Pública Federal (México)"
  descripcion: "Panel longitudinal de PPI federales reconstruido a partir de OPA/SHCP."
  temas:
    - "finanzas públicas"
    - "obra pública"
  licencia:
    nombre: "Términos de Libre Uso MX"
    url: "https://datos.gob.mx/libreusomx"
    fundamento: "DOF 20/02/2015."
  cadencia:
    valor: "trimestral"
    fundamento: "Sigue el calendario de publicación de la SHCP."
  contacto:
    nombre: "Repositorio panel-obra-publica-mx"
    referencia: "https://github.com/iChocko/panel-obra-publica-mx"
  fuente_primaria:
    nombre: "SHCP -- Obra Pública Abierta"
    url: "https://www.transparenciapresupuestaria.gob.mx"
"""


def _escribir(tmp_path: Path, contenido: str) -> Path:
    ruta = tmp_path / "dcat.yml"
    ruta.write_text(contenido, encoding="utf-8")
    return ruta


def test_yaml_completo_y_valido_carga_bien(tmp_path: Path) -> None:
    ruta = _escribir(tmp_path, _YAML_VALIDO)

    config = cargar_dcat_config(ruta)

    assert config["catalogo"]["titulo"] == "Panel Histórico de Obra Pública Federal (México)"
    assert config["catalogo"]["licencia"]["url"] == "https://datos.gob.mx/libreusomx"
    assert config["catalogo"]["cadencia"]["valor"] == "trimestral"
    assert config["catalogo"]["fuente_primaria"]["url"] == (
        "https://www.transparenciapresupuestaria.gob.mx"
    )
    assert config["catalogo"]["temas"] == ["finanzas públicas", "obra pública"]


def test_falta_clave_anidada_levanta_con_esa_clave_nombrada(tmp_path: Path) -> None:
    yaml_sin_url_licencia = """
catalogo:
  titulo: "Panel Histórico de Obra Pública Federal (México)"
  descripcion: "Panel longitudinal de PPI federales."
  licencia:
    nombre: "Términos de Libre Uso MX"
  cadencia:
    valor: "trimestral"
  fuente_primaria:
    url: "https://www.transparenciapresupuestaria.gob.mx"
"""
    ruta = _escribir(tmp_path, yaml_sin_url_licencia)

    with pytest.raises(ErrorDcatConfig, match="catalogo.licencia.url"):
        cargar_dcat_config(ruta)


def test_faltan_varias_claves_a_la_vez_y_el_mensaje_las_lista_todas(tmp_path: Path) -> None:
    yaml_incompleto = """
catalogo:
  descripcion: "Panel longitudinal de PPI federales."
  licencia:
    nombre: "Términos de Libre Uso MX"
  cadencia: {}
"""
    ruta = _escribir(tmp_path, yaml_incompleto)

    with pytest.raises(ErrorDcatConfig) as exc_info:
        cargar_dcat_config(ruta)

    mensaje = str(exc_info.value)
    assert "catalogo.titulo" in mensaje
    assert "catalogo.licencia.url" in mensaje
    assert "catalogo.cadencia.valor" in mensaje
    assert "catalogo.fuente_primaria.url" in mensaje
    # No debe reportar como faltante una clave que sí está presente y no vacía.
    assert "catalogo.descripcion" not in mensaje
    assert "catalogo.licencia.nombre" not in mensaje


def test_valor_vacio_cuenta_como_faltante(tmp_path: Path) -> None:
    yaml_titulo_vacio = """
catalogo:
  titulo: "   "
  descripcion: "Panel longitudinal de PPI federales."
  licencia:
    nombre: "Términos de Libre Uso MX"
    url: "https://datos.gob.mx/libreusomx"
  cadencia:
    valor: "trimestral"
  fuente_primaria:
    url: "https://www.transparenciapresupuestaria.gob.mx"
"""
    ruta = _escribir(tmp_path, yaml_titulo_vacio)

    with pytest.raises(ErrorDcatConfig, match="catalogo.titulo"):
        cargar_dcat_config(ruta)


def test_archivo_inexistente_levanta_error_claro(tmp_path: Path) -> None:
    with pytest.raises(ErrorDcatConfig, match="No existe"):
        cargar_dcat_config(tmp_path / "no_existe.yml")


def test_yaml_raiz_no_es_mapeo_levanta_error_claro(tmp_path: Path) -> None:
    ruta = _escribir(tmp_path, "- solo\n- una\n- lista\n")

    with pytest.raises(ErrorDcatConfig, match="mapeo"):
        cargar_dcat_config(ruta)
