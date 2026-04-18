"""Unit tests for the file classifier."""

import pytest

from erp_wiki_mcp.scanner.classifier import classify


class TestClassifierCommon:
    """Test common classification rules (both Grails versions)."""

    @pytest.mark.parametrize(
        "path,expected",
        [
            ("grails-app/controllers/UserController.groovy", ("grails_controller", "groovy")),
            ("grails-app/controllers/api/ApiController.groovy", ("grails_controller", "groovy")),
            ("grails-app/services/UserService.groovy", ("grails_service", "groovy")),
            ("grails-app/domain/User.groovy", ("grails_domain", "groovy")),
            ("grails-app/taglib/CustomTagLib.groovy", ("grails_taglib", "groovy")),
            ("grails-app/jobs/CleanupJob.groovy", ("grails_job", "groovy")),
            ("grails-app/conf/UrlMappings.groovy", ("grails_urlmappings", "groovy")),
            ("grails-app/conf/SecurityFilters.groovy", ("grails_filters", "groovy")),
            ("grails-app/views/layouts/main.gsp", ("gsp_layout", "gsp")),
            ("grails-app/views/user/_form.gsp", ("gsp_template", "gsp")),
            ("grails-app/views/user/show.gsp", ("gsp_view", "gsp")),
            ("web-app/WEB-INF/includes/header.jspf", ("jsp_include", "jsp")),
            ("web-app/WEB-INF/views/index.jsp", ("jsp_view", "jsp")),
            ("src/java/com/example/Util.java", ("plain_java", "java")),
            ("config/application.xml", ("xml_config", "xml")),
            ("config/database.properties", ("properties_config", "properties")),
        ],
    )
    def test_common_rules(self, path, expected):
        """Test common classification rules."""
        result = classify(path, "3.x")
        assert result == expected

    @pytest.mark.parametrize(
        "path",
        [
            "grails-app/controllers/UserController.groovy",
            "grails-app/services/UserService.groovy",
            "grails-app/domain/User.groovy",
        ],
    )
    def test_common_rules_grails2(self, path):
        """Test common rules work for Grails 2.x too."""
        # Common rules should work for both versions
        result = classify(path, "2.x")
        assert result[1] == "groovy"  # At least language should match


class TestClassifierGrails3:
    """Test Grails 3.x specific classification rules."""

    @pytest.mark.parametrize(
        "path,expected",
        [
            ("grails-app/controllers/AuthInterceptor.groovy", ("grails_interceptor", "groovy")),
            ("grails-app/conf/resources.groovy", ("grails_spring_dsl", "groovy")),
            ("grails-app/conf/application.yml", ("grails_config", "yaml")),
            ("grails-app/conf/application.groovy", ("grails_config", "groovy")),
            ("src/main/groovy/com/example/Helper.groovy", ("plain_groovy", "groovy")),
            ("src/main/java/com/example/Util.java", ("plain_java", "java")),
            ("config/settings.yml", ("yaml_config", "yaml")),
            ("config/settings.yaml", ("yaml_config", "yaml")),
            ("scripts/deploy.groovy", ("plain_groovy", "groovy")),
        ],
    )
    def test_grails3_rules(self, path, expected):
        """Test Grails 3.x specific rules."""
        result = classify(path, "3.x")
        assert result == expected


class TestClassifierGrails2:
    """Test Grails 2.x specific classification rules."""

    @pytest.mark.parametrize(
        "path,expected",
        [
            ("grails-app/conf/Config.groovy", ("grails_config", "groovy")),
            ("grails-app/conf/DataSource.groovy", ("grails_datasource", "groovy")),
            ("grails-app/conf/BuildConfig.groovy", ("grails_buildconfig", "groovy")),
            ("grails-app/conf/BootStrap.groovy", ("grails_bootstrap", "groovy")),
            ("grails-app/conf/spring/resources.groovy", ("grails_spring_dsl", "groovy")),
            ("grails-app/conf/spring/security.groovy", ("grails_spring_dsl", "groovy")),
            ("src/groovy/com/example/Helper.groovy", ("plain_groovy", "groovy")),
            ("src/java/com/example/Util.java", ("plain_java", "java")),
            ("web-app/js/app.js", ("unknown", "unknown")),  # JS not classified
            ("web-app/css/style.css", ("unknown", "unknown")),  # CSS not classified
        ],
    )
    def test_grails2_rules(self, path, expected):
        """Test Grails 2.x specific rules."""
        result = classify(path, "2.x")
        assert result == expected


class TestClassifierEdgeCases:
    """Test edge cases and error handling."""

    def test_unknown_file_type(self):
        """Test unknown file types return unknown."""
        result = classify("random/file.xyz", "3.x")
        assert result == ("unknown", "unknown")

    def test_case_insensitive(self):
        """Test that classification is case-insensitive."""
        result1 = classify("grails-app/controllers/UserController.groovy", "3.x")
        result2 = classify("GRAILS-APP/CONTROLLERS/UserController.GROOVY", "3.x")
        # Both should classify as grails_controller
        assert result1[0] == "grails_controller"
        assert result2[0] == "grails_controller"

    def test_windows_paths(self):
        """Test Windows-style paths are handled."""
        result = classify("grails-app\\controllers\\UserController.groovy", "3.x")
        assert result[0] == "grails_controller"

    def test_empty_path(self):
        """Test empty path handling."""
        result = classify("", "3.x")
        assert result == ("unknown", "unknown")
