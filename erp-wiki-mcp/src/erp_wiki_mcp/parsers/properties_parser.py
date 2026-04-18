"""Properties file parser - for .properties config files."""
from dataclasses import dataclass, field
import re


@dataclass
class PropertiesParseResult:
    """Parse result for a .properties file."""
    data: dict = field(default_factory=dict)
    comments: list[str] = field(default_factory=list)
    error: str | None = None


def parse_properties(source: str | bytes, file_path: str) -> PropertiesParseResult:
    """
    Parse Java-style properties file.
    
    Handles:
    - key=value and key:value syntax
    - Line continuations with backslash
    - Comments starting with # or !
    - Unicode escapes (\\uXXXX)
    - Escaped special characters
    """
    result = PropertiesParseResult()
    
    try:
        if isinstance(source, bytes):
            source = source.decode('utf-8')
        
        data = {}
        current_key = None
        current_value = None
        continuation = False
        
        lines = source.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].rstrip('\r')
            
            # Handle line continuation
            if continuation:
                # Append to current value
                stripped = line.lstrip()
                if stripped.endswith('\\'):
                    current_value += stripped[:-1]
                else:
                    current_value += stripped
                    continuation = False
                    if current_key is not None:
                        data[current_key] = _unescape_value(current_value)
                i += 1
                continue
            
            # Skip empty lines
            if not line.strip():
                i += 1
                continue
            
            # Handle comments
            stripped = line.lstrip()
            if stripped.startswith('#') or stripped.startswith('!'):
                result.comments.append(stripped[1:].strip())
                i += 1
                continue
            
            # Parse key-value pair
            match = re.match(r'^([^:=]+?)\s*[:=]\s*(.*)', line)
            if match:
                key = match.group(1).strip()
                value = match.group(2)
                
                # Check for continuation
                if value.endswith('\\'):
                    current_key = key
                    current_value = value[:-1]
                    continuation = True
                else:
                    data[key] = _unescape_value(value)
            elif current_key is None and '=' in line:
                # Edge case: key starts with spaces
                parts = line.split('=', 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1]
                    if value.endswith('\\'):
                        current_key = key
                        current_value = value[:-1]
                        continuation = True
                    else:
                        data[key] = _unescape_value(value)
            
            i += 1
        
        # Handle unterminated continuation
        if continuation and current_key is not None:
            data[current_key] = _unescape_value(current_value)
        
        result.data = data
        
    except Exception as e:
        result.error = f"Properties parse error: {e}"
    
    return result


def _unescape_value(value: str) -> str:
    """Unescape Java properties value."""
    if not value:
        return ''
    
    # Handle common escape sequences
    result = []
    i = 0
    while i < len(value):
        char = value[i]
        
        if char == '\\' and i + 1 < len(value):
            next_char = value[i + 1]
            if next_char == 'n':
                result.append('\n')
                i += 2
                continue
            elif next_char == 'r':
                result.append('\r')
                i += 2
                continue
            elif next_char == 't':
                result.append('\t')
                i += 2
                continue
            elif next_char == 'f':
                result.append('\f')
                i += 2
                continue
            elif next_char == '\\':
                result.append('\\')
                i += 2
                continue
            elif next_char == ':':
                result.append(':')
                i += 2
                continue
            elif next_char == '=':
                result.append('=')
                i += 2
                continue
            elif next_char == 'u' and i + 5 < len(value):
                # Unicode escape \uXXXX
                try:
                    unicode_val = int(value[i + 2:i + 6], 16)
                    result.append(chr(unicode_val))
                    i += 6
                    continue
                except ValueError:
                    pass
        
        result.append(char)
        i += 1
    
    return ''.join(result).strip()


def extract_database_config(data: dict) -> dict:
    """Extract database configuration from properties data."""
    db_config = {}
    
    # Common Spring Boot / Grails DB property patterns
    patterns = {
        'url': ['dataSource.url', 'dataSource.dbcp.url', 'spring.datasource.url', 
                'jdbc.url', 'database.url', 'hibernate.connection.url'],
        'driver': ['dataSource.driverClassName', 'dataSource.driver', 
                   'spring.datasource.driver-class-name', 'jdbc.driver'],
        'username': ['dataSource.username', 'dataSource.user', 
                     'spring.datasource.username', 'jdbc.user'],
        'password': ['dataSource.password', 'spring.datasource.password', 
                     'jdbc.password'],
        'dialect': ['hibernate.dialect', 'dataSource.dialect'],
    }
    
    for config_key, prop_keys in patterns.items():
        for prop_key in prop_keys:
            if prop_key in data:
                db_config[config_key] = data[prop_key]
                break
    
    return db_config
