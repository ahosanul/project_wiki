"""GSP (Groovy Server Pages) Parser - two-pass HTML + Groovy extraction."""
import re
from dataclasses import dataclass, field
from bs4 import BeautifulSoup
from typing import Iterator


@dataclass
class GspTag:
    """Represents a GSP tag like <g:link> or <f:display>."""
    namespace: str
    name: str
    attrs: dict
    line: int


@dataclass
class GspParseResult:
    """Complete parse result for a GSP file."""
    layout: str | None = None
    tags: list[GspTag] = field(default_factory=list)
    includes: list[str] = field(default_factory=list)
    model_variable_refs: list[str] = field(default_factory=list)
    static_text: str = ""
    scriptlets: list[str] = field(default_factory=list)
    expressions: list[str] = field(default_factory=list)
    el_expressions: list[str] = field(default_factory=list)
    taglib_directives: list[dict] = field(default_factory=list)


def parse_gsp(source: str, file_path: str) -> GspParseResult:
    """
    Parse a GSP file using two-pass approach.
    
    Pass 1: BS4 + lxml for HTML structure and tags
    Pass 2: Regex for scriptlets, expressions, EL
    """
    result = GspParseResult()
    
    # Pass 1: BeautifulSoup for HTML structure
    soup = BeautifulSoup(source, 'lxml')
    
    # Find layout from meta tag
    layout_meta = soup.find('meta', attrs={'name': 'layout'})
    if layout_meta and layout_meta.get('content'):
        result.layout = layout_meta['content']
    
    # Find all g:* and f:* tags
    for tag in soup.find_all(re.compile(r'^(g|f):')):
        tag_name = tag.name
        if ':' in tag_name:
            namespace, name = tag_name.split(':', 1)
        else:
            namespace = ''
            name = tag_name
        
        # Extract attributes
        attrs = {}
        for attr, value in tag.attrs.items():
            if attr not in ['xmlns']:
                attrs[attr] = value
        
        # Estimate line number (imperfect without original line tracking)
        line = _estimate_line_number(source, f'<{tag_name}')
        
        result.tags.append(GspTag(
            namespace=namespace,
            name=name,
            attrs=attrs,
            line=line,
        ))
        
        # Extract includes from g:include
        if namespace == 'g' and name == 'include':
            include_val = attrs.get('template') or attrs.get('page') or attrs.get('view')
            if include_val:
                result.includes.append(include_val)
    
    # Find taglib directives
    for directive in soup.find_all(string=re.compile(r'<%@ taglib')):
        match = re.search(r'<%@ taglib\s+uri="([^"]+)"\s+prefix="([^"]+)"', directive)
        if match:
            result.taglib_directives.append({
                'uri': match.group(1),
                'prefix': match.group(2),
            })
    
    # Extract static text (simplified - just get body text)
    if soup.body:
        result.static_text = soup.body.get_text(separator=' ', strip=True)[:5000]
    else:
        result.static_text = soup.get_text(separator=' ', strip=True)[:5000]
    
    # Pass 2: Regex for dynamic content
    lines = source.split('\n')
    
    # Scriptlets: <% ... %>
    scriptlet_pattern = re.compile(r'<%\s*(?!%)(.*?)\s*%>', re.DOTALL)
    for match in scriptlet_pattern.finditer(source):
        content = match.group(1).strip()
        if content:  # Skip empty scriptlets
            result.scriptlets.append(content)
    
    # Expressions: <%= ... %>
    expr_pattern = re.compile(r'<%=\s*(.*?)\s*%>')
    for match in expr_pattern.finditer(source):
        content = match.group(1).strip()
        if content:
            result.expressions.append(content)
    
    # EL expressions: ${...}
    el_pattern = re.compile(r'\$\{([^}]+)\}')
    for match in el_pattern.finditer(source):
        content = match.group(1).strip()
        if content:
            result.el_expressions.append(content)
            # Extract variable names from EL
            var_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)', content)
            if var_match:
                var_name = var_match.group(1)
                if var_name not in result.model_variable_refs:
                    result.model_variable_refs.append(var_name)
    
    # Extract model variable references from GSP expressions
    for tag in result.tags:
        if tag.namespace == 'g' and tag.name in ('link', 'render', 'form', 'actionLink'):
            # These often reference model variables
            for attr_val in tag.attrs.values():
                if isinstance(attr_val, str):
                    # Look for ${var} patterns in attribute values
                    for var_match in re.finditer(r'\$\{([a-zA-Z_][a-zA-Z0-9_]*)', attr_val):
                        var_name = var_match.group(1)
                        if var_name not in result.model_variable_refs:
                            result.model_variable_refs.append(var_name)
    
    return result


def _estimate_line_number(source: str, search_str: str, start_pos: int = 0) -> int:
    """Estimate line number for a string in source."""
    pos = source.find(search_str, start_pos)
    if pos == -1:
        return 1
    
    # Count newlines before position
    return source[:pos].count('\n') + 1


def extract_gsp_links(tags: list[GspTag]) -> list[dict]:
    """Extract link information from g:link tags."""
    links = []
    for tag in tags:
        if tag.namespace == 'g' and tag.name == 'link':
            link_info = {
                'action': tag.attrs.get('action'),
                'controller': tag.attrs.get('controller'),
                'mapping': tag.attrs.get('mapping'),
                'uri': tag.attrs.get('uri'),
                'id': tag.attrs.get('id'),
            }
            if any(link_info.values()):
                links.append(link_info)
    return links


def extract_gsp_renders(tags: list[GspTag]) -> list[dict]:
    """Extract render/include information from g:render tags."""
    renders = []
    for tag in tags:
        if tag.namespace == 'g' and tag.name == 'render':
            render_info = {
                'template': tag.attrs.get('template'),
                'model': tag.attrs.get('model'),
                'var': tag.attrs.get('var'),
            }
            if render_info['template']:
                renders.append(render_info)
    return renders
