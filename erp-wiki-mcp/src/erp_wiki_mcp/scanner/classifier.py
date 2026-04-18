"""File classifier for Grails/Java projects."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def classify(file_path: str, grails_version: str) -> tuple[str, str]:
    """
    Classify a file by its path and Grails version.

    Args:
        file_path: Relative path within the project
        grails_version: "2.x" | "3.x" | "unknown"

    Returns:
        Tuple of (artifact_type, language)
    """
    path_lower = file_path.lower()
    path_normalized = file_path.replace("\\", "/")
    path_normalized_lower = path_normalized.lower()

    # Common patterns for both versions (first-match wins)
    common_rules = [
        ("grails-app/controllers/", "*controller.groovy", "grails_controller", "groovy"),
        ("grails-app/services/", "*service.groovy", "grails_service", "groovy"),
        ("grails-app/domain/", "*.groovy", "grails_domain", "groovy"),
        ("grails-app/taglib/", "*taglib.groovy", "grails_taglib", "groovy"),
        ("grails-app/jobs/", "*job.groovy", "grails_job", "groovy"),
        ("grails-app/conf/urlmappings.groovy", None, "grails_urlmappings", "groovy"),
        ("grails-app/conf/", "*filters.groovy", "grails_filters", "groovy"),
        ("grails-app/views/layouts/", "*.gsp", "gsp_layout", "gsp"),
        ("grails-app/views/", "_*.gsp", "gsp_template", "gsp"),
        ("grails-app/views/", "*.gsp", "gsp_view", "gsp"),
        ("", "*.jspf", "jsp_include", "jsp"),
        ("", "*.jsp", "jsp_view", "jsp"),
        ("", "*.java", "plain_java", "java"),
        ("", "*.xml", "xml_config", "xml"),
        ("", "*.properties", "properties_config", "properties"),
    ]

    # Grails 3.x specific rules
    grails3_rules = [
        ("grails-app/controllers/", "*interceptor.groovy", "grails_interceptor", "groovy"),
        ("grails-app/conf/", "resources.groovy", "grails_spring_dsl", "groovy"),
        ("grails-app/conf/application.yml", None, "grails_config", "yaml"),
        ("grails-app/conf/application.groovy", None, "grails_config", "groovy"),
        ("src/main/groovy/", "*.groovy", "plain_groovy", "groovy"),
        ("src/main/java/", "*.java", "plain_java", "java"),
        ("", "*.yml", "yaml_config", "yaml"),
        ("", "*.yaml", "yaml_config", "yaml"),
        ("", "*.groovy", "plain_groovy", "groovy"),  # fallback
    ]

    # Grails 2.x specific rules
    grails2_rules = [
        ("grails-app/conf/config.groovy", None, "grails_config", "groovy"),
        ("grails-app/conf/datasource.groovy", None, "grails_datasource", "groovy"),
        ("grails-app/conf/buildconfig.groovy", None, "grails_buildconfig", "groovy"),
        ("grails-app/conf/bootstrap.groovy", None, "grails_bootstrap", "groovy"),
        ("grails-app/conf/spring/resources.groovy", None, "grails_spring_dsl", "groovy"),
        ("grails-app/conf/spring/", "*.groovy", "grails_spring_dsl", "groovy"),
        ("src/groovy/", "*.groovy", "plain_groovy", "groovy"),
        ("src/java/", "*.java", "plain_java", "java"),
        ("web-app/", "*.jsp", "jsp_view", "jsp"),
        ("web-app/", "*.jspf", "jsp_include", "jsp"),
        ("", "*.groovy", "plain_groovy", "groovy"),  # fallback
    ]

    def _match(filename: str, pattern: str) -> bool:
        """Match filename against pattern with * wildcard."""
        if pattern is None:
            return True
        if "*" not in pattern:
            return filename == pattern
        prefix, suffix = pattern.split("*", 1) if "*" in pattern else (pattern, "")
        return filename.startswith(prefix) and filename.endswith(suffix)

    def _check_rules(rules: list) -> tuple[str, str] | None:
        """Check file against a list of rules."""
        for rule in rules:
            prefix, pattern, artifact_type, language = rule
            
            # Check prefix match
            if prefix and not path_normalized_lower.startswith(prefix):
                continue
            
            # Get filename or full path for pattern matching
            filename = Path(file_path).name.lower()
            
            # If prefix is empty, check against full path or filename
            if not prefix:
                if pattern:
                    if _match(filename, pattern):
                        return (artifact_type, language)
                else:
                    # Exact path match
                    if path_normalized_lower.endswith(rule[1].lower() if rule[1] else ""):
                        pass
            else:
                # Check pattern against remainder of path or filename
                if pattern:
                    if _match(filename, pattern):
                        return (artifact_type, language)
        
        return None

    # Try common rules first
    for rule in common_rules:
        prefix, pattern, artifact_type, language = rule
        
        filename = Path(file_path).name.lower()
        
        # Handle exact file match (when pattern is None)
        if pattern is None:
            # Exact path match needed
            if path_normalized_lower == prefix.lower():
                return (artifact_type, language)
            continue
        
        # Check prefix match
        if prefix and not path_normalized_lower.startswith(prefix):
            continue
        
        # Pattern matching
        if _match(filename, pattern):
            return (artifact_type, language)

    # Version-specific rules
    if grails_version == "3.x":
        for rule in grails3_rules:
            prefix, pattern, artifact_type, language = rule
            
            filename = Path(file_path).name.lower()
            
            # Handle exact file match (when pattern is None)
            if pattern is None:
                if path_normalized_lower == prefix.lower():
                    return (artifact_type, language)
                continue
            
            if prefix and not path_normalized_lower.startswith(prefix):
                # Special case for root-level patterns
                if not prefix and _match(filename, pattern):
                    return (artifact_type, language)
                continue
            
            if _match(filename, pattern):
                return (artifact_type, language)

    elif grails_version == "2.x":
        for rule in grails2_rules:
            prefix, pattern, artifact_type, language = rule
            
            filename = Path(file_path).name.lower()
            
            # Handle exact file match (when pattern is None)
            if pattern is None:
                if path_normalized_lower == prefix.lower():
                    return (artifact_type, language)
                continue
            
            if prefix and not path_normalized_lower.startswith(prefix):
                if not prefix and _match(filename, pattern):
                    return (artifact_type, language)
                continue
            
            if _match(filename, pattern):
                return (artifact_type, language)

    # Fallback for unknown files
    logger.warning(f"Unknown file type: {file_path}")
    return ("unknown", "unknown")
