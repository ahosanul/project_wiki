"""Groovy Extractor - extracts symbols from Groovy AST (from sidecar)."""
from dataclasses import dataclass, field
from typing import Any
from erp_wiki_mcp.extractors.base import ExtractorResult
from erp_wiki_mcp.registry.models import Node


@dataclass
class GroovyExtractor:
    """Extracts nodes and edges from Groovy AST."""
    
    project_id: str
    file_path: str
    artifact_type: str
    grails_version: str = "unknown"
    
    def extract(self, ast_data: dict) -> ExtractorResult:
        """
        Extract nodes and edges from Groovy AST.
        
        Handles:
        - Classes, interfaces, traits
        - Methods, constructors, fields
        - Named closures at class body level → method/action nodes
        - Traits → interface nodes
        - Script-level statements → wrapped in synthetic Script class
        """
        nodes = []
        raw_edges = []
        
        classes = ast_data.get('classes', [])
        
        for cls in classes:
            # Determine kind based on artifact type and class characteristics
            kind = self._determine_kind(cls)
            
            # Extract class node
            class_node = self._extract_class_node(cls, kind)
            if class_node:
                nodes.append(class_node)
            
            # Extract fields
            for field_data in cls.get('fields', []):
                field_node = self._extract_field_node(cls, field_data, kind)
                if field_node:
                    nodes.append(field_node)
                    # DECLARES edge from class to field
                    raw_edges.append({
                        'source_id': class_node.id,
                        'target_id': field_node.id,
                        'type': 'DECLARES',
                        'confidence': 'EXACT',
                        'file_path': self.file_path,
                        'line': field_data.get('line', 0),
                        'extractor': 'groovy_extractor',
                    })
            
            # Extract methods
            for method_data in cls.get('methods', []):
                method_node = self._extract_method_node(cls, method_data, kind)
                if method_node:
                    nodes.append(method_node)
                    # DECLARES edge from class to method
                    raw_edges.append({
                        'source_id': class_node.id,
                        'target_id': method_node.id,
                        'type': 'DECLARES',
                        'confidence': 'EXACT',
                        'file_path': self.file_path,
                        'line': method_data.get('line', 0),
                        'extractor': 'groovy_extractor',
                    })
        
        return ExtractorResult(nodes=nodes, raw_edges=raw_edges)
    
    def _determine_kind(self, cls: dict) -> str:
        """Determine the kind of symbol based on artifact type and class characteristics."""
        # Import here to avoid circular dependency
        from .grails_classifier import classify_grails_artifact
        
        base_kind = classify_grails_artifact(cls, self.artifact_type)
        
        # Check if it's a trait (Groovy interface-like construct)
        if cls.get('traits'):
            return 'interface'
        
        # Check annotations for special types
        annotations = cls.get('annotations', [])
        ann_names = [a.get('name', '') for a in annotations]
        
        if 'Interface' in ann_names or cls.get('is_interface'):
            return 'interface'
        
        return base_kind
    
    def _extract_class_node(self, cls: dict, kind: str) -> Node | None:
        """Extract a class/interface/enum node."""
        fqn = cls.get('fqn', cls.get('name', ''))
        name = cls.get('name', fqn.split('.')[-1] if fqn else '')
        
        # Build properties
        properties = {
            'superclass_hint': cls.get('superClass'),
            'interfaces_hints': cls.get('interfaces', []),
            'is_abstract': cls.get('is_abstract', False),
            'is_interface': kind == 'interface',
            'is_enum': kind == 'enum',
            'annotations': cls.get('annotations', []),
            'artifact_type': self.artifact_type,
            'grails_version': self.grails_version,
        }
        
        # Generate ID using project_id prefix
        project_prefix = self.project_id[:8] if len(self.project_id) >= 8 else self.project_id
        node_id = f"{project_prefix}:class:{fqn}"
        
        line_start = 1
        line_end = 1
        # Try to get line info from first method or field
        methods = cls.get('methods', [])
        fields = cls.get('fields', [])
        if methods:
            line_start = methods[0].get('line', 1)
        elif fields:
            line_start = fields[0].get('line', 1)
        
        return Node(
            id=node_id,
            kind=kind,
            name=name,
            fqn=fqn,
            file_path=self.file_path,
            line_start=line_start,
            line_end=line_end,
            language='groovy',
            project_id=self.project_id,
            last_run_id='',  # Will be set by orchestrator
            docstring='',  # Could extract from Javadoc if available
            source_hash='',  # Will be set by hash_gate
            properties=properties,
            grails_version=self.grails_version,
        )
    
    def _extract_field_node(self, cls: dict, field_data: dict, class_kind: str) -> Node | None:
        """Extract a field node."""
        field_name = field_data.get('name', '')
        if not field_name:
            return None
        
        class_fqn = cls.get('fqn', cls.get('name', ''))
        fqn = f"{class_fqn}#{field_name}"
        
        properties = {
            'type_hint': field_data.get('type', 'def'),
            'is_static': field_data.get('isStatic', False),
            'is_final': field_data.get('isFinal', False),
            'visibility': self._get_visibility(field_data),
            'annotations': field_data.get('annotations', []),
            'is_property': field_data.get('isProperty', False),
        }
        
        # DI candidate detection
        annotations = field_data.get('annotations', [])
        di_annotations = {'Autowired', 'Inject', 'Resource'}
        has_di = any(a.get('name') in di_annotations for a in annotations)
        
        # Spring-style untyped Java detection
        field_type = field_data.get('type', 'def')
        service_suffixes = {'Service', 'Repository', 'Dao', 'Manager', 'Component'}
        is_di_candidate = has_di or (
            field_type != 'def' and 
            any(field_type.endswith(suffix) for suffix in service_suffixes)
        )
        
        properties['is_di_candidate'] = is_di_candidate
        properties['injection_point'] = has_di
        
        # Qualifier hint
        for ann in annotations:
            if ann.get('name') == 'Qualifier':
                members = ann.get('members', {})
                properties['qualifier_hint'] = members.get('value', '')
                break
            elif ann.get('name') == 'Resource':
                members = ann.get('members', {})
                properties['qualifier_hint'] = members.get('name', '')
                break
        
        project_prefix = self.project_id[:8] if len(self.project_id) >= 8 else self.project_id
        node_id = f"{project_prefix}:field:{fqn}"
        
        return Node(
            id=node_id,
            kind='field',
            name=field_name,
            fqn=fqn,
            file_path=self.file_path,
            line_start=field_data.get('line', 0),
            line_end=field_data.get('endLine', field_data.get('line', 0)),
            language='groovy',
            project_id=self.project_id,
            last_run_id='',
            docstring='',
            source_hash='',
            properties=properties,
            grails_version=self.grails_version,
        )
    
    def _extract_method_node(self, cls: dict, method_data: dict, class_kind: str) -> Node | None:
        """Extract a method/action node."""
        method_name = method_data.get('name', '')
        if not method_name:
            return None
        
        class_fqn = cls.get('fqn', cls.get('name', ''))
        
        # Build signature from params
        params = method_data.get('params', [])
        param_types = ','.join(p.get('type', 'def') for p in params)
        signature = f"{method_name}({param_types})"
        fqn = f"{class_fqn}#{signature}"
        
        properties = {
            'return_type_hint': method_data.get('returnType', 'void'),
            'param_types': [p.get('type', 'def') for p in params],
            'is_static': method_data.get('isStatic', False),
            'is_abstract': method_data.get('isAbstract', False),
            'visibility': self._get_visibility(method_data),
            'annotations': method_data.get('annotations', []),
        }
        
        # Determine if this is an action (for controllers)
        if class_kind == 'controller':
            # Actions are methods/closures not starting with _ and not internal
            internal_methods = {'init', 'destroy', 'allowedMethods'}
            if not method_name.startswith('_') and method_name not in internal_methods:
                kind = 'action'
                properties['controller_id'] = f"{self.project_id[:8]}:class:{class_fqn}"
            else:
                kind = 'method'
        else:
            kind = 'method'
        
        project_prefix = self.project_id[:8] if len(self.project_id) >= 8 else self.project_id
        node_id = f"{project_prefix}:method:{fqn}"
        
        return Node(
            id=node_id,
            kind=kind,
            name=method_name,
            fqn=fqn,
            file_path=self.file_path,
            line_start=method_data.get('line', 0),
            line_end=method_data.get('endLine', method_data.get('line', 0)),
            language='groovy',
            project_id=self.project_id,
            last_run_id='',
            docstring='',
            source_hash='',
            properties=properties,
            grails_version=self.grails_version,
        )
    
    def _get_visibility(self, node_data: dict) -> str:
        """Extract visibility modifier from node data."""
        modifiers = node_data.get('modifiers', 0)
        
        # Java/Groovy modifier flags
        PUBLIC = 0x0001
        PROTECTED = 0x0004
        PRIVATE = 0x0002
        
        if modifiers & PRIVATE:
            return 'private'
        elif modifiers & PROTECTED:
            return 'protected'
        elif modifiers & PUBLIC:
            return 'public'
        else:
            return 'package'  # Default package-private
