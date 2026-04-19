# mcp-server-card-demo

A tiny, stdlib-only Python CLI that illustrates **MCP v2.1 Server Cards**:
structured capability metadata served from a `.well-known` URL so that
agent hosts, registries, and browsers can discover an MCP server's tools
without opening a live JSON-RPC session.

The 2026 MCP roadmap pushes hard on stateless, scalable discovery: a
server should be able to describe itself through a cacheable static
document instead of requiring every potential consumer to connect and
send `tools/list`. This demo is a pedagogical take on that idea.

> The field set here is **illustrative**, modelled on the public 2026
> MCP roadmap discussion of `.well-known` discovery metadata. Treat it
> as a conceptual reference, not the canonical spec.

## What's included

- `mcp_card.py` — a single-file CLI with three subcommands:
  - `serve` — expose a demo Server Card at
    `/.well-known/mcp-server-card.json`
  - `discover` — fetch and pretty-print a Server Card from any base URL
  - `validate` — structurally validate a Server Card JSON document
- `sample_card.json` — an example card used for offline validation

No third-party dependencies. Runs on any Python 3.9+.

## Why it matters

With Claude Desktop and Cursor both shipping MCP v2.1 support in
April 2026, tool discovery is moving from "connect and ask" to
"GET a well-known URL". Small self-describing servers are cheap to
deploy, cache-friendly, and trivially crawlable by registries. This
demo shows the end-to-end loop (serve → discover → validate) in
around 200 lines of pure stdlib Python.

## Quickstart

```sh
# 1. Start the demo server in one terminal
python3 mcp_card.py serve --port 8765

# 2. In another terminal, discover it
python3 mcp_card.py discover http://127.0.0.1:8765

# 3. Validate the bundled sample card offline
python3 mcp_card.py validate sample_card.json

# 4. Or fetch the raw JSON
python3 mcp_card.py discover http://127.0.0.1:8765 --raw
```

Expected `discover` output:

```
name            : demo-weather-server
version         : 0.1.0
protocol_version: 2.1
description     : Illustrative MCP v2.1 demo server ...
capabilities    : tools, resources, logging, streamable_http
tools (2):
  - get_current_weather: Return fake current weather for a city.
      inputs: city, units
  - get_forecast: Return a fake 3-day forecast for a city.
      inputs: city
resources (1):
  - demo://readme (text/plain)
```

## Card shape (illustrative)

```json
{
  "name": "demo-weather-server",
  "version": "0.1.0",
  "protocol_version": "2.1",
  "description": "...",
  "capabilities": {
    "tools": true,
    "resources": true,
    "prompts": false,
    "logging": true,
    "streamable_http": true
  },
  "endpoints": {"jsonrpc": "/rpc", "sse": null},
  "tools": [
    {
      "name": "get_current_weather",
      "description": "...",
      "input_schema": {"type": "object", "properties": {...}, "required": [...]}
    }
  ],
  "resources": [{"uri": "demo://readme", "name": "...", "mime_type": "text/plain"}]
}
```

The validator checks for the top-level required fields
(`name`, `version`, `protocol_version`, `tools`), confirms
`protocol_version` starts with `2.`, and walks each tool for
`name`, `description`, and `input_schema`.

## Sources

Research that informed this demo:

- 2026 MCP Roadmap — <https://blog.modelcontextprotocol.io/posts/2026-mcp-roadmap/>
- MCP protocol roadmap index — <https://modelcontextprotocol.io/development/roadmap>
- MCP ecosystem status, April 2026 — <https://thenewstack.io/model-context-protocol-roadmap-2026/>
- AI Weekly: Agents, Models, and Chips (April 9–15, 2026) — <https://dev.to/alexmercedcoder/ai-weekly-agents-models-and-chips-april-9-15-2026-486f>

## License

MIT. See `LICENSE`.
