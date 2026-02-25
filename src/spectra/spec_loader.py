"""OpenAPI spec loader for local files and remote URLs."""

from __future__ import annotations

import json
from pathlib import Path

import requests
import yaml


class SpecLoaderError(ValueError):
    """Raised when a spec cannot be loaded or parsed."""


def _parse_spec_text(content: str, source: str) -> dict:
    if not content.strip():
        msg = f"Spec from {source!r} is empty"
        raise SpecLoaderError(msg)

    errors: list[str] = []

    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            return parsed
        errors.append("JSON is not an object")
    except json.JSONDecodeError as exc:
        errors.append(f"JSON parse error: {exc.msg}")

    try:
        parsed = yaml.safe_load(content)
        if isinstance(parsed, dict):
            return parsed
        errors.append("YAML is not an object")
    except yaml.YAMLError as exc:
        errors.append(f"YAML parse error: {exc}")

    joined = "; ".join(errors)
    msg = f"Invalid OpenAPI/Swagger spec from {source!r}: {joined}"
    raise SpecLoaderError(msg)


def _validate_version(spec: dict) -> None:
    openapi = spec.get("openapi")
    swagger = spec.get("swagger")

    if isinstance(openapi, str):
        if openapi.startswith("3."):
            return
        msg = f"Unsupported OpenAPI version: {openapi}"
        raise SpecLoaderError(msg)

    if isinstance(swagger, str):
        if swagger.startswith("2."):
            return
        msg = f"Unsupported Swagger version: {swagger}"
        raise SpecLoaderError(msg)

    msg = "Spec must define either 'openapi' (3.x) or 'swagger' (2.x)"
    raise SpecLoaderError(msg)


def load_spec(source: str, timeout: float = 15.0) -> dict:
    """Load OpenAPI/Swagger spec from a local file path or HTTP(S) URL."""
    if source.startswith(("http://", "https://")):
        try:
            response = requests.get(source, timeout=timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            msg = f"Unable to fetch URL {source!r}: {exc}"
            raise SpecLoaderError(msg) from exc
        spec = _parse_spec_text(response.text, source)
    else:
        path = Path(source).expanduser()
        if not path.exists():
            msg = f"Spec file not found: {path}"
            raise SpecLoaderError(msg)
        if not path.is_file():
            msg = f"Spec path is not a file: {path}"
            raise SpecLoaderError(msg)
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            msg = f"Unable to read spec file {path}: {exc}"
            raise SpecLoaderError(msg) from exc
        spec = _parse_spec_text(content, str(path))

    _validate_version(spec)
    return spec
