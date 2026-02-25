"""Parsers for OpenAPI and Swagger endpoint metadata."""

from __future__ import annotations

from dataclasses import dataclass, field

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


@dataclass(slots=True)
class ParsedSpec:
    endpoints: list[Endpoint]
    by_tag: dict[str, list[Endpoint]]


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


def _group_by_tag(endpoints: list[Endpoint]) -> dict[str, list[Endpoint]]:
    by_tag: dict[str, list[Endpoint]] = {}
    for endpoint in endpoints:
        tags = endpoint.tags or ["default"]
        for tag in tags:
            by_tag.setdefault(tag, []).append(endpoint)
    return by_tag


def parse_spec(spec: dict) -> ParsedSpec:
    """Parse an OpenAPI 3.x or Swagger 2.x spec to endpoint metadata."""
    paths = spec.get("paths")
    if not isinstance(paths, dict):
        return ParsedSpec(endpoints=[], by_tag={})

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

            merged_parameters = [*path_parameters, *op_parameters]
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
            )
            endpoints.append(endpoint)

    return ParsedSpec(endpoints=endpoints, by_tag=_group_by_tag(endpoints))
