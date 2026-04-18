# Running ERP Wiki MCP Server on Linux

## Prerequisites

- Python 3.11+ (tested with Python 3.12)
- pip package manager

## Installation

### 1. Install Required Python Packages

```bash
# Install core dependencies (system-wide or in virtualenv)
pip install --no-cache-dir \
    mcp \
    tree-sitter \
    tree-sitter-java \
    beautifulsoup4 \
    lxml \
    kuzu \
    aiosqlite \
    blake3 \
    PyYAML \
    pydantic-settings \
    structlog \
    gitignore-parser
```

### 2. Set Environment Variables (Optional)

Create a `.env` file or export variables:

```bash
export MCP_DATA_DIR=~/.erp-wiki-mcp/data
export MCP_LOG_LEVEL=INFO
export MCP_MAX_PARSE_WORKERS=4
export MCP_MAX_FILE_SIZE_MB=5
```

## Running the Server

The server uses the **MCP (Model Context Protocol)** and communicates via **stdio**. It's designed to be used with MCP clients like Claude Desktop.

### Option 1: Direct Execution

```bash
cd /workspace/erp-wiki-mcp
PYTHONPATH=/workspace/erp-wiki-mcp/src:$PYTHONPATH python -m erp_wiki_mcp.server
```

### Option 2: Using Wrapper Script

```bash
cd /workspace/erp-wiki-mcp
python run_server.py
```

### Option 3: As MCP Client Subprocess

Configure your MCP client (e.g., Claude Desktop) to spawn the server:

```json
{
  "mcpServers": {
    "erp-wiki-mcp": {
      "command": "python",
      "args": ["-m", "erp_wiki_mcp.server"],
      "cwd": "/workspace/erp-wiki-mcp",
      "env": {
        "PYTHONPATH": "/workspace/erp-wiki-mcp/src"
      }
    }
  }
}
```

## Testing the Installation

Run the test script to verify all modules load correctly:

```bash
cd /workspace/erp-wiki-mcp
python test_server.py
```

Expected output:
```
Testing imports...
✓ Config loaded: data_dir=~/.local/share/erp-wiki-mcp
✓ RegistryDB imported
✓ index_project imported
✓ status imported
✓ Server created
✓ Server name: erp-wiki-mcp

✅ All modules loaded successfully!
```

## Available MCP Tools

Once running, the server provides these tools:

1. **index_project** - Index a Grails/Java project
   - `path`: Project root directory (required)
   - `mode`: auto | full | dry_run (default: dry_run)
   - `scope`: full | file:<path> | module:<dir> | api:<controller> | view:<gsp>

2. **status** - Get indexing status
   - `run_id`: Run ID to query
   - `project_id`: Project ID to query

## Example Usage

### Dry Run (No Writes)

```json
{
  "tool": "index_project",
  "arguments": {
    "path": "/path/to/grails/project",
    "mode": "dry_run",
    "scope": "full"
  }
}
```

### Full Index

```json
{
  "tool": "index_project",
  "arguments": {
    "path": "/path/to/grails/project",
    "mode": "auto",
    "scope": "full"
  }
}
```

### Check Status

```json
{
  "tool": "status",
  "arguments": {
    "project_id": "your-project-id"
  }
}
```

## Troubleshooting

### Module Not Found Errors

Ensure PYTHONPATH is set:
```bash
export PYTHONPATH=/workspace/erp-wiki-mcp/src:$PYTHONPATH
```

### Disk Space Issues

The server needs space for:
- KuzuDB graph database
- Chroma vector store
- SQLite registry

Default location: `~/.local/share/erp-wiki-mcp`

Change with `MCP_DATA_DIR` environment variable.

### Groovy Parsing (Optional)

For Groovy/Grails projects, you'll need:
- Groovy 3.x installed
- Set `MCP_GROOVY_EXECUTABLE=groovy` (or full path)

## Current Implementation Status

This is a **Milestone M1 (Skeleton)** implementation:
- ✅ MCP server process boots
- ✅ `index_project` and `status` tools wired
- ✅ SQLite registry schema
- ✅ File scanner + classifier
- ✅ Hash gate (BLAKE3 diff)
- ✅ `dry_run` mode

Full Java/Groovy parsing, graph storage, and RAG features are planned for future milestones.
