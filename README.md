# Spectra

Spectra is an accessible OpenAPI documentation browser and REST client for blind and low-vision developers.

Swagger UI and many API tools can be difficult to use with screen readers. Spectra is designed as a keyboard-first desktop app with explicit labels, status updates, and readable text output.

## Features

- Load OpenAPI 3.x and Swagger 2.x specs from local JSON/YAML files or URLs
- Import HAR 1.2 files from browser DevTools and save them as reusable `.spectra.json` collections
- Browse endpoints grouped by tag in a keyboard-navigable tree
- Read endpoint details in text form: method, path, summary, parameters, request body, and responses
- Send requests from a built-in REST client with headers, auth, and body editing
- Review response status, headers, and pretty JSON body
- Track request history (last 50 requests) and repopulate requests quickly
- Accessibility-focused controls and keyboard shortcuts

## Installation

```bash
pip install -e .
```

Run:

```bash
spectra
```

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+O` | Open spec file |
| `Ctrl+U` | Open spec URL |
| `Ctrl+I` | Import HAR |
| `Ctrl+Enter` | Send request |
| `Ctrl+H` | Focus history |
| `Ctrl+F` | Filter endpoints |
| `F5` | Reload current spec |
| `Escape` | Clear request/response |

## Development

```bash
pip install -e .[dev]
ruff check .
pytest
```

## Contributing

Contributions are welcome. Please open an issue or pull request with:

- Accessibility impact notes
- Reproducible test steps
- Tests for behavior changes
