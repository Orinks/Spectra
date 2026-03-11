"""HAR import helpers."""

from __future__ import annotations

import json
from collections import Counter
from urllib.parse import urlparse

from spectra.spec_parser import Endpoint, ParsedSpec

SUPPORTED_RESPONSE_TYPES = ("application/json", "application/xml", "text/xml")


class HarImportError(ValueError):
    """Raised when a HAR file cannot be parsed."""


def _normalize_media_type(value: str) -> str:
    media_type = value.split(";", 1)[0].strip().lower()
    if media_type.endswith("+json") or media_type.endswith("+xml"):
        return media_type
    return media_type


def _is_supported_response(entry: dict) -> bool:
    response = entry.get("response")
    if not isinstance(response, dict):
        return False

    content = response.get("content")
    mime_type = ""
    if isinstance(content, dict):
        mime_type = str(content.get("mimeType", ""))
    if not mime_type:
        headers = response.get("headers")
        if isinstance(headers, list):
            for header in headers:
                if not isinstance(header, dict):
                    continue
                if str(header.get("name", "")).lower() == "content-type":
                    mime_type = str(header.get("value", ""))
                    break

    normalized = _normalize_media_type(mime_type)
    return bool(normalized) and (
        normalized in SUPPORTED_RESPONSE_TYPES
        or normalized.endswith("+json")
        or normalized.endswith("+xml")
    )


def _headers_to_dict(headers: object) -> dict[str, str]:
    result: dict[str, str] = {}
    if not isinstance(headers, list):
        return result
    for header in headers:
        if not isinstance(header, dict):
            continue
        name = str(header.get("name", "")).strip()
        if not name:
            continue
        result[name] = str(header.get("value", "")).strip()
    return result


def _group_for_url(url: str, host_counts: Counter[str]) -> str:
    parsed = urlparse(url)
    host = parsed.netloc or "captured"
    segments = [segment for segment in parsed.path.split("/") if segment]

    if len(host_counts) > 1:
        return host
    if segments:
        return f"{host} /{segments[0]}"
    return host


def parse_har_document(document: dict) -> ParsedSpec:
    log = document.get("log")
    if not isinstance(log, dict):
        raise HarImportError("HAR document is missing a log object")

    raw_entries = log.get("entries")
    if not isinstance(raw_entries, list):
        raise HarImportError("HAR document is missing log.entries")

    supported_entries = [
        entry
        for entry in raw_entries
        if isinstance(entry, dict) and _is_supported_response(entry)
    ]
    host_counts = Counter(
        urlparse(str(entry.get("request", {}).get("url", ""))).netloc
        for entry in supported_entries
    )

    endpoints: list[Endpoint] = []
    by_tag: dict[str, list[Endpoint]] = {}

    for entry in supported_entries:
        request = entry.get("request")
        response = entry.get("response")
        if not isinstance(request, dict) or not isinstance(response, dict):
            continue

        url = str(request.get("url", "")).strip()
        method = str(request.get("method", "GET")).upper()
        if not url or not method:
            continue

        parsed_url = urlparse(url)
        path = parsed_url.path or "/"
        query = f"?{parsed_url.query}" if parsed_url.query else ""
        response_content = response.get("content")
        response_type = ""
        if isinstance(response_content, dict):
            response_type = _normalize_media_type(str(response_content.get("mimeType", "")))

        post_data = request.get("postData")
        body = ""
        if isinstance(post_data, dict):
            body = str(post_data.get("text", ""))

        group = _group_for_url(url, host_counts)
        endpoint = Endpoint(
            method=method,
            path=f"{path}{query}",
            url=url,
            summary=f"Imported from HAR: {parsed_url.netloc or 'captured request'}",
            description="Captured HTTP request",
            tags=[group],
            request_headers=_headers_to_dict(request.get("headers")),
            request_body=body,
            responses={
                str(response.get("status", "")): " ".join(
                    part
                    for part in [
                        str(response.get("statusText", "")).strip(),
                        f"[{response_type}]" if response_type else "",
                    ]
                    if part
                ).strip()
            },
        )
        endpoints.append(endpoint)
        by_tag.setdefault(group, []).append(endpoint)

    return ParsedSpec(endpoints=endpoints, by_tag=by_tag)


def load_har_file(path: str) -> ParsedSpec:
    try:
        with open(path, encoding="utf-8") as handle:
            document = json.load(handle)
    except FileNotFoundError as exc:
        raise HarImportError(f"HAR file not found: {path}") from exc
    except OSError as exc:
        raise HarImportError(f"Unable to read HAR file {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise HarImportError(f"Invalid HAR JSON in {path}: {exc.msg}") from exc

    return parse_har_document(document)
