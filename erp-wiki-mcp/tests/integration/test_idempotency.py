"""Integration tests for idempotency."""

import asyncio
import tempfile
from pathlib import Path

import pytest

from erp_wiki_mcp.config import settings
from erp_wiki_mcp.registry.db import RegistryDB
from erp_wiki_mcp.tools.index_project import index_project


@pytest.fixture
def test_project(tmp_path: Path) -> Path:
    """Create a minimal Grails 3.x project structure for testing."""
    project_root = tmp_path / "test-grails-app"
    project_root.mkdir()

    # Create build.gradle to signal Grails 3.x
    (project_root / "build.gradle").write_text("// Grails 3.x build file\n")

    # Create grails-app directory structure
    controllers_dir = project_root / "grails-app" / "controllers"
    controllers_dir.mkdir(parents=True)
    (controllers_dir / "UserController.groovy").write_text(
        "class UserController { def index() {} }"
    )
    (controllers_dir / "ApiController.groovy").write_text(
        "class ApiController { def list() {} }"
    )

    services_dir = project_root / "grails-app" / "services"
    services_dir.mkdir(parents=True)
    (services_dir / "UserService.groovy").write_text(
        "class UserService { def find() {} }"
    )

    domain_dir = project_root / "grails-app" / "domain"
    domain_dir.mkdir(parents=True)
    (domain_dir / "User.groovy").write_text("class User { String name }")

    views_dir = project_root / "grails-app" / "views" / "user"
    views_dir.mkdir(parents=True)
    (views_dir / "show.gsp").write_text("<html><body>Show User</body></html>")
    (views_dir / "_form.gsp").write_text("<g:form>Form</g:form>")

    layouts_dir = project_root / "grails-app" / "views" / "layouts"
    layouts_dir.mkdir(parents=True)
    (layouts_dir / "main.gsp").write_text("<html><g:layoutBody/></html>")

    conf_dir = project_root / "grails-app" / "conf"
    conf_dir.mkdir(parents=True)
    (conf_dir / "UrlMappings.groovy").write_text(
        "class UrlMappings { static mappings = { } }"
    )
    (conf_dir / "application.yml").write_text("grails:\n  profile: web\n")

    # Create src/main/groovy
    groovy_src = project_root / "src" / "main" / "groovy" / "com" / "example"
    groovy_src.mkdir(parents=True)
    (groovy_src / "Helper.groovy").write_text("class Helper { }")

    # Create .gitignore
    (project_root / ".gitignore").write_text("*.log\nbuild/\n")

    return project_root


@pytest.fixture
async def registry(tmp_path: Path) -> RegistryDB:
    """Create a test registry database."""
    db_path = tmp_path / "test_registry.db"
    registry = RegistryDB(db_path)
    await registry.init_db()
    return registry


@pytest.mark.asyncio
async def test_idempotency_two_dry_runs(test_project: Path, registry: RegistryDB):
    """Test that two consecutive dry_run passes produce zero diff on second pass."""
    # First dry run
    result1 = await index_project(
        registry=registry,
        path=str(test_project),
        mode="dry_run",
        scope="full",
    )

    assert result1["state"] == "COMPLETED"
    assert result1["error"] is None

    # Should have found some files
    total_files = result1["created"] + result1["modified"] + result1["unchanged"]
    assert total_files > 0, "Should have found at least one file"

    # Second dry run - should show zero created/modified since nothing changed
    result2 = await index_project(
        registry=registry,
        path=str(test_project),
        mode="dry_run",
        scope="full",
    )

    assert result2["state"] == "COMPLETED"
    assert result2["error"] is None

    # In dry_run mode, files aren't persisted to DB, so we expect same counts
    # But the key test is that running in full mode twice shows idempotency
    # Let's verify the file counts are consistent
    assert result1["file_counts"] == result2["file_counts"], (
        "File counts should be identical between runs"
    )


@pytest.mark.asyncio
async def test_full_mode_idempotency(test_project: Path, registry: RegistryDB):
    """Test that full mode indexing is idempotent."""
    # First full run
    result1 = await index_project(
        registry=registry,
        path=str(test_project),
        mode="full",
        scope="full",
    )

    assert result1["state"] == "COMPLETED"
    assert result1["error"] is None

    # First run should create files
    assert result1["created"] > 0 or result1["modified"] > 0

    # Second full run - should show zero created/modified
    result2 = await index_project(
        registry=registry,
        path=str(test_project),
        mode="full",
        scope="full",
    )

    assert result2["state"] == "COMPLETED"
    assert result2["error"] is None

    # Second run should have no new files and no modifications
    assert result2["created"] == 0, f"Expected 0 created, got {result2['created']}"
    assert result2["modified"] == 0, f"Expected 0 modified, got {result2['modified']}"


@pytest.mark.asyncio
async def test_all_files_classified(test_project: Path, registry: RegistryDB):
    """Test that all standard Grails files are classified (no unknown)."""
    result = await index_project(
        registry=registry,
        path=str(test_project),
        mode="dry_run",
        scope="full",
    )

    assert result["state"] == "COMPLETED"

    # Check that we have expected artifact types
    file_counts = result["file_counts"]

    # Should have these artifact types from our test project
    expected_types = [
        "grails_controller",
        "grails_service",
        "grails_domain",
        "gsp_view",
        "gsp_template",
        "gsp_layout",
        "grails_urlmappings",
        "grails_config",
        "plain_groovy",
    ]

    for artifact_type in expected_types:
        assert artifact_type in file_counts, f"Missing artifact type: {artifact_type}"
        assert file_counts[artifact_type] > 0

    # Should have no unknown files
    assert "unknown" not in file_counts or file_counts.get("unknown", 0) == 0
