"""mcp-server-card-demo

Pedagogical, stdlib-only Python CLI illustrating MCP v2.1 Server Cards:
a structured-metadata descriptor served from a well-known URL so that
browsers, registries, and agent hosts can discover an MCP server's
capabilities without opening a live session.

Subcommands:
    serve    - expose a demo Server Card at /.well-known/mcp-server-card.json
    discover - fetch and pretty-print a Server Card from any base URL
    validate - structurally validate a Server Card JSON document

The schema below is illustrative and based on the public 2026 MCP roadmap
discussion of .well-known discovery metadata. Treat field names as
representative, not canonical.
"""

from __future__ import annotations

import argparse
import json
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

WELL_KNOWN_PATH = "/.well-known/mcp-server-card.json"
PROTOCOL_VERSION = "2.1"

REQUIRED_TOP_LEVEL = ("name", "version", "protocol_version", "tools")
REQUIRED_TOOL_FIELDS = ("name", "description", "input_schema")


def demo_card() -> dict[str, Any]:
    """Return an illustrative Server Card for the built-in demo server."""
    return {
        "name": "demo-weather-server",
        "version": "0.1.0",
        "protocol_version": PROTOCOL_VERSION,
        "description": (
            "Illustrative MCP v2.1 demo server: exposes two weather tools "
            "and a static resource. Not connected to any live data source."
        ),
        "vendor": {
            "name": "mcp-server-card-demo",
            "url": "https://github.com/",
        },
        "capabilities": {
            "tools": True,
            "resources": True,
            "prompts": False,
            "logging": True,
            "streamable_http": True,
        },
        "endpoints": {
            "jsonrpc": "/rpc",
            "sse": None,
        },
        "tools": [
            {
                "name": "get_current_weather",
                "description": "Return fake current weather for a city.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string"},
                        "units": {"type": "string", "enum": ["c", "f"]},
                    },
                    "required": ["city"],
                },
            },
            {
                "name": "get_forecast",
                "description": "Return a fake 3-day forecast for a city.",
                "input_schema": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                    "required": ["city"],
                },
            },
        ],
        "resources": [
            {
                "uri": "demo://readme",
                "name": "About this demo server",
                "mime_type": "text/plain",
            }
        ],
    }


class CardHandler(BaseHTTPRequestHandler):
    """Serve a Server Card at the well-known path; 404 otherwise."""

    card_body: bytes = b""

    def do_GET(self) -> None:  # noqa: N802 (stdlib naming)
        if self.path == WELL_KNOWN_PATH:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(self.card_body)))
            self.send_header("Cache-Control", "public, max-age=300")
            self.end_headers()
            self.wfile.write(self.card_body)
            return
        self.send_response(HTTPStatus.NOT_FOUND)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Not found. Try " + WELL_KNOWN_PATH.encode())

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("[mcp-card] %s\n" % (fmt % args))


def cmd_serve(args: argparse.Namespace) -> int:
    card = demo_card()
    CardHandler.card_body = json.dumps(card, indent=2).encode("utf-8")
    httpd = HTTPServer((args.host, args.port), CardHandler)
    url = f"http://{args.host}:{args.port}{WELL_KNOWN_PATH}"
    print(f"Serving Server Card at {url}", file=sys.stderr)
    print("Press Ctrl+C to stop.", file=sys.stderr)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.", file=sys.stderr)
    finally:
        httpd.server_close()
    return 0


def fetch_card(base_url: str, timeout: float) -> dict[str, Any]:
    url = urljoin(base_url if base_url.endswith("/") else base_url + "/", WELL_KNOWN_PATH.lstrip("/"))
    req = Request(url, headers={"Accept": "application/json"})
    with urlopen(req, timeout=timeout) as resp:
        payload = resp.read()
    return json.loads(payload.decode("utf-8"))


def print_card(card: dict[str, Any]) -> None:
    print(f"name            : {card.get('name')}")
    print(f"version         : {card.get('version')}")
    print(f"protocol_version: {card.get('protocol_version')}")
    desc = card.get("description") or ""
    print(f"description     : {desc}")
    caps = card.get("capabilities") or {}
    if caps:
        flags = ", ".join(k for k, v in caps.items() if v)
        print(f"capabilities    : {flags or '(none)'}")
    tools = card.get("tools") or []
    print(f"tools ({len(tools)}):")
    for t in tools:
        print(f"  - {t.get('name')}: {t.get('description')}")
        props = (t.get("input_schema") or {}).get("properties") or {}
        if props:
            fields = ", ".join(sorted(props.keys()))
            print(f"      inputs: {fields}")
    resources = card.get("resources") or []
    if resources:
        print(f"resources ({len(resources)}):")
        for r in resources:
            print(f"  - {r.get('uri')} ({r.get('mime_type', 'unknown')})")


def cmd_discover(args: argparse.Namespace) -> int:
    try:
        card = fetch_card(args.base_url, args.timeout)
    except HTTPError as e:
        print(f"HTTP error {e.code} fetching card: {e.reason}", file=sys.stderr)
        return 2
    except URLError as e:
        print(f"Network error: {e.reason}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as e:
        print(f"Card is not valid JSON: {e}", file=sys.stderr)
        return 2
    if args.raw:
        json.dump(card, sys.stdout, indent=2)
        print()
    else:
        print_card(card)
    errors = validate_card(card)
    if errors:
        print("\nValidation warnings:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
    return 0


def validate_card(card: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(card, dict):
        return ["card is not a JSON object"]
    for field in REQUIRED_TOP_LEVEL:
        if field not in card:
            errors.append(f"missing required field: {field}")
    proto = card.get("protocol_version")
    if proto is not None and not str(proto).startswith("2."):
        errors.append(f"unexpected protocol_version: {proto!r} (want 2.x)")
    tools = card.get("tools")
    if isinstance(tools, list):
        for i, tool in enumerate(tools):
            if not isinstance(tool, dict):
                errors.append(f"tools[{i}] is not an object")
                continue
            for tf in REQUIRED_TOOL_FIELDS:
                if tf not in tool:
                    errors.append(f"tools[{i}] missing field: {tf}")
    elif tools is not None:
        errors.append("tools must be a list")
    return errors


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        with open(args.path, encoding="utf-8") as f:
            card = json.load(f)
    except OSError as e:
        print(f"Cannot open {args.path}: {e}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in {args.path}: {e}", file=sys.stderr)
        return 2
    errors = validate_card(card)
    if errors:
        print(f"FAIL: {len(errors)} issue(s) in {args.path}")
        for err in errors:
            print(f"  - {err}")
        return 1
    print(f"OK: {args.path} looks like a valid MCP v{PROTOCOL_VERSION} Server Card.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mcp-card",
        description="Serve, discover, and validate MCP v2.1 Server Cards.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    ps = sub.add_parser("serve", help="serve a demo Server Card over HTTP")
    ps.add_argument("--host", default="127.0.0.1")
    ps.add_argument("--port", type=int, default=8765)
    ps.set_defaults(func=cmd_serve)

    pd = sub.add_parser("discover", help="fetch a Server Card from a base URL")
    pd.add_argument("base_url", help="e.g. http://127.0.0.1:8765")
    pd.add_argument("--timeout", type=float, default=5.0)
    pd.add_argument("--raw", action="store_true", help="print raw JSON")
    pd.set_defaults(func=cmd_discover)

    pv = sub.add_parser("validate", help="validate a Server Card JSON file")
    pv.add_argument("path")
    pv.set_defaults(func=cmd_validate)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
