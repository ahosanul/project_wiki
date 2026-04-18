#!/usr/bin/env python
"""Quick test of the MCP server modules."""
import sys
sys.path.insert(0, '/workspace/erp-wiki-mcp/src')

print("Testing imports...")
from erp_wiki_mcp.config import settings
print(f"✓ Config loaded: data_dir={settings.data_dir}")

from erp_wiki_mcp.registry.db import RegistryDB
print(f"✓ RegistryDB imported")

from erp_wiki_mcp.tools.index_project import index_project
print(f"✓ index_project imported")

from erp_wiki_mcp.tools.status import get_status
print(f"✓ status imported")

from erp_wiki_mcp.server import create_server
print(f"✓ Server created")

server = create_server()
print(f"✓ Server name: {server.name}")
print(f"\n✅ All modules loaded successfully!")
print(f"\nTo run the server:")
print(f"  PYTHONPATH=/workspace/erp-wiki-mcp/src:$PYTHONPATH python -m erp_wiki_mcp.server")
print(f"\nOr use the wrapper script:")
print(f"  ./run_server.py")
