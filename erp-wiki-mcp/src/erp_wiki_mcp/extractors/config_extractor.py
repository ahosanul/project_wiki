"""Config extractor with secret redaction."""

import re
from erp_wiki_mcp.extractors.base import ExtractorResult
from erp_wiki_mcp.registry.models import Node, RawEdge

SECRET_PATTERNS = [
    r'.*password.*',
    r'.*secret.*',
    r'.*token.*',
    r'.*apikey.*',
    r'.*api_key.*',
    r'.*credential.*',
]


def is_secret_key(key: str) -> bool:
    """Check if key matches secret patterns (case-insensitive)."""
    key_lower = key.lower()
    for pattern in SECRET_PATTERNS:
        if re.match(pattern, key_lower):
            return True
    return False


def flatten_dict(d: dict, parent_key: str = '', sep: str = '.') -> dict:
    """Flatten nested dict to dot-notation keys."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def extract_config(config_data: dict, file_path: str, project_id: str, last_run_id: str) -> ExtractorResult:
    """Extract config key nodes with secret redaction."""
    nodes: list[Node] = []
    edges: list[RawEdge] = []
    
    flattened = flatten_dict(config_data)
    
    for key, value in flattened.items():
        is_redacted = is_secret_key(key)
        stored_value = "[REDACTED]" if is_redacted else str(value)
        
        config_props = {
            "value": stored_value,
            "is_redacted": is_redacted,
            "original_type": type(value).__name__,
        }
        
        config_node = Node(
            id=f"{project_id}:config_key:{key}",
            kind="config_key",
            name=key.split(".")[-1],
            fqn=key,
            file_path=file_path,
            line_start=0,
            line_end=0,
            language="yaml" if file_path.endswith((".yml", ".yaml")) else "groovy",
            project_id=project_id,
            last_run_id=last_run_id,
            docstring=None,
            source_hash="",
            properties=config_props,
            grails_version=None,
        )
        nodes.append(config_node)
    
    return ExtractorResult(nodes=nodes, raw_edges=edges)
