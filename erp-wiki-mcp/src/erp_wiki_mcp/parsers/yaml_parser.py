"""YAML Parser - for application.yml and other YAML config files."""
import yaml
from typing import Any
from dataclasses import dataclass, field


@dataclass
class YamlParseResult:
    """Parse result for a YAML file."""
    data: dict = field(default_factory=dict)
    flat_data: dict = field(default_factory=dict)
    error: str | None = None
    is_multi_document: bool = False
    documents: list[dict] = field(default_factory=list)


def parse_yaml(source: str | bytes, file_path: str) -> YamlParseResult:
    """
    Parse YAML using safe loader.
    
    Handles multi-document YAML (--- separators) and flattens nested dicts
    to dot-notation for config files.
    """
    result = YamlParseResult()
    
    try:
        if isinstance(source, bytes):
            source = source.decode('utf-8')
        
        # Check for multi-document YAML
        if '---' in source:
            result.is_multi_document = True
            result.documents = list(yaml.safe_load_all(source))
            # Merge all documents into single data dict
            merged = {}
            for doc in result.documents:
                if doc:
                    _deep_merge(merged, doc)
            result.data = merged
        else:
            result.data = yaml.safe_load(source) or {}
        
        # Flatten to dot-notation for config access
        result.flat_data = _flatten_dict(result.data)
        
    except yaml.YAMLError as e:
        result.error = f"YAML syntax error: {e}"
    except Exception as e:
        result.error = f"YAML parse error: {e}"
    
    return result


def _flatten_dict(d: dict, parent_key: str = '', sep: str = '.') -> dict:
    """Flatten nested dictionary to dot-notation keys."""
    items = []
    if not isinstance(d, dict):
        return {parent_key: d} if parent_key else {}
    
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, new_key, sep).items())
        elif isinstance(v, list):
            # Convert lists to string representation
            items.append((new_key, _serialize_list(v)))
        else:
            items.append((new_key, v))
    
    return dict(items)


def _serialize_list(lst: list) -> str:
    """Serialize a list to a string representation."""
    if not lst:
        return '[]'
    
    # Simple comma-separated for primitive values
    if all(isinstance(x, (str, int, float, bool)) for x in lst):
        return ', '.join(str(x) for x in lst)
    
    # For complex objects, use YAML representation
    try:
        return yaml.dump(lst, default_flow_style=True).strip()
    except Exception:
        return str(lst)


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge two dictionaries, with override taking precedence."""
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result


def extract_spring_profiles(data: dict) -> list[str]:
    """Extract Spring profile names from YAML structure."""
    profiles = []
    
    # Look for spring.profiles or profiles keys
    if 'spring' in data and isinstance(data['spring'], dict):
        spring_data = data['spring']
        if 'profiles' in spring_data:
            prof_val = spring_data['profiles']
            if isinstance(prof_val, str):
                profiles.extend(prof_val.split(','))
            elif isinstance(prof_val, list):
                profiles.extend(prof_val)
    
    # Look for profile-specific sections (e.g., ---\nspring:\n  config:\n    activate:\n      on-profile: dev)
    def find_on_profile(obj, path=''):
        if isinstance(obj, dict):
            if 'on-profile' in obj:
                profile = obj['on-profile']
                if isinstance(profile, str) and profile not in profiles:
                    profiles.append(profile)
            for k, v in obj.items():
                find_on_profile(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for item in obj:
                find_on_profile(item, path)
    
    find_on_profile(data)
    
    return profiles
