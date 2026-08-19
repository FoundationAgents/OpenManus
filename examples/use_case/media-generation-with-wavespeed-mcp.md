# Media generation with the WaveSpeed MCP server

OpenManus has no built-in image/video generation tool, but it can gain image,
video, audio, and 3D generation through MCP. This example connects the
[WaveSpeed](https://wavespeed.ai) MCP server (`@wavespeed/mcp`), which exposes
the live WaveSpeed model catalog with schema introspection, price quotes, and
local-file upload.

## Prerequisites

- Node.js (for `npx`)
- A WaveSpeed API key from <https://wavespeed.ai/accesskey> (user-supplied;
  pay-per-use account)

## Configuration

Create `config/config.toml` as usual, then add the server to `config/mcp.json`
(create the file from `config/mcp.example.json` if you don't have one):

```json
{
    "mcpServers": {
        "wavespeed": {
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@wavespeed/mcp"]
        }
    }
}
```

This matches the loader in `app/config.py` (`MCPSettings.load_server_config`),
which accepts `type` (`"stdio"` or `"sse"`), `command`, `args`, and `url`.

### Supplying the API key

OpenManus spawns configured stdio MCP servers with the MCP SDK's *default*
environment (only `HOME`, `PATH`, and a few other safe variables are
inherited), so an exported `WAVESPEED_API_KEY` from your shell is **not**
forwarded to the server. Use one of these instead:

1. **Recommended — log in once with the WaveSpeed CLI.** The MCP server reads
   the CLI's stored credentials (under `$HOME/.config`), which survives the
   restricted environment:

   ```bash
   npm i -g @wavespeed/cli
   wavespeed login
   ```

2. **Alternative — inline the key via `env`** in `config/mcp.json` (keep this
   file out of version control):

   ```json
   {
       "mcpServers": {
           "wavespeed": {
               "type": "stdio",
               "command": "env",
               "args": ["WAVESPEED_API_KEY=your-key-here", "npx", "-y", "@wavespeed/mcp"]
           }
       }
   }
   ```

## Run

```bash
python main.py
```

**Prompt**:

```
Generate a poster image for a lo-fi coding livestream called "Night Shift" — dark
synthwave palette, a desk with a glowing monitor, retro grid horizon. Pick a good
text-to-image model, check its price first, then save the resulting image URL to
poster.md in the workspace.
```

**Expected flow** — the agent receives the server's tools prefixed with the
server id (`mcp_wavespeed_*`) and typically:

1. `mcp_wavespeed_list_models` — searches the live catalog for a text-to-image
   model.
2. `mcp_wavespeed_get_model_schema` — fetches the chosen model's real input
   schema (sizes, defaults, required fields).
3. `mcp_wavespeed_get_price` — quotes the cost of the run before executing.
4. `mcp_wavespeed_run_model` — runs the generation and returns hosted output
   URLs.
5. Writes `poster.md` with the image URL via the file tool.

The same flow works for video, audio (TTS/music), and 3D models — just ask for
them; the catalog search in step 1 covers all modalities. Image-to-image and
image-to-video tasks can reference local files as `"@./path"` input values,
which the server uploads automatically.
