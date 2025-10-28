"""
Test cases for enhanced .env file loading functionality.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest

from agentbay.config import find_dotenv_file, load_dotenv_with_fallback, load_config


class TestDotEnvLoading:
    """Test enhanced .env file loading functionality."""

    def test_find_dotenv_file_current_directory(self):
        """Test finding .env file in current directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            env_file = tmpdir_path / ".env"
            env_file.write_text("TEST_VAR=current_dir")
            
            # Find .env file from current directory
            found_file = find_dotenv_file(tmpdir_path)
            assert found_file.resolve() == env_file.resolve()
            assert found_file.exists()

    def test_find_dotenv_file_parent_directory(self):
        """Test finding .env file in parent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Create .env in parent directory
            parent_env = tmpdir_path / ".env"
            parent_env.write_text("TEST_VAR=parent_dir")
            
            # Create subdirectory
            subdir = tmpdir_path / "subdir"
            subdir.mkdir()
            
            # Find .env file from subdirectory (should find parent's .env)
            found_file = find_dotenv_file(subdir)
            assert found_file.resolve() == parent_env.resolve()
            assert found_file.exists()

    def test_find_dotenv_file_git_repo_root(self):
        """Test finding .env file in git repository root."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Create .git directory (simulate git repo)
            git_dir = tmpdir_path / ".git"
            git_dir.mkdir()
            
            # Create .env in git root
            git_env = tmpdir_path / ".env"
            git_env.write_text("TEST_VAR=git_root")
            
            # Create nested subdirectory
            subdir = tmpdir_path / "src" / "deep"
            subdir.mkdir(parents=True)
            
            # Find .env file from deep subdirectory
            found_file = find_dotenv_file(subdir)
            assert found_file.resolve() == git_env.resolve()

    def test_find_dotenv_file_not_found(self):
        """Test when .env file is not found anywhere."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            subdir = tmpdir_path / "subdir"
            subdir.mkdir()
            
            # No .env file anywhere
            found_file = find_dotenv_file(subdir)
            assert found_file is None

    def test_load_dotenv_with_custom_path(self):
        """Test loading .env file from custom path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            custom_env = tmpdir_path / "custom.env"
            custom_env.write_text("CUSTOM_VAR=custom_value")
            
            # Clear any existing env var
            if "CUSTOM_VAR" in os.environ:
                del os.environ["CUSTOM_VAR"]
            
            # Load custom .env file
            load_dotenv_with_fallback(str(custom_env))
            
            # Check if variable was loaded
            assert os.environ.get("CUSTOM_VAR") == "custom_value"
            
            # Cleanup
            if "CUSTOM_VAR" in os.environ:
                del os.environ["CUSTOM_VAR"]

    def test_load_dotenv_with_fallback_search(self):
        """Test loading .env file using fallback search."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Create .env in parent
            parent_env = tmpdir_path / ".env"
            parent_env.write_text("FALLBACK_VAR=fallback_value")
            
            # Create subdirectory
            subdir = tmpdir_path / "subdir"
            subdir.mkdir()
            
            # Clear any existing env var
            if "FALLBACK_VAR" in os.environ:
                del os.environ["FALLBACK_VAR"]
            
            # Change to subdirectory and load .env
            with patch('pathlib.Path.cwd', return_value=subdir):
                load_dotenv_with_fallback()
            
            # Check if variable was loaded from parent
            assert os.environ.get("FALLBACK_VAR") == "fallback_value"
            
            # Cleanup
            if "FALLBACK_VAR" in os.environ:
                del os.environ["FALLBACK_VAR"]

    def test_environment_variable_precedence(self):
        """Test that environment variables take precedence over .env file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            env_file = tmpdir_path / ".env"
            env_file.write_text("PRECEDENCE_VAR=from_env_file")
            
            # Set environment variable (higher precedence)
            os.environ["PRECEDENCE_VAR"] = "from_environment"
            
            try:
                # Load config with .env file
                config = load_config(None, str(env_file))
                
                # Environment variable should take precedence
                assert os.environ.get("PRECEDENCE_VAR") == "from_environment"
                
            finally:
                # Cleanup
                if "PRECEDENCE_VAR" in os.environ:
                    del os.environ["PRECEDENCE_VAR"]

    def test_load_config_with_custom_env_file(self):
        """Test load_config with custom .env file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            custom_env = tmpdir_path / "test.env"
            custom_env.write_text("""
AGENTBAY_ENDPOINT=wuyingai.ap-southeast-1.aliyuncs.com
AGENTBAY_TIMEOUT_MS=30000
""".strip())

            # Clear existing env vars
            for var in ["AGENTBAY_ENDPOINT", "AGENTBAY_TIMEOUT_MS"]:
                if var in os.environ:
                    del os.environ[var]

            try:
                # Load config with custom .env file
                config = load_config(None, str(custom_env))

                # Check if config was loaded from custom .env file
                assert config["endpoint"] == "wuyingai.ap-southeast-1.aliyuncs.com"
                assert config["timeout_ms"] == 30000

            finally:
                # Cleanup
                for var in ["AGENTBAY_ENDPOINT", "AGENTBAY_TIMEOUT_MS"]:
                    if var in os.environ:
                        del os.environ[var]

    def test_load_config_upward_search(self):
        """Test load_config with upward .env file search."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create .env in parent
            parent_env = tmpdir_path / ".env"
            parent_env.write_text("AGENTBAY_ENDPOINT=wuyingai.cn-shanghai.aliyuncs.com")

            # Create subdirectory
            subdir = tmpdir_path / "project" / "src"
            subdir.mkdir(parents=True)

            # Clear existing env vars
            if "AGENTBAY_ENDPOINT" in os.environ:
                del os.environ["AGENTBAY_ENDPOINT"]

            try:
                # Simulate running from subdirectory
                with patch('os.getcwd', return_value=str(subdir)):
                    config = load_config(None)

                # Should find .env from parent directory
                assert config["endpoint"] == "wuyingai.cn-shanghai.aliyuncs.com"

            finally:
                # Cleanup
                if "AGENTBAY_ENDPOINT" in os.environ:
                    del os.environ["AGENTBAY_ENDPOINT"]

    def test_invalid_timeout_handling(self):
        """Test handling of invalid AGENTBAY_TIMEOUT_MS values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            env_file = tmpdir_path / ".env"
            env_file.write_text("AGENTBAY_TIMEOUT_MS=invalid_number")
            
            # Clear existing env vars
            if "AGENTBAY_TIMEOUT_MS" in os.environ:
                del os.environ["AGENTBAY_TIMEOUT_MS"]
            
            try:
                # Load config with invalid timeout
                config = load_config(None, str(env_file))
                
                # Should use default timeout value
                assert config["timeout_ms"] == 60000  # Default value
                
            finally:
                # Cleanup
                if "AGENTBAY_TIMEOUT_MS" in os.environ:
                    del os.environ["AGENTBAY_TIMEOUT_MS"]


if __name__ == "__main__":
    pytest.main([__file__])