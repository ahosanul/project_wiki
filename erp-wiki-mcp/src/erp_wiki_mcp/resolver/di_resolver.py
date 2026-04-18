"""DI Resolver (Pass 1) - resolves INJECTS edges."""
from dataclasses import dataclass, field
from typing import Any
from erp_wiki_mcp.resolver.index_builder import IndexTables


@dataclass
class ResolvedEdge:
    """An edge that has been resolved with confidence level."""
    source_id: str
    target_id: str
    type: str
    confidence: str  # EXACT | LIKELY | HEURISTIC | UNRESOLVED
    file_path: str
    line: int
    extractor: str
    target_hint: str = ""


@dataclass
class ResolverWarning:
    """Warning from resolver."""
    code: str  # missing_view|missing_template|unresolved_di|ambiguous_call
    edge_type: str
    source_id: str
    hint: str
    file_path: str
    line: int


@dataclass
class ResolverResult:
    """Result of DI resolution pass."""
    resolved: list[ResolvedEdge] = field(default_factory=list)
    unresolved: list = field(default_factory=list)  # RawEdge
    warnings: list[ResolverWarning] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)  # edge IDs removed


def resolve_injects(
    inject_edges: list,
    index: IndexTables,
    file_imports: dict[str, list[str]],
) -> ResolverResult:
    """
    Resolve INJECTS edges with confidence=UNRESOLVED.
    
    Resolution order:
    1. @Qualifier("x") → bean_name_to_id["x"] → EXACT
    2. @Autowired + typed → fqn_to_id via file_imports → EXACT
    3. Typed field → fqn_to_id via file_imports → EXACT
    4. def / untyped Groovy → bean_name_to_id[field_name] (Grails DI convention) → LIKELY
    5. Multiple beans match → HEURISTIC (store all candidate IDs)
    6. No match → UNRESOLVED (keep target_hint)
    """
    result = ResolverResult()
    
    for edge in inject_edges:
        source_id = edge.get('source_id', '')
        target_hint = edge.get('target_hint', '')
        file_path = edge.get('file_path', '')
        line = edge.get('line', 0)
        extractor = edge.get('extractor', 'di_resolver')
        
        # Extract info from target_hint
        # Format: service:{field_name}|class:{class}|file:{file_path}
        hint_parts = {}
        for part in target_hint.split('|'):
            if ':' in part:
                key, val = part.split(':', 1)
                hint_parts[key] = val
        
        field_name = hint_parts.get('service', hint_parts.get('field', ''))
        class_fqn = hint_parts.get('class', '')
        
        # Get source node properties to check for annotations and type
        # (This would normally come from the graph, but we'll use hints for now)
        
        resolved_edge = None
        
        # Step 1: Check for @Qualifier
        qualifier = hint_parts.get('qualifier', '')
        if qualifier and qualifier in index.bean_name_to_id:
            target_id = index.bean_name_to_id[qualifier]
            resolved_edge = ResolvedEdge(
                source_id=source_id,
                target_id=target_id,
                type='INJECTS',
                confidence='EXACT',
                file_path=file_path,
                line=line,
                extractor=extractor,
                target_hint=target_hint,
            )
        
        # Step 2-3: Typed field → fqn_to_id via imports
        elif hint_parts.get('type') and hint_parts['type'] != 'def':
            field_type = hint_parts['type']
            # Try direct FQN match
            if field_type in index.fqn_to_id:
                target_id = index.fqn_to_id[field_type]
                resolved_edge = ResolvedEdge(
                    source_id=source_id,
                    target_id=target_id,
                    type='INJECTS',
                    confidence='EXACT',
                    file_path=file_path,
                    line=line,
                    extractor=extractor,
                    target_hint=target_hint,
                )
            else:
                # Try via imports
                imports = file_imports.get(file_path, [])
                for imp in imports:
                    if imp.endswith(field_type) or imp.split('.')[-1] == field_type:
                        if imp in index.fqn_to_id:
                            target_id = index.fqn_to_id[imp]
                            resolved_edge = ResolvedEdge(
                                source_id=source_id,
                                target_id=target_id,
                                type='INJECTS',
                                confidence='EXACT',
                                file_path=file_path,
                                line=line,
                                extractor=extractor,
                                target_hint=target_hint,
                            )
                            break
        
        # Step 4: Untyped Groovy → bean_name_to_id[field_name] (Grails convention)
        elif field_name:
            # Convert field name to bean name convention (camelCase)
            bean_name = field_name
            if bean_name in index.bean_name_to_id:
                target_id = index.bean_name_to_id[bean_name]
                resolved_edge = ResolvedEdge(
                    source_id=source_id,
                    target_id=target_id,
                    type='INJECTS',
                    confidence='LIKELY',
                    file_path=file_path,
                    line=line,
                    extractor=extractor,
                    target_hint=target_hint,
                )
        
        if resolved_edge:
            result.resolved.append(resolved_edge)
        else:
            # Keep as UNRESOLVED
            result.unresolved.append(edge)
            
            # Emit warning for unresolved DI
            result.warnings.append(ResolverWarning(
                code='unresolved_di',
                edge_type='INJECTS',
                source_id=source_id,
                hint=target_hint,
                file_path=file_path,
                line=line,
            ))
    
    return result
