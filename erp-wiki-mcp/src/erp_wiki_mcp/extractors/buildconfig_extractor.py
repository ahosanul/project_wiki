"""BuildConfig extractor for Grails 2.x build configuration."""

from erp_wiki_mcp.extractors.base import ExtractorResult
from erp_wiki_mcp.registry.models import Node, RawEdge


def extract_buildconfig(ast_node: dict, file_path: str, project_id: str, last_run_id: str) -> ExtractorResult:
    """Extract Grails 2.x plugin dependencies."""
    nodes: list[Node] = []
    edges: list[RawEdge] = []
    
    plugins = ast_node.get("plugins", [])
    if not isinstance(plugins, list):
        plugins = [plugins] if plugins else []
    
    for plugin in plugins:
        plugin_name = plugin.get("name", "")
        plugin_version = plugin.get("version", "")
        plugin_line = plugin.get("line", 0)
        
        plugin_props = {
            "name": plugin_name,
            "version": plugin_version,
            "scope": plugin.get("scope", "compile"),
        }
        
        plugin_node = Node(
            id=f"{project_id}:plugin_dep:{plugin_name}",
            kind="grails_plugin_dep",
            name=plugin_name,
            fqn=plugin_name,
            file_path=file_path,
            line_start=plugin_line,
            line_end=plugin_line + 1,
            language="groovy",
            project_id=project_id,
            last_run_id=last_run_id,
            docstring=None,
            source_hash="",
            properties=plugin_props,
            grails_version="2.x",
        )
        nodes.append(plugin_node)
    
    return ExtractorResult(nodes=nodes, raw_edges=edges)
