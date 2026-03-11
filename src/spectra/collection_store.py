"""Persistence for Spectra endpoint collections."""

from __future__ import annotations

import json
from pathlib import Path

from spectra.spec_parser import Endpoint, Parameter, ParsedSpec

COLLECTION_FORMAT = "spectra.collection"
COLLECTION_VERSION = 1


class CollectionStoreError(ValueError):
    """Raised when a Spectra collection cannot be read or written."""


def _endpoint_to_dict(endpoint: Endpoint) -> dict:
    return {
        "method": endpoint.method,
        "path": endpoint.path,
        "url": endpoint.url,
        "summary": endpoint.summary,
        "description": endpoint.description,
        "tags": endpoint.tags,
        "parameters": [
            {
                "name": parameter.name,
                "location": parameter.location,
                "required": parameter.required,
                "schema": parameter.schema,
            }
            for parameter in endpoint.parameters
        ],
        "request_headers": endpoint.request_headers,
        "request_body": endpoint.request_body,
        "responses": endpoint.responses,
    }


def _endpoint_from_dict(raw: dict) -> Endpoint:
    parameters = []
    for item in raw.get("parameters", []):
        if not isinstance(item, dict):
            continue
        parameters.append(
            Parameter(
                name=str(item.get("name", "unnamed")),
                location=str(item.get("location", "unknown")),
                required=bool(item.get("required", False)),
                schema=str(item.get("schema", "")),
            )
        )

    request_headers = raw.get("request_headers", {})
    if not isinstance(request_headers, dict):
        request_headers = {}

    responses = raw.get("responses", {})
    if not isinstance(responses, dict):
        responses = {}

    tags = raw.get("tags", ["default"])
    if not isinstance(tags, list) or not tags:
        tags = ["default"]

    return Endpoint(
        method=str(raw.get("method", "GET")).upper(),
        path=str(raw.get("path", "/")),
        url=str(raw.get("url", "")),
        summary=str(raw.get("summary", "")),
        description=str(raw.get("description", "")),
        tags=[str(tag) for tag in tags],
        parameters=parameters,
        request_headers={str(key): str(value) for key, value in request_headers.items()},
        request_body=str(raw.get("request_body", "")),
        responses={str(key): str(value) for key, value in responses.items()},
    )


def save_collection(path: str, parsed: ParsedSpec) -> None:
    payload = {
        "format": COLLECTION_FORMAT,
        "version": COLLECTION_VERSION,
        "endpoints": [_endpoint_to_dict(endpoint) for endpoint in parsed.endpoints],
    }
    target = Path(path).expanduser()
    try:
        target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError as exc:
        raise CollectionStoreError(f"Unable to write collection {target}: {exc}") from exc


def load_collection(path: str) -> ParsedSpec:
    target = Path(path).expanduser()
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CollectionStoreError(f"Collection file not found: {target}") from exc
    except OSError as exc:
        raise CollectionStoreError(f"Unable to read collection {target}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise CollectionStoreError(f"Invalid collection JSON in {target}: {exc.msg}") from exc

    if raw.get("format") != COLLECTION_FORMAT:
        raise CollectionStoreError(f"Unsupported collection format in {target}")
    if raw.get("version") != COLLECTION_VERSION:
        raise CollectionStoreError(f"Unsupported collection version in {target}")

    raw_endpoints = raw.get("endpoints")
    if not isinstance(raw_endpoints, list):
        raise CollectionStoreError(f"Collection endpoints are invalid in {target}")

    endpoints = [_endpoint_from_dict(item) for item in raw_endpoints if isinstance(item, dict)]
    by_tag: dict[str, list[Endpoint]] = {}
    for endpoint in endpoints:
        for tag in endpoint.tags or ["default"]:
            by_tag.setdefault(tag, []).append(endpoint)
    return ParsedSpec(endpoints=endpoints, by_tag=by_tag)
