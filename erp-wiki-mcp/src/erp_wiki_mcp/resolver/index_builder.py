"""Resolver index builder."""

from dataclasses import dataclass, field


@dataclass
class IndexTables:
    """In-memory index tables for resolution."""

    fqn_to_id: dict[str, str] = field(default_factory=dict)
    simple_name_to_ids: dict[str, list[str]] = field(default_factory=dict)
    bean_name_to_id: dict[str, str] = field(default_factory=dict)
    controller_action_map: dict[tuple[str, str], str] = field(default_factory=dict)
    view_path_map: dict[str, str] = field(default_factory=dict)
    file_imports: dict[str, list[str]] = field(default_factory=dict)


def build_index_tables(nodes: list, file_imports: dict[str, list[str]]) -> IndexTables:
    """
    Build index tables from extracted nodes.

    Args:
        nodes: List of Node objects from extraction
        file_imports: Mapping of file_path to list of imports

    Returns:
        IndexTables with populated indices
    """
    tables = IndexTables(file_imports=file_imports)

    for node in nodes:
        # Build FQN index
        if node.fqn:
            tables.fqn_to_id[node.fqn] = node.id

        # Build simple name index
        if node.name:
            simple_name = node.name.split(".")[-1].split("#")[0]
            if simple_name not in tables.simple_name_to_ids:
                tables.simple_name_to_ids[simple_name] = []
            tables.simple_name_to_ids[simple_name].append(node.id)

        # Build bean name index for DI candidates
        if node.kind == "field" and node.properties.get("is_di_candidate"):
            bean_name = node.name
            # Also try camelCase conversion for class names
            type_hint = node.properties.get("type_hint", "")
            if type_hint:
                # Convert ClassName to className for bean name
                if len(type_hint) > 0:
                    bean_name_camel = type_hint[0].lower() + type_hint[1:]
                    tables.bean_name_to_id[bean_name_camel] = node.id
            tables.bean_name_to_id[bean_name] = node.id

        # Build controller action map
        if node.kind == "method" and "Controller" in node.fqn:
            # Extract controller name and action
            parts = node.fqn.split(".")
            if len(parts) >= 2:
                controller_name = parts[-2]
                action_name = node.name
                tables.controller_action_map[(controller_name, action_name)] = node.id

    return tables
