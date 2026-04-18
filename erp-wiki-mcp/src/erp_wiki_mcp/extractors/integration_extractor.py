"""Integration extractor for external service detection."""

from erp_wiki_mcp.extractors.base import ExtractorResult
from erp_wiki_mcp.registry.models import Node, RawEdge


def extract_integrations(ast_node: dict, file_path: str, project_id: str, last_run_id: str) -> ExtractorResult:
    """Extract external HTTP, RabbitMQ, Camel, and cache integrations."""
    nodes: list[Node] = []
    edges: list[RawEdge] = []
    
    # Process methods for integration patterns
    for cls in ast_node.get("classes", []):
        class_fqn = cls.get("fqn", cls.get("name", ""))
        
        for method in cls.get("methods", []):
            method_name = method.get("name", "")
            method_line = method.get("line", 0)
            
            body = method.get("body", {})
            statements = body.get("statements", []) if isinstance(body, dict) else []
            
            for stmt in statements:
                stmt_type = stmt.get("type", "")
                line = stmt.get("line", method_line)
                
                # External HTTP calls
                if stmt_type in ("restTemplate_call", "url_text", "httpBuilder_call", "webClient_call"):
                    url_hint = stmt.get("url_hint", "")
                    config_key = stmt.get("config_key")
                    
                    if config_key:
                        ext_node = Node(
                            id=f"{project_id}:external_http:{url_hint or method_name}_{line}",
                            kind="external_http",
                            name=url_hint.split("/")[-1] if url_hint else method_name,
                            fqn=url_hint,
                            file_path=file_path,
                            line_start=line,
                            line_end=line,
                            language="java" if "java" in file_path else "groovy",
                            project_id=project_id,
                            last_run_id=last_run_id,
                            docstring=None,
                            source_hash="",
                            properties={
                                "url_hint": url_hint,
                                "config_key_hint": config_key,
                                "method": stmt.get("http_method", "GET"),
                            },
                            grails_version=None,
                        )
                    else:
                        ext_node = Node(
                            id=f"{project_id}:external_http:{url_hint or method_name}_{line}",
                            kind="external_http",
                            name=url_hint.split("/")[-1] if url_hint else method_name,
                            fqn=url_hint,
                            file_path=file_path,
                            line_start=line,
                            line_end=line,
                            language="java" if "java" in file_path else "groovy",
                            project_id=project_id,
                            last_run_id=last_run_id,
                            docstring=None,
                            source_hash="",
                            properties={
                                "url_hint": url_hint or f"variable:{stmt.get('var_name', 'unknown')}",
                                "method": stmt.get("http_method", "GET"),
                            },
                            grails_version=None,
                        )
                    nodes.append(ext_node)
                    
                    source_id = f"{project_id}:method:{class_fqn}#{method_name}"
                    edges.append(RawEdge(
                        source_id=source_id,
                        target_id=ext_node.id,
                        target_hint="",
                        type="CALLS_EXTERNAL",
                        file_path=file_path,
                        line=line,
                        confidence="LIKELY" if not url_hint else "EXACT",
                        extractor="integration_extractor",
                    ))
                
                # RabbitMQ publish
                elif stmt_type == "rabbitmq_publish":
                    exchange = stmt.get("exchange", "")
                    queue = stmt.get("queue", "")
                    
                    mq_node = Node(
                        id=f"{project_id}:mq_exchange:{exchange}",
                        kind="mq_exchange",
                        name=exchange,
                        fqn=exchange,
                        file_path=file_path,
                        line_start=line,
                        line_end=line,
                        language="java" if "java" in file_path else "groovy",
                        project_id=project_id,
                        last_run_id=last_run_id,
                        docstring=None,
                        source_hash="",
                        properties={"type": stmt.get("exchange_type", "topic")},
                        grails_version=None,
                    )
                    nodes.append(mq_node)
                    
                    source_id = f"{project_id}:method:{class_fqn}#{method_name}"
                    edges.append(RawEdge(
                        source_id=source_id,
                        target_id=mq_node.id,
                        target_hint="",
                        type="PUBLISHES_TO",
                        file_path=file_path,
                        line=line,
                        confidence="EXACT",
                        extractor="integration_extractor",
                    ))
                
                # Cache annotations
                elif stmt_type == "cache_annotation":
                    cache_name = stmt.get("cache_name", "")
                    annotation_type = stmt.get("annotation_type", "Cacheable")
                    
                    cache_node = Node(
                        id=f"{project_id}:cache_region:{cache_name}",
                        kind="cache_region",
                        name=cache_name,
                        fqn=cache_name,
                        file_path=file_path,
                        line_start=line,
                        line_end=line,
                        language="java" if "java" in file_path else "groovy",
                        project_id=project_id,
                        last_run_id=last_run_id,
                        docstring=None,
                        source_hash="",
                        properties={},
                        grails_version=None,
                    )
                    nodes.append(cache_node)
                    
                    source_id = f"{project_id}:method:{class_fqn}#{method_name}"
                    edge_type = "EVICTS_CACHE" if annotation_type == "CacheEvict" else "CACHED_BY"
                    edges.append(RawEdge(
                        source_id=source_id,
                        target_id=cache_node.id,
                        target_hint="",
                        type=edge_type,
                        file_path=file_path,
                        line=line,
                        confidence="EXACT",
                        extractor="integration_extractor",
                    ))
    
    return ExtractorResult(nodes=nodes, raw_edges=edges)
