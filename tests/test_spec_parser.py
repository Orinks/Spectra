from __future__ import annotations

from spectra.spec_parser import parse_spec


def test_parse_openapi_endpoint_basic() -> None:
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/users": {
                "get": {
                    "summary": "List users",
                    "description": "Returns users",
                    "tags": ["users"],
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
    }

    parsed = parse_spec(spec)

    assert len(parsed.endpoints) == 1
    endpoint = parsed.endpoints[0]
    assert endpoint.method == "GET"
    assert endpoint.path == "/users"
    assert endpoint.summary == "List users"
    assert endpoint.tags == ["users"]


def test_group_by_tag_multiple() -> None:
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/u": {"get": {"tags": ["users"], "responses": {"200": {"description": "OK"}}}},
            "/a": {"get": {"tags": ["admin"], "responses": {"200": {"description": "OK"}}}},
        },
    }

    parsed = parse_spec(spec)

    assert set(parsed.by_tag) == {"users", "admin"}


def test_missing_tag_fallback_default() -> None:
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/u": {"get": {"responses": {"200": {"description": "OK"}}}},
        },
    }

    parsed = parse_spec(spec)

    assert "default" in parsed.by_tag
    assert parsed.by_tag["default"][0].path == "/u"


def test_parse_parameters_path_and_operation() -> None:
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/u/{id}": {
                "parameters": [
                    {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}
                ],
                "get": {
                    "parameters": [
                        {
                            "name": "expand",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "boolean"},
                        }
                    ],
                    "responses": {"200": {"description": "OK"}},
                },
            }
        },
    }

    endpoint = parse_spec(spec).endpoints[0]

    assert len(endpoint.parameters) == 2
    assert endpoint.parameters[0].name == "id"
    assert endpoint.parameters[0].schema == "string"
    assert endpoint.parameters[1].name == "expand"


def test_operation_parameter_overrides_matching_path_parameter() -> None:
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/u/{id}": {
                "parameters": [
                    {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}},
                    {"name": "expand", "in": "query", "schema": {"type": "boolean"}},
                ],
                "get": {
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"},
                        }
                    ],
                    "responses": {"200": {"description": "OK"}},
                },
            }
        },
    }

    endpoint = parse_spec(spec).endpoints[0]

    assert len(endpoint.parameters) == 2
    assert [(parameter.name, parameter.location) for parameter in endpoint.parameters] == [
        ("id", "path"),
        ("expand", "query"),
    ]
    assert endpoint.parameters[0].schema == "integer"


def test_parse_openapi_request_body() -> None:
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/u": {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {"name": {"type": "string"}},
                                }
                            }
                        }
                    },
                    "responses": {"201": {"description": "Created"}},
                }
            }
        },
    }

    endpoint = parse_spec(spec).endpoints[0]

    assert "application/json" in endpoint.request_body
    assert "object{name}" in endpoint.request_body


def test_parse_responses_with_content_schema() -> None:
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/u": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "array", "items": {"type": "string"}}
                                }
                            },
                        }
                    }
                }
            }
        },
    }

    endpoint = parse_spec(spec).endpoints[0]

    assert "application/json=array[string]" in endpoint.responses["200"]


def test_parse_paths_missing_returns_empty() -> None:
    parsed = parse_spec({"openapi": "3.0.0"})

    assert parsed.endpoints == []
    assert parsed.by_tag == {}


def test_parse_swagger2_endpoint() -> None:
    spec = {
        "swagger": "2.0",
        "paths": {"/pets": {"get": {"responses": {"200": {"description": "OK"}}}}},
    }

    endpoint = parse_spec(spec).endpoints[0]

    assert endpoint.method == "GET"
    assert endpoint.path == "/pets"


def test_parse_swagger2_body_parameter() -> None:
    spec = {
        "swagger": "2.0",
        "paths": {
            "/pets": {
                "post": {
                    "parameters": [
                        {"in": "body", "name": "body", "schema": {"$ref": "#/definitions/Pet"}}
                    ],
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
    }

    endpoint = parse_spec(spec).endpoints[0]

    assert endpoint.request_body == "#/definitions/Pet"


def test_parse_ignores_non_method_keys() -> None:
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/u": {
                "parameters": [],
                "summary": "ignore",
                "get": {"responses": {"200": {"description": "OK"}}},
            }
        },
    }

    parsed = parse_spec(spec)

    assert len(parsed.endpoints) == 1


def test_parse_multiple_methods_same_path() -> None:
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/u": {
                "get": {"responses": {"200": {"description": "OK"}}},
                "post": {"responses": {"201": {"description": "Created"}}},
            }
        },
    }

    parsed = parse_spec(spec)

    assert len(parsed.endpoints) == 2
    assert {e.method for e in parsed.endpoints} == {"GET", "POST"}


def test_parse_parameter_type_fallback() -> None:
    spec = {
        "swagger": "2.0",
        "paths": {
            "/u": {
                "get": {
                    "parameters": [{"name": "limit", "in": "query", "type": "integer"}],
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
    }

    endpoint = parse_spec(spec).endpoints[0]

    assert endpoint.parameters[0].schema == "integer"


def test_parse_ref_schema_parameter() -> None:
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/u": {
                "get": {
                    "parameters": [
                        {
                            "name": "filter",
                            "in": "query",
                            "schema": {"$ref": "#/components/schemas/F"},
                        }
                    ],
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
    }

    endpoint = parse_spec(spec).endpoints[0]

    assert endpoint.parameters[0].schema == "#/components/schemas/F"


def test_parse_postman_collection_groups_by_folder_and_prefill_fields() -> None:
    spec = {
        "info": {
            "name": "Weather",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "variable": [{"key": "baseUrl", "value": "https://api.example.com"}],
        "item": [
            {
                "name": "Forecast",
                "item": [
                    {
                        "name": "Get Forecast",
                        "request": {
                            "method": "GET",
                            "header": [{"key": "Accept", "value": "application/json"}],
                            "url": {
                                "raw": "{{baseUrl}}/forecast?days=5",
                                "path": ["forecast"],
                                "query": [{"key": "days", "value": "5"}],
                            },
                        },
                    }
                ],
            }
        ],
    }

    parsed = parse_spec(spec)

    assert parsed.variables == {"baseUrl": "https://api.example.com"}
    assert set(parsed.by_tag) == {"Forecast"}
    endpoint = parsed.by_tag["Forecast"][0]
    assert endpoint.method == "GET"
    assert endpoint.path == "/forecast?days=5"
    assert endpoint.request_url == "{{baseUrl}}/forecast?days=5"
    assert endpoint.request_headers == {"Accept": "application/json"}


def test_parse_postman_collection_body_and_nested_folder_name() -> None:
    spec = {
        "info": {
            "name": "Demo",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "item": [
            {
                "name": "Admin",
                "item": [
                    {
                        "name": "Users",
                        "item": [
                            {
                                "name": "Create User",
                                "request": {
                                    "method": "POST",
                                    "body": {
                                        "mode": "raw",
                                        "raw": '{"name":"{{userName}}"}',
                                    },
                                    "url": "https://api.example.com/users",
                                },
                            }
                        ],
                    }
                ],
            }
        ],
    }

    endpoint = parse_spec(spec).endpoints[0]

    assert endpoint.tags == ["Admin / Users"]
    assert endpoint.request_body == '{"name":"{{userName}}"}'
    assert endpoint.request_body_text == '{"name":"{{userName}}"}'
