"""Parser for Spectra manual collection files."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from spectra.spec_loader import SpecLoaderError
from spectra.spec_parser import Endpoint, Parameter


@dataclass(slots=True)
class ParsedCollection:
    name: str
    base_url: str
    endpoints: list[Endpoint]
    by_tag: dict[str, list[Endpoint]]


def _require_string(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        msg = f"Collection field {field_name!r} must be a string"
        raise SpecLoaderError(msg)
    return value.strip()


def _parse_parameter(raw_parameter: object, endpoint_label: str) -> Parameter:
    if not isinstance(raw_parameter, dict):
        msg = f"Parameter in {endpoint_label} must be an object"
        raise SpecLoaderError(msg)

    return Parameter(
        name=_require_string(raw_parameter.get("name", ""), "name") or "unnamed",
        location=_require_string(raw_parameter.get("in", "query"), "in") or "query",
        required=bool(raw_parameter.get("required", False)),
        schema=_require_string(raw_parameter.get("type", ""), "type"),
        description=str(raw_parameter.get("description", "")).strip(),
    )


def parse_collection(document: dict) -> ParsedCollection:
    """Parse a `.spectra.json` collection file into endpoint metadata."""
    if not isinstance(document, dict):
        msg = "Collection document must be a JSON object"
        raise SpecLoaderError(msg)

    name = _require_string(document.get("name", ""), "name")
    base_url = str(document.get("baseUrl", "")).strip()

    raw_groups = document.get("groups", [])
    if not isinstance(raw_groups, list):
        msg = "Collection field 'groups' must be a list"
        raise SpecLoaderError(msg)

    endpoints: list[Endpoint] = []
    by_tag: dict[str, list[Endpoint]] = {}

    for raw_group in raw_groups:
        if not isinstance(raw_group, dict):
            msg = "Collection groups must be objects"
            raise SpecLoaderError(msg)

        group_name = _require_string(raw_group.get("name", ""), "group.name") or "default"
        raw_endpoints = raw_group.get("endpoints", [])
        if not isinstance(raw_endpoints, list):
            msg = f"Group {group_name!r} must define an 'endpoints' list"
            raise SpecLoaderError(msg)

        group_endpoints: list[Endpoint] = []
        for raw_endpoint in raw_endpoints:
            if not isinstance(raw_endpoint, dict):
                msg = f"Endpoint in group {group_name!r} must be an object"
                raise SpecLoaderError(msg)

            method = _require_string(raw_endpoint.get("method", ""), "method").upper() or "GET"
            path = _require_string(raw_endpoint.get("path", ""), "path")
            endpoint_label = f"{method} {path or '<empty>'}"

            raw_parameters = raw_endpoint.get("parameters", [])
            if not isinstance(raw_parameters, list):
                msg = f"Collection endpoint {endpoint_label} has invalid parameters"
                raise SpecLoaderError(msg)

            endpoint = Endpoint(
                method=method,
                path=path,
                summary=str(raw_endpoint.get("summary", "")).strip(),
                description=str(raw_endpoint.get("description", "")).strip(),
                tags=[group_name],
                parameters=[
                    _parse_parameter(raw_parameter, endpoint_label)
                    for raw_parameter in raw_parameters
                ],
                request_body=str(raw_endpoint.get("requestBodyExample", "")).strip(),
                example_body=str(raw_endpoint.get("requestBodyExample", "")).strip(),
            )
            group_endpoints.append(endpoint)
            endpoints.append(endpoint)

        by_tag[group_name] = group_endpoints

    return ParsedCollection(name=name, base_url=base_url, endpoints=endpoints, by_tag=by_tag)


def load_collection(path_str: str) -> ParsedCollection:
    """Load and parse a `.spectra.json` file from disk."""
    path = Path(path_str).expanduser()
    if not path.exists():
        msg = f"Collection file not found: {path}"
        raise SpecLoaderError(msg)
    if not path.is_file():
        msg = f"Collection path is not a file: {path}"
        raise SpecLoaderError(msg)

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        msg = f"Unable to read collection file {path}: {exc}"
        raise SpecLoaderError(msg) from exc

    if not content.strip():
        msg = f"Collection from {str(path)!r} is empty"
        raise SpecLoaderError(msg)

    try:
        document = json.loads(content)
    except json.JSONDecodeError as exc:
        msg = f"Invalid collection JSON from {str(path)!r}: {exc.msg}"
        raise SpecLoaderError(msg) from exc

    return parse_collection(document)


def collection_to_dict(name: str, base_url: str, by_tag: dict[str, list[Endpoint]]) -> dict:
    """Serialize grouped endpoints into a `.spectra.json` document."""
    groups: list[dict[str, object]] = []
    for group_name in sorted(by_tag):
        endpoints: list[dict[str, object]] = []
        for endpoint in by_tag[group_name]:
            parameters = [
                {
                    "name": parameter.name,
                    "in": parameter.location,
                    "required": parameter.required,
                    "type": parameter.schema,
                    "description": parameter.description,
                }
                for parameter in endpoint.parameters
            ]
            endpoints.append(
                {
                    "method": endpoint.method,
                    "path": endpoint.path,
                    "summary": endpoint.summary,
                    "description": endpoint.description,
                    "parameters": parameters,
                    "requestBodyExample": endpoint.example_body,
                }
            )
        groups.append({"name": group_name, "endpoints": endpoints})

    return {"name": name, "baseUrl": base_url, "groups": groups}
