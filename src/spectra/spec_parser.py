"""Parsers for OpenAPI, Swagger, and Postman endpoint metadata."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from urllib.parse import urlencode

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}


@dataclass(slots=True)
class Parameter:
    name: str
    location: str
    required: bool
    schema: str


@dataclass(slots=True)
class Endpoint:
    method: str
    path: str
    summary: str
    description: str
    tags: list[str] = field(default_factory=list)
    parameters: list[Parameter] = field(default_factory=list)
    request_body: str = ""
    responses: dict[str, str] = field(default_factory=dict)
    request_url: str = ""
    request_headers: dict[str, str] = field(default_factory=dict)
    request_body_text: str = ""


@dataclass(slots=True)
class ParsedSpec:
    endpoints: list[Endpoint]
    by_tag: dict[str, list[Endpoint]]
    variables: dict[str, str] = field(default_factory=dict)


def _schema_to_text(schema: dict | None) -> str:
    if not isinstance(schema, dict) or not schema:
        return ""

    if "$ref" in schema:
        return str(schema["$ref"])

    schema_type = schema.get("type")
    if schema_type == "array":
        inner = _schema_to_text(schema.get("items")) or "any"
        return f"array[{inner}]"

    if schema_type == "object":
        properties = schema.get("properties") or {}
        if isinstance(properties, dict) and properties:
            keys = ", ".join(sorted(properties))
            return f"object{{{keys}}}"
        return "object"

    if isinstance(schema_type, str):
        return schema_type

    if "allOf" in schema:
        return "allOf"
    if "anyOf" in schema:
        return "anyOf"
    if "oneOf" in schema:
        return "oneOf"

    return "schema"


def _parse_openapi3_request_body(operation: dict) -> str:
    request_body = operation.get("requestBody")
    if not isinstance(request_body, dict):
        return ""

    content = request_body.get("content")
    if not isinstance(content, dict):
        return ""

    parts: list[str] = []
    for media_type, media_info in content.items():
        schema_text = _schema_to_text(
            media_info.get("schema") if isinstance(media_info, dict) else None
        )
        parts.append(f"{media_type}: {schema_text or 'unspecified'}")

    return "\n".join(parts)


def _parse_swagger2_request_body(operation: dict, parameters: list[dict]) -> str:
    body_params = [p for p in parameters if isinstance(p, dict) and p.get("in") == "body"]
    if not body_params:
        return ""

    body = body_params[0]
    schema_text = _schema_to_text(body.get("schema"))
    return schema_text or "body"


def _parse_responses(operation: dict) -> dict[str, str]:
    responses = operation.get("responses")
    if not isinstance(responses, dict):
        return {}

    parsed: dict[str, str] = {}
    for code, response_obj in responses.items():
        description = ""
        if isinstance(response_obj, dict):
            description = str(response_obj.get("description", "")).strip()

            content = response_obj.get("content")
            if isinstance(content, dict) and content:
                details: list[str] = []
                for media_type, media_info in content.items():
                    schema_text = _schema_to_text(
                        media_info.get("schema") if isinstance(media_info, dict) else None
                    )
                    details.append(f"{media_type}={schema_text or 'unspecified'}")
                extra = "; ".join(details)
                description = f"{description} [{extra}]".strip()

            schema = response_obj.get("schema")
            if schema:
                schema_text = _schema_to_text(schema if isinstance(schema, dict) else None)
                description = f"{description} [schema={schema_text}]".strip()

        parsed[str(code)] = description

    return parsed


def _parse_parameters(raw_parameters: list[dict]) -> list[Parameter]:
    parameters: list[Parameter] = []
    for item in raw_parameters:
        if not isinstance(item, dict):
            continue

        schema = item.get("schema")
        if not schema and "type" in item:
            schema = {"type": item["type"]}

        parameters.append(
            Parameter(
                name=str(item.get("name", "unnamed")),
                location=str(item.get("in", "unknown")),
                required=bool(item.get("required", False)),
                schema=_schema_to_text(schema if isinstance(schema, dict) else None),
            )
        )
    return parameters


def _merge_parameters(path_parameters: list[dict], operation_parameters: list[dict]) -> list[dict]:
    merged_parameters = [*path_parameters]
    parameter_positions = {
        (str(parameter.get("name", "")), str(parameter.get("in", ""))): index
        for index, parameter in enumerate(merged_parameters)
        if isinstance(parameter, dict)
    }

    for parameter in operation_parameters:
        if not isinstance(parameter, dict):
            continue

        parameter_key = (str(parameter.get("name", "")), str(parameter.get("in", "")))
        if parameter_key in parameter_positions:
            merged_parameters[parameter_positions[parameter_key]] = parameter
        else:
            parameter_positions[parameter_key] = len(merged_parameters)
            merged_parameters.append(parameter)

    return merged_parameters


def _group_by_tag(endpoints: list[Endpoint]) -> dict[str, list[Endpoint]]:
    by_tag: dict[str, list[Endpoint]] = {}
    for endpoint in endpoints:
        tags = endpoint.tags or ["default"]
        for tag in tags:
            by_tag.setdefault(tag, []).append(endpoint)
    return by_tag


def _build_postman_url(url_value: str | dict) -> tuple[str, str]:
    if isinstance(url_value, str):
        return url_value, url_value

    if not isinstance(url_value, dict):
        return "", ""

    raw = str(url_value.get("raw", "")).strip()

    path_value = url_value.get("path")
    if isinstance(path_value, list) and path_value:
        path = "/" + "/".join(str(part).strip("/") for part in path_value if str(part))
    elif isinstance(path_value, str) and path_value:
        path = path_value if path_value.startswith("/") else f"/{path_value}"
    else:
        path = raw

    query_value = url_value.get("query")
    if isinstance(query_value, list):
        query_items: list[tuple[str, str]] = []
        for item in query_value:
            if not isinstance(item, dict) or item.get("disabled"):
                continue
            key = str(item.get("key", "")).strip()
            value = str(item.get("value", "")).strip()
            if key:
                query_items.append((key, value))
        if query_items:
            query_text = urlencode(query_items)
            if query_text:
                separator = "&" if "?" in path else "?"
                path = f"{path}{separator}{query_text}"

    if raw:
        return raw, path

    protocol = str(url_value.get("protocol", "")).strip()
    host_value = url_value.get("host")
    if isinstance(host_value, list):
        host = ".".join(str(part) for part in host_value if str(part))
    else:
        host = str(host_value or "").strip()

    if protocol and host:
        return f"{protocol}://{host}{path}", path
    return path, path


def _parse_postman_headers(headers: Iterable[dict]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for item in headers:
        if not isinstance(item, dict) or item.get("disabled"):
            continue
        key = str(item.get("key", "")).strip()
        if not key:
            continue
        parsed[key] = str(item.get("value", "")).strip()
    return parsed


def _parse_postman_body(body: dict) -> str:
    mode = str(body.get("mode", "")).strip()
    if mode == "raw":
        return str(body.get("raw", ""))
    if mode in {"urlencoded", "formdata"}:
        rows: list[str] = []
        for item in body.get(mode, []):
            if not isinstance(item, dict) or item.get("disabled"):
                continue
            key = str(item.get("key", "")).strip()
            value = str(item.get("value", "")).strip()
            if key:
                rows.append(f"{key}={value}")
        return "\n".join(rows)
    if mode == "graphql":
        graphql = body.get("graphql")
        if not isinstance(graphql, dict):
            return ""
        parts: list[str] = []
        query = str(graphql.get("query", "")).strip()
        variables = graphql.get("variables")
        if query:
            parts.append(query)
        if variables:
            variable_text = variables
            if not isinstance(variable_text, str):
                variable_text = json.dumps(variable_text, indent=2, sort_keys=True)
            parts.append(str(variable_text))
        return "\n\n".join(parts)
    return ""


def _extract_postman_variables(spec: dict) -> dict[str, str]:
    raw_variables = spec.get("variable")
    if not isinstance(raw_variables, list):
        return {}

    variables: dict[str, str] = {}
    for item in raw_variables:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key", "")).strip()
        if not key:
            continue
        value = item.get("value", item.get("default", ""))
        variables[key] = "" if value is None else str(value)
    return variables


def _postman_description_text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        content = value.get("content")
        if isinstance(content, str):
            return content.strip()
    return ""


def _parse_postman_items(
    items: list[dict],
    folder_stack: list[str],
    endpoints: list[Endpoint],
) -> None:
    for item in items:
        if not isinstance(item, dict):
            continue

        nested_items = item.get("item")
        if isinstance(nested_items, list):
            folder_name = str(item.get("name", "")).strip()
            next_stack = [*folder_stack, folder_name] if folder_name else folder_stack
            _parse_postman_items(nested_items, next_stack, endpoints)
            continue

        request = item.get("request")
        if not isinstance(request, dict):
            continue

        request_url, display_path = _build_postman_url(request.get("url", ""))
        tags = [" / ".join(folder_stack)] if folder_stack else ["default"]
        body = request.get("body")
        body_text = _parse_postman_body(body) if isinstance(body, dict) else ""
        endpoint = Endpoint(
            method=str(request.get("method", "GET")).upper(),
            path=display_path or request_url or "/",
            summary=str(item.get("name", "")).strip(),
            description=_postman_description_text(request.get("description")),
            tags=tags,
            request_body=body_text,
            request_url=request_url or display_path or "/",
            request_headers=_parse_postman_headers(request.get("header", [])),
            request_body_text=body_text,
        )
        endpoints.append(endpoint)


def parse_spec(spec: dict) -> ParsedSpec:
    """Parse an OpenAPI 3.x, Swagger 2.x, or Postman Collection spec."""
    if isinstance(spec.get("item"), list):
        endpoints: list[Endpoint] = []
        _parse_postman_items(spec["item"], folder_stack=[], endpoints=endpoints)
        return ParsedSpec(
            endpoints=endpoints,
            by_tag=_group_by_tag(endpoints),
            variables=_extract_postman_variables(spec),
        )

    paths = spec.get("paths")
    if not isinstance(paths, dict):
        return ParsedSpec(endpoints=[], by_tag={}, variables={})

    is_openapi3 = isinstance(spec.get("openapi"), str)
    is_swagger2 = isinstance(spec.get("swagger"), str)

    endpoints: list[Endpoint] = []

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue

        path_parameters = path_item.get("parameters")
        if not isinstance(path_parameters, list):
            path_parameters = []

        for method, operation in path_item.items():
            if method.lower() not in HTTP_METHODS:
                continue
            if not isinstance(operation, dict):
                continue

            op_parameters = operation.get("parameters")
            if not isinstance(op_parameters, list):
                op_parameters = []

            merged_parameters = _merge_parameters(path_parameters, op_parameters)
            parameters = _parse_parameters([p for p in merged_parameters if isinstance(p, dict)])

            if is_openapi3:
                request_body = _parse_openapi3_request_body(operation)
            elif is_swagger2:
                request_body = _parse_swagger2_request_body(operation, merged_parameters)
            else:
                request_body = ""

            tags = operation.get("tags")
            if not isinstance(tags, list) or not tags:
                tags = ["default"]

            endpoint = Endpoint(
                method=method.upper(),
                path=str(path),
                summary=str(operation.get("summary", "")).strip(),
                description=str(operation.get("description", "")).strip(),
                tags=[str(tag) for tag in tags],
                parameters=parameters,
                request_body=request_body,
                responses=_parse_responses(operation),
                request_url=str(path),
            )
            endpoints.append(endpoint)

    return ParsedSpec(endpoints=endpoints, by_tag=_group_by_tag(endpoints), variables={})
