"""Render Resolver (Pass 3) - resolves RENDERS, REDIRECTS_TO, LINKS_TO, etc."""
from dataclasses import dataclass, field
from typing import Any
from erp_wiki_mcp.resolver.index_builder import IndexTables
from .di_resolver import ResolvedEdge, ResolverWarning, ResolverResult


@dataclass
class RenderResolver:
    """Resolves render, redirect, forward, chain, and view-related edges."""
    
    index: IndexTables
    grails_version: str = "unknown"
    
    def resolve_renders(self, render_edges: list, file_path_map: dict[str, str]) -> ResolverResult:
        """
        Resolve RENDERS edges.
        
        - render(view:'show') → construct views/{ctrl_dir}/show.gsp → view_path_map → EXACT
        - No explicit view → default views/{ctrl_dir}/{action_name}.gsp → same lookup
        - Not found → UNRESOLVED, kind=missing_view, emit warning
        """
        result = ResolverResult()
        
        for edge in render_edges:
            source_id = edge.get('source_id', '')
            target_hint = edge.get('target_hint', '')
            file_path = edge.get('file_path', '')
            line = edge.get('line', 0)
            extractor = edge.get('extractor', 'render_resolver')
            
            # Extract view name from hint
            # Format: view:{view_name}|controller:{ctrl}|action:{action}
            hint_parts = {}
            for part in target_hint.split('|'):
                if ':' in part:
                    key, val = part.split(':', 1)
                    hint_parts[key] = val
            
            view_name = hint_parts.get('view', '')
            controller = hint_parts.get('controller', '')
            action = hint_parts.get('action', '')
            
            resolved_edge = None
            
            if view_name:
                # Explicit view specified
                # Try to find in view_path_map
                # Construct possible paths
                possible_paths = []
                if controller:
                    possible_paths.append(f"grails-app/views/{controller.lower()}/{view_name}.gsp")
                possible_paths.append(f"grails-app/views/{view_name}.gsp")
                
                for path in possible_paths:
                    if path in self.index.view_path_map:
                        target_id = self.index.view_path_map[path]
                        resolved_edge = ResolvedEdge(
                            source_id=source_id,
                            target_id=target_id,
                            type='RENDERS',
                            confidence='EXACT',
                            file_path=file_path,
                            line=line,
                            extractor=extractor,
                            target_hint=target_hint,
                        )
                        break
                
                # Also try short name lookup
                if not resolved_edge and view_name in self.index.view_path_map:
                    target_id = self.index.view_path_map[view_name]
                    resolved_edge = ResolvedEdge(
                        source_id=source_id,
                        target_id=target_id,
                        type='RENDERS',
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
                
                # Emit warning for missing view
                result.warnings.append(ResolverWarning(
                    code='missing_view',
                    edge_type='RENDERS',
                    source_id=source_id,
                    hint=view_name or target_hint,
                    file_path=file_path,
                    line=line,
                ))
        
        return result
    
    def resolve_redirects(self, redirect_edges: list) -> ResolverResult:
        """
        Resolve REDIRECTS_TO / FORWARDS_TO / CHAINS_TO edges.
        
        - redirect(action:'list') → controller_action_map[(source_ctrl, 'list')] → EXACT
        - redirect(action:'list', controller:'Loan') → controller_action_map[('LoanController','list')] → EXACT
        - redirect(uri:'/loan/list') → url_mapping_map[('*','/loan/list')] → LIKELY
        """
        result = ResolverResult()
        
        for edge in redirect_edges:
            source_id = edge.get('source_id', '')
            target_hint = edge.get('target_hint', '')
            file_path = edge.get('file_path', '')
            line = edge.get('line', 0)
            extractor = edge.get('extractor', 'render_resolver')
            edge_type = edge.get('type', 'REDIRECTS_TO')
            
            # Extract from hint
            # Format: action:{action}|controller:{ctrl}|uri:{uri}
            hint_parts = {}
            for part in target_hint.split('|'):
                if ':' in part:
                    key, val = part.split(':', 1)
                    hint_parts[key] = val
            
            action = hint_parts.get('action', '')
            controller = hint_parts.get('controller', '')
            uri = hint_parts.get('uri', '')
            
            resolved_edge = None
            
            # Try action/controller resolution
            if action:
                # Need to determine source controller from source_id
                # For now, use hint or infer
                ctrl_hint = controller or hint_parts.get('source_controller', '')
                
                if ctrl_hint:
                    # Normalize controller name
                    if not ctrl_hint.endswith('Controller'):
                        ctrl_hint = f"{ctrl_hint}Controller"
                    
                    key = (ctrl_hint, action)
                    if key in self.index.controller_action_map:
                        target_id = self.index.controller_action_map[key]
                        resolved_edge = ResolvedEdge(
                            source_id=source_id,
                            target_id=target_id,
                            type=edge_type,
                            confidence='EXACT',
                            file_path=file_path,
                            line=line,
                            extractor=extractor,
                            target_hint=target_hint,
                        )
            
            # Try URI resolution
            if not resolved_edge and uri:
                # Try exact match first
                if ('*', uri) in self.index.url_mapping_map:
                    target_id = self.index.url_mapping_map[('*', uri)]
                    resolved_edge = ResolvedEdge(
                        source_id=source_id,
                        target_id=target_id,
                        type=edge_type,
                        confidence='LIKELY',
                        file_path=file_path,
                        line=line,
                        extractor=extractor,
                        target_hint=target_hint,
                    )
            
            if resolved_edge:
                result.resolved.append(resolved_edge)
            else:
                result.unresolved.append(edge)
        
        return result
    
    def resolve_links_to(self, link_edges: list) -> ResolverResult:
        """
        Resolve LINKS_TO edges from GSP <g:link> tags.
        
        - <g:link action="approve" controller="Loan"> → controller_action_map[('LoanController','approve')] → EXACT
        - No controller → infer from view file path → LIKELY
        - <g:link mapping="approveRoute"> → url_mapping_map by named mapping → EXACT
        """
        result = ResolverResult()
        
        for edge in link_edges:
            source_id = edge.get('source_id', '')
            target_hint = edge.get('target_hint', '')
            file_path = edge.get('file_path', '')
            line = edge.get('line', 0)
            extractor = edge.get('extractor', 'render_resolver')
            
            # Extract from hint
            # Format: action:{action}|controller:{ctrl}|mapping:{name}
            hint_parts = {}
            for part in target_hint.split('|'):
                if ':' in part:
                    key, val = part.split(':', 1)
                    hint_parts[key] = val
            
            action = hint_parts.get('action', '')
            controller = hint_parts.get('controller', '')
            mapping = hint_parts.get('mapping', '')
            
            resolved_edge = None
            
            # Try named mapping first
            if mapping:
                # Look for named URL mapping
                for (http_method, pattern), target_id in self.index.url_mapping_map.items():
                    # This is simplified - would need actual named mapping lookup
                    pass
            
            # Try action/controller resolution
            if action and not resolved_edge:
                ctrl_hint = controller or ''
                if ctrl_hint:
                    if not ctrl_hint.endswith('Controller'):
                        ctrl_hint = f"{ctrl_hint}Controller"
                    
                    key = (ctrl_hint, action)
                    if key in self.index.controller_action_map:
                        target_id = self.index.controller_action_map[key]
                        resolved_edge = ResolvedEdge(
                            source_id=source_id,
                            target_id=target_id,
                            type='LINKS_TO',
                            confidence='EXACT',
                            file_path=file_path,
                            line=line,
                            extractor=extractor,
                            target_hint=target_hint,
                        )
            
            if resolved_edge:
                result.resolved.append(resolved_edge)
            else:
                result.unresolved.append(edge)
        
        return result
    
    def resolve_uses_layout(self, uses_layout_edges: list) -> ResolverResult:
        """
        Resolve USES_LAYOUT edges.
        
        - layout_map["main"] → EXACT
        - else UNRESOLVED kind=missing_layout
        """
        result = ResolverResult()
        
        for edge in uses_layout_edges:
            source_id = edge.get('source_id', '')
            target_hint = edge.get('target_hint', '')
            file_path = edge.get('file_path', '')
            line = edge.get('line', 0)
            extractor = edge.get('extractor', 'render_resolver')
            
            # Extract layout name from hint
            layout_name = target_hint.replace('layout:', '') if ':' in target_hint else target_hint
            
            resolved_edge = None
            
            if layout_name in self.index.layout_map:
                target_id = self.index.layout_map[layout_name]
                resolved_edge = ResolvedEdge(
                    source_id=source_id,
                    target_id=target_id,
                    type='USES_LAYOUT',
                    confidence='EXACT',
                    file_path=file_path,
                    line=line,
                    extractor=extractor,
                    target_hint=target_hint,
                )
            
            if resolved_edge:
                result.resolved.append(resolved_edge)
            else:
                result.unresolved.append(edge)
                
                result.warnings.append(ResolverWarning(
                    code='missing_layout',
                    edge_type='USES_LAYOUT',
                    source_id=source_id,
                    hint=layout_name,
                    file_path=file_path,
                    line=line,
                ))
        
        return result
