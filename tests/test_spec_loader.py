from __future__ import annotations

from pathlib import Path

import pytest
import requests

from spectra.spec_loader import SpecLoaderError, load_spec

OPENAPI_JSON = '{"openapi":"3.0.0","paths":{}}'
OPENAPI_YAML = "openapi: 3.0.1\npaths: {}\n"
SWAGGER_JSON = '{"swagger":"2.0","paths":{}}'


def test_load_local_json(tmp_path: Path) -> None:
    file_path = tmp_path / "spec.json"
    file_path.write_text(OPENAPI_JSON, encoding="utf-8")

    spec = load_spec(str(file_path))

    assert spec["openapi"] == "3.0.0"


def test_load_local_yaml(tmp_path: Path) -> None:
    file_path = tmp_path / "spec.yaml"
    file_path.write_text(OPENAPI_YAML, encoding="utf-8")

    spec = load_spec(str(file_path))

    assert spec["openapi"] == "3.0.1"


def test_load_swagger2(tmp_path: Path) -> None:
    file_path = tmp_path / "swagger.json"
    file_path.write_text(SWAGGER_JSON, encoding="utf-8")

    spec = load_spec(str(file_path))

    assert spec["swagger"] == "2.0"


def test_load_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(SpecLoaderError, match="not found"):
        load_spec(str(tmp_path / "missing.json"))


def test_load_directory_raises(tmp_path: Path) -> None:
    with pytest.raises(SpecLoaderError, match="not a file"):
        load_spec(str(tmp_path))


def test_empty_file_raises(tmp_path: Path) -> None:
    file_path = tmp_path / "empty.yaml"
    file_path.write_text("", encoding="utf-8")

    with pytest.raises(SpecLoaderError, match="empty"):
        load_spec(str(file_path))


def test_invalid_text_raises(tmp_path: Path) -> None:
    file_path = tmp_path / "bad.txt"
    file_path.write_text("not: [valid", encoding="utf-8")

    with pytest.raises(SpecLoaderError, match="Invalid OpenAPI/Swagger"):
        load_spec(str(file_path))


def test_unsupported_openapi_version_raises(tmp_path: Path) -> None:
    file_path = tmp_path / "v31.json"
    file_path.write_text('{"openapi":"4.0.0","paths":{}}', encoding="utf-8")

    with pytest.raises(SpecLoaderError, match="Unsupported OpenAPI"):
        load_spec(str(file_path))


def test_unsupported_swagger_version_raises(tmp_path: Path) -> None:
    file_path = tmp_path / "swagger1.json"
    file_path.write_text('{"swagger":"1.2","paths":{}}', encoding="utf-8")

    with pytest.raises(SpecLoaderError, match="Unsupported Swagger"):
        load_spec(str(file_path))


def test_missing_version_keys_raises(tmp_path: Path) -> None:
    file_path = tmp_path / "noversion.json"
    file_path.write_text('{"paths":{}}', encoding="utf-8")

    with pytest.raises(SpecLoaderError, match="must define"):
        load_spec(str(file_path))


def test_load_url_json(mocker) -> None:
    response = mocker.Mock()
    response.text = OPENAPI_JSON
    response.raise_for_status.return_value = None
    mock_get = mocker.patch("spectra.spec_loader.requests.get", return_value=response)

    spec = load_spec("https://example.com/openapi.json")

    mock_get.assert_called_once()
    assert spec["openapi"] == "3.0.0"


def test_load_url_yaml(mocker) -> None:
    response = mocker.Mock()
    response.text = OPENAPI_YAML
    response.raise_for_status.return_value = None
    mocker.patch("spectra.spec_loader.requests.get", return_value=response)

    spec = load_spec("https://example.com/openapi.yaml")

    assert spec["openapi"] == "3.0.1"


def test_load_url_request_error_raises(mocker) -> None:
    mocker.patch("spectra.spec_loader.requests.get", side_effect=requests.RequestException("boom"))

    with pytest.raises(SpecLoaderError, match="Unable to fetch"):
        load_spec("https://example.com/fail")
