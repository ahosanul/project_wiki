"""Grails Artifact Classifier - stamps Groovy AST nodes with Grails artifact kinds."""
from typing import Any


def classify_grails_artifact(ast_data: dict, artifact_type: str) -> str:
    """
    Given a Groovy AST node + artifact_type → stamp with Grails artifact kind.
    
    Rules:
    - controller artifact_type → kind='controller'
    - service → 'service'
    - domain → 'domain'
    - taglib → 'tag_lib'
    - job → 'job'
    - filters → 'grails_filters'
    - interceptor → 'interceptor'
    - urlmappings → 'url_mappings'
    - config → 'grails_config'
    - bootstrap → 'bootstrap'
    - buildconfig → 'grails_buildconfig'
    - resources.groovy → 'grails_spring_dsl'
    - etc.
    """
    # Direct mapping from artifact_type to kind
    type_to_kind = {
        'grails_controller': 'controller',
        'grails_service': 'service',
        'grails_domain': 'domain',
        'grails_taglib': 'tag_lib',
        'grails_job': 'job',
        'grails_filters': 'grails_filters',
        'grails_interceptor': 'interceptor',
        'grails_urlmappings': 'url_mappings',
        'grails_config': 'grails_config',
        'grails_bootstrap': 'bootstrap',
        'grails_buildconfig': 'grails_buildconfig',
        'grails_spring_dsl': 'grails_spring_dsl',
        'grails_datasource': 'grails_datasource',
        'gsp_view': 'gsp_view',
        'gsp_layout': 'gsp_layout',
        'gsp_template': 'gsp_template',
        'jsp_view': 'jsp_view',
        'jsp_include': 'jsp_include',
    }
    
    return type_to_kind.get(artifact_type, 'plain_groovy')


def get_artifact_metadata(artifact_type: str, grails_version: str) -> dict:
    """Get metadata about an artifact type for the given Grails version."""
    metadata = {
        'grails_controller': {
            'description': 'Grails Controller',
            'convention': '*Controller.groovy',
            'actions': 'public methods or closures',
        },
        'grails_service': {
            'description': 'Grails Service',
            'convention': '*Service.groovy',
            'transactional': True,
        },
        'grails_domain': {
            'description': 'Grails Domain Class',
            'convention': 'grails-app/domain/**/*.groovy',
            'orm': 'GORM',
        },
        'grails_taglib': {
            'description': 'Grails Tag Library',
            'convention': '*TagLib.groovy',
            'namespace': 'static namespace',
        },
        'grails_job': {
            'description': 'Grails Quartz Job',
            'convention': '*Job.groovy',
            'triggers': 'static triggers or closure',
        },
        'grails_interceptor': {
            'description': 'Grails 3.x Interceptor',
            'convention': '*Interceptor.groovy',
            'only_if': 'Grails 3.x',
        },
        'grails_filters': {
            'description': 'Grails 2.x Filters',
            'convention': '*Filters.groovy',
            'only_if': 'Grails 2.x',
        },
        'grails_urlmappings': {
            'description': 'URL Mappings',
            'file': 'UrlMappings.groovy',
        },
        'grails_bootstrap': {
            'description': 'Bootstrap Class',
            'file': 'BootStrap.groovy',
            'methods': ['init', 'destroy'],
        },
        'grails_buildconfig': {
            'description': 'Build Configuration',
            'file': 'BuildConfig.groovy',
            'only_if': 'Grails 2.x',
        },
        'grails_spring_dsl': {
            'description': 'Spring Bean DSL',
            'file': 'resources.groovy or spring/resources.groovy',
        },
        'grails_config': {
            'description': 'Application Configuration',
            'files': ['Config.groovy', 'application.groovy', 'application.yml'],
        },
    }
    
    return metadata.get(artifact_type, {})
