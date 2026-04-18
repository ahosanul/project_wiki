#!/usr/bin/env python
"""Run the ERP Wiki MCP server."""
import sys
sys.path.insert(0, '/workspace/erp-wiki-mcp/src')

from erp_wiki_mcp.server import main

if __name__ == "__main__":
    main()
