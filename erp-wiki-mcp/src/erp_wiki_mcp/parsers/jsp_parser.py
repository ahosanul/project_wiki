"""JSP (JavaServer Pages) Parser - similar to GSP but for JSP files."""
import re
from dataclasses import dataclass, field
from bs4 import BeautifulSoup


@dataclass
class JspDirective:
    """Represents a JSP directive like <%@ page %> or <%@ include %>."""
    type: str  # page, include, taglib
    attrs: dict
    line: int


@dataclass
class JspAction:
    """Represents a JSP action like <jsp:include> or <jsp:forward>."""
    name: str
    attrs: dict
    line: int


@dataclass
class JspParseResult:
    """Complete parse result for a JSP file."""
    directives: list[JspDirective] = field(default_factory=list)
    actions: list[JspAction] = field(default_factory=list)
    taglib_directives: list[dict] = field(default_factory=list)
    includes: list[str] = field(default_factory=list)
    forwards: list[str] = field(default_factory=list)
    static_text: str = ""
    scriptlets: list[str] = field(default_factory=list)
    expressions: list[str] = field(default_factory=list)
    el_expressions: list[str] = field(default_factory=list)


def parse_jsp(source: str, file_path: str) -> JspParseResult:
    """
    Parse a JSP file using two-pass approach.
    
    Pass 1: BS4 + lxml for HTML structure and tags
    Pass 2: Regex for scriptlets, expressions, EL, directives
    """
    result = JspParseResult()
    
    # Pass 1: BeautifulSoup for HTML structure
    soup = BeautifulSoup(source, 'lxml')
    
    # Find jsp:* actions
    for tag in soup.find_all(re.compile(r'^jsp:')):
        tag_name = tag.name
        if ':' in tag_name:
            _, name = tag_name.split(':', 1)
        else:
            name = tag_name
        
        # Extract attributes
        attrs = {}
        for attr, value in tag.attrs.items():
            attrs[attr] = value
        
        line = _estimate_line_number(source, f'<{tag_name}')
        
        action = JspAction(name=name, attrs=attrs, line=line)
        result.actions.append(action)
        
        # Extract includes
        if name == 'include':
            include_val = attrs.get('page')
            if include_val:
                result.includes.append(include_val)
        
        # Extract forwards
        if name == 'forward':
            forward_val = attrs.get('page')
            if forward_val:
                result.forwards.append(forward_val)
    
    # Extract static text
    if soup.body:
        result.static_text = soup.body.get_text(separator=' ', strip=True)[:5000]
    else:
        result.static_text = soup.get_text(separator=' ', strip=True)[:5000]
    
    # Pass 2: Regex for directives and dynamic content
    
    # Directives: <%@ ... %>
    directive_pattern = re.compile(r'<%@\s+(\w+)\s+([^%]+)%>', re.DOTALL)
    for match in directive_pattern.finditer(source):
        directive_type = match.group(1).strip()
        attrs_str = match.group(2).strip()
        
        # Parse attributes
        attrs = {}
        attr_pattern = re.compile(r'(\w+)="([^"]*)"')
        for attr_match in attr_pattern.finditer(attrs_str):
            attrs[attr_match.group(1)] = attr_match.group(2)
        
        line = source[:match.start()].count('\n') + 1
        
        directive = JspDirective(type=directive_type, attrs=attrs, line=line)
        result.directives.append(directive)
        
        # Taglib directives
        if directive_type == 'taglib':
            result.taglib_directives.append({
                'uri': attrs.get('uri', ''),
                'prefix': attrs.get('prefix', ''),
            })
        
        # Include directives
        if directive_type == 'include' and 'file' in attrs:
            result.includes.append(attrs['file'])
    
    # Scriptlets: <% ... %> (not directives)
    scriptlet_pattern = re.compile(r'<%\s*(?![@=])(.*?)\s*%>', re.DOTALL)
    for match in scriptlet_pattern.finditer(source):
        content = match.group(1).strip()
        if content:
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
    
    return result


def _estimate_line_number(source: str, search_str: str, start_pos: int = 0) -> int:
    """Estimate line number for a string in source."""
    pos = source.find(search_str, start_pos)
    if pos == -1:
        return 1
    return source[:pos].count('\n') + 1
