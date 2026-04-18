"""XML Parser - streaming parser for Spring XML config and other XML files."""
from lxml import etree
from typing import Iterator, Any
from dataclasses import dataclass, field


@dataclass
class XmlParseResult:
    """Parse result for an XML file."""
    root_tag: str = ""
    namespaces: dict = field(default_factory=dict)
    elements_count: int = 0
    bean_count: int = 0
    beans: list[dict] = field(default_factory=list)
    tree: Any = None  # lxml element tree
    error: str | None = None


def parse_xml(source: bytes | str, file_path: str) -> XmlParseResult:
    """
    Parse XML using streaming iterparse for memory efficiency.
    
    Special handling for Spring XML configuration to extract bean definitions.
    """
    result = XmlParseResult()
    
    try:
        if isinstance(source, str):
            source = source.encode('utf-8')
        
        # Use iterparse for streaming
        context = etree.iterparse(
            source,
            events=('start', 'end'),
            tag_filter=None,
            recover=True,
            huge_tree=True,
        )
        
        beans = []
        elements_count = 0
        bean_count = 0
        
        root = None
        for event, elem in context:
            elements_count += 1
            
            if event == 'start' and root is None:
                root = elem
                result.root_tag = elem.tag
                
                # Extract namespaces
                if hasattr(elem, 'nsmap') and elem.nsmap:
                    result.namespaces = {k or 'default': v for k, v in elem.nsmap.items()}
            
            # Look for Spring bean definitions
            if event == 'end' and _is_bean_element(elem):
                bean_info = _extract_bean_info(elem)
                if bean_info:
                    beans.append(bean_info)
                    bean_count += 1
                
                # Clear element to save memory
                elem.clear()
                while elem.getprevious() is not None:
                    del elem.getparent()[0]
        
        result.elements_count = elements_count
        result.bean_count = bean_count
        result.beans = beans
        
        # Re-parse to get full tree (for small/medium files)
        try:
            if isinstance(source, bytes):
                result.tree = etree.fromstring(source)
            else:
                result.tree = etree.fromstring(source.encode('utf-8'))
        except Exception:
            pass  # Tree not critical, we have the extracted info
        
    except etree.XMLSyntaxError as e:
        result.error = f"XML syntax error: {e}"
    except Exception as e:
        result.error = f"XML parse error: {e}"
    
    return result


def _is_bean_element(elem) -> bool:
    """Check if element is a Spring bean definition."""
    tag = elem.tag
    
    # Remove namespace prefix if present
    if '}' in tag:
        tag = tag.split('}')[1]
    
    return tag in ('bean', 'alias')


def _extract_bean_info(elem) -> dict | None:
    """Extract bean information from a Spring <bean> element."""
    tag = elem.tag
    if '}' in tag:
        tag = tag.split('}')[1]
    
    if tag == 'alias':
        return {
            'type': 'alias',
            'name': elem.get('name', ''),
            'alias': elem.get('alias', ''),
        }
    
    # Bean element
    bean_info = {
        'type': 'bean',
        'id': elem.get('id', ''),
        'name': elem.get('name', ''),
        'class': elem.get('class', ''),
        'parent': elem.get('parent-bean', '') or elem.get('parent', ''),
        'abstract': elem.get('abstract', 'false').lower() == 'true',
        'singleton': elem.get('singleton', 'true').lower() == 'true',
        'lazy_init': elem.get('lazy-init', 'false').lower() == 'true',
        'init_method': elem.get('init-method', ''),
        'destroy_method': elem.get('destroy-method', ''),
        'scope': elem.get('scope', 'singleton'),
        'properties': [],
        'constructor_args': [],
    }
    
    # Extract properties
    for prop in elem.findall('.//*'):
        prop_tag = prop.tag
        if '}' in prop_tag:
            prop_tag = prop_tag.split('}')[1]
        
        if prop_tag == 'property':
            prop_info = {
                'name': prop.get('name', ''),
                'ref': prop.get('ref', ''),
                'value': prop.get('value', ''),
            }
            bean_info['properties'].append(prop_info)
        elif prop_tag == 'constructor-arg':
            arg_info = {
                'name': prop.get('name', ''),
                'ref': prop.get('ref', ''),
                'value': prop.get('value', ''),
                'index': prop.get('index', ''),
                'type': prop.get('type', ''),
            }
            bean_info['constructor_args'].append(arg_info)
    
    return bean_info


def find_elements_by_xpath(tree: Any, xpath: str, namespaces: dict | None = None) -> list:
    """Find elements in parsed XML tree using XPath."""
    if tree is None:
        return []
    
    try:
        if namespaces:
            return tree.xpath(xpath, namespaces=namespaces)
        else:
            return tree.xpath(xpath)
    except Exception:
        return []
