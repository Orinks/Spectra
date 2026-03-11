from __future__ import annotations

import json

import pytest

from spectra.collection_store import load_collection, save_collection
from spectra.har_import import HarImportError, parse_har_document


def test_parse_har_filters_noise_and_groups_requests() -> None:
    har = {
        "log": {
            "entries": [
                {
                    "request": {
                        "method": "POST",
                        "url": "https://api.example.com/v1/users?id=42",
                        "headers": [{"name": "Content-Type", "value": "application/json"}],
                        "postData": {"text": '{"name":"Ada"}'},
                    },
                    "response": {
                        "status": 201,
                        "statusText": "Created",
                        "content": {"mimeType": "application/json; charset=utf-8"},
                    },
                },
                {
                    "request": {
                        "method": "GET",
                        "url": "https://api.example.com/assets/logo.png",
                        "headers": [],
                    },
                    "response": {
                        "status": 200,
                        "statusText": "OK",
                        "content": {"mimeType": "image/png"},
                    },
                },
            ]
        }
    }

    parsed = parse_har_document(har)

    assert len(parsed.endpoints) == 1
    endpoint = parsed.endpoints[0]
    assert endpoint.method == "POST"
    assert endpoint.url == "https://api.example.com/v1/users?id=42"
    assert endpoint.path == "/v1/users?id=42"
    assert endpoint.request_headers == {"Content-Type": "application/json"}
    assert endpoint.request_body == '{"name":"Ada"}'
    assert endpoint.tags == ["api.example.com /v1"]
    assert endpoint.responses == {"201": "Created [application/json]"}


def test_parse_har_uses_hostname_groups_when_hosts_differ() -> None:
    har = {
        "log": {
            "entries": [
                {
                    "request": {
                        "method": "GET",
                        "url": "https://one.example.com/users",
                        "headers": [],
                    },
                    "response": {
                        "status": 200,
                        "statusText": "OK",
                        "content": {"mimeType": "application/json"},
                    },
                },
                {
                    "request": {
                        "method": "GET",
                        "url": "https://two.example.com/users",
                        "headers": [],
                    },
                    "response": {
                        "status": 200,
                        "statusText": "OK",
                        "content": {"mimeType": "application/xml"},
                    },
                },
            ]
        }
    }

    parsed = parse_har_document(har)

    assert {endpoint.tags[0] for endpoint in parsed.endpoints} == {
        "one.example.com",
        "two.example.com",
    }


def test_parse_har_rejects_invalid_document() -> None:
    with pytest.raises(HarImportError):
        parse_har_document({})


def test_collection_round_trip(tmp_path) -> None:
    parsed = parse_har_document(
        {
            "log": {
                "entries": [
                    {
                        "request": {
                            "method": "POST",
                            "url": "https://api.example.com/v1/users",
                            "headers": [{"name": "Accept", "value": "application/json"}],
                            "postData": {"text": '{"name":"Ada"}'},
                        },
                        "response": {
                            "status": 200,
                            "statusText": "OK",
                            "content": {"mimeType": "application/json"},
                        },
                    }
                ]
            }
        }
    )

    target = tmp_path / "imported.spectra.json"
    save_collection(str(target), parsed)

    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["format"] == "spectra.collection"

    loaded = load_collection(str(target))
    assert loaded.endpoints[0].url == parsed.endpoints[0].url
    assert loaded.endpoints[0].request_headers == {"Accept": "application/json"}
