#!/usr/bin/env python3
"""Test workflow generation uses correct GitHub token configuration."""

import shutil
import sys
import tempfile
import pytest
from pathlib import Path

# Add the parent directory to the path so we can import setup  # noqa: E402
sys.path.insert(0, str(Path(__file__).parent.parent))

from setup import ConductorSetup  # noqa: E402


def test_generated_workflows_use_github_token():
    """Test that generated workflows use github.token, not CONDUCTOR_GITHUB_TOKEN."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a minimal project structure
        project_path = Path(tmpdir) / "test-project"
        project_path.mkdir()

        # Initialize git repo
        import subprocess

        subprocess.run(["git", "init"], cwd=project_path, capture_output=True)

        # Create minimal package.json to trigger stack detection
        package_json = project_path / "package.json"
        package_json.write_text(
            '{"name": "test-project", "dependencies": {"react": "^18.0.0"}}'
        )

        # Run setup in the test project directory
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(project_path)
            setup = ConductorSetup()
            # Set up minimal config with code-reviewer role
            setup.config = {
                "roles": {"default": "dev", "specialized": ["code-reviewer"]}
            }
            setup._create_github_workflows()
        finally:
            os.chdir(original_cwd)

        # Check conductor.yml
        conductor_workflow = project_path / ".github" / "workflows" / "conductor.yml"
        assert (
            conductor_workflow.exists()
        ), f"Workflow not found at {conductor_workflow}"

        content = conductor_workflow.read_text()
        # Should use github.token
        assert "${{ github.token }}" in content
        # Should NOT use CONDUCTOR_GITHUB_TOKEN
        assert "CONDUCTOR_GITHUB_TOKEN" not in content

        # Check pr-review.yml
        pr_review_workflow = project_path / ".github" / "workflows" / "pr-review.yml"
        assert pr_review_workflow.exists()

        pr_content = pr_review_workflow.read_text()
        # Should use github.token
        assert "${{ github.token }}" in pr_content
        # Should NOT use CONDUCTOR_GITHUB_TOKEN
        assert "CONDUCTOR_GITHUB_TOKEN" not in pr_content

        # Check cleanup workflow
        cleanup_workflow = (
            project_path / ".github" / "workflows" / "conductor-cleanup.yml"
        )
        assert cleanup_workflow.exists()

        cleanup_content = cleanup_workflow.read_text()
        # Cleanup workflow doesn't need GH_TOKEN, but should not have CONDUCTOR_GITHUB_TOKEN
        assert "CONDUCTOR_GITHUB_TOKEN" not in cleanup_content


def test_no_workflow_copy_during_install():
    """Verify that conductor-init.sh doesn't copy workflow files."""
    init_script = Path(__file__).parent.parent / "conductor-init.sh"
    assert init_script.exists()

    content = init_script.read_text()

    # Should NOT copy workflow files
    assert 'cp -r "$TEMP_DIR/.github/workflows"' not in content

    # Should have a note about workflow generation
    assert (
        "Workflow files will be regenerated" in content
        or "workflows are generated by setup.py" in content
    )


if __name__ == "__main__":
    test_generated_workflows_use_github_token()
    test_no_workflow_copy_during_install()
    print("✅ All workflow generation tests passed!")
