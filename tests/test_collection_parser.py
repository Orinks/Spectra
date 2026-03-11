from __future__ import annotations

import json
from pathlib import Path

import pytest

from spectra.collection_parser import collection_to_dict, load_collection, parse_collection
from spectra.spec_loader import SpecLoaderError
from spectra.spec_parser import Endpoint, Parameter


def test_parse_collection_basic() -> None:
    document = {
        "name": "Weather",
        "baseUrl": "https://weather.example.com",
        "groups": [
            {
                "name": "Timeline",
                "endpoints": [
                    {
                        "method": "GET",
                        "path": "/timeline/{location}",
                        "summary": "Forecast",
                        "description": "Get a forecast",
                        "parameters": [
                            {
                                "name": "location",
                                "in": "path",
                                "required": True,
                                "type": "string",
                                "description": "Location slug",
                            }
                        ],
                        "requestBodyExample": '{"unit":"metric"}',
                    }
                ],
            }
        ],
    }

    parsed = parse_collection(document)

    assert parsed.name == "Weather"
    assert parsed.base_url == "https://weather.example.com"
    assert list(parsed.by_tag) == ["Timeline"]
    endpoint = parsed.endpoints[0]
    assert endpoint.tags == ["Timeline"]
    assert endpoint.example_body == '{"unit":"metric"}'
    assert endpoint.parameters[0].description == "Location slug"


def test_collection_to_dict_round_trip() -> None:
    by_tag = {
        "Timeline": [
            Endpoint(
                method="POST",
                path="/timeline",
                summary="Create timeline",
                description="Create one",
                tags=["Timeline"],
                parameters=[
                    Parameter(
                        name="key",
                        location="query",
                        required=True,
                        schema="string",
                        description="API key",
                    )
                ],
                example_body='{"days":5}',
                request_body='{"days":5}',
            )
        ]
    }

    document = collection_to_dict("Weather", "https://weather.example.com", by_tag)
    parsed = parse_collection(document)

    assert parsed.name == "Weather"
    assert parsed.endpoints[0].method == "POST"
    assert parsed.endpoints[0].parameters[0].schema == "string"
    assert parsed.endpoints[0].example_body == '{"days":5}'


def test_load_collection_from_file(tmp_path: Path) -> None:
    path = tmp_path / "weather.spectra.json"
    document = {
        "name": "Weather",
        "baseUrl": "",
        "groups": [{"name": "One", "endpoints": []}],
    }
    path.write_text(
        json.dumps(document),
        encoding="utf-8",
    )

    parsed = load_collection(str(path))

    assert parsed.name == "Weather"
    assert parsed.by_tag["One"] == []


def test_parse_collection_invalid_groups_raises() -> None:
    with pytest.raises(SpecLoaderError, match="groups"):
        parse_collection({"name": "Weather", "groups": "bad"})


def test_load_collection_invalid_json_raises(tmp_path: Path) -> None:
    path = tmp_path / "broken.spectra.json"
    path.write_text("{", encoding="utf-8")

    with pytest.raises(SpecLoaderError, match="Invalid collection JSON"):
        load_collection(str(path))
