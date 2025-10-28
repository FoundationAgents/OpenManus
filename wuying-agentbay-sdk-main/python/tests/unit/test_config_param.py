import unittest
from unittest.mock import mock_open, patch

import os
import tempfile
from unittest import TestCase
from unittest.mock import patch, mock_open

from agentbay.config import load_config, default_config
from agentbay import Config
from pathlib import Path


class LoadConfigTestCase(unittest.TestCase):
    def setUp(self):
        # Create temporary .env file directory
        self.test_dir = tempfile.TemporaryDirectory()
        self.env_file = Path(self.test_dir.name) / ".env"

    def tearDown(self):
        self.test_dir.cleanup()

    def test_load_from_passed_config(self):
        """Test loading configuration from passed Config object"""
        os.chdir(self.test_dir.name)
        custom_cfg = Config(
            endpoint="custom-endpoint",
            timeout_ms=5000,
        )
        result = load_config(custom_cfg)

        self.assertEqual(result["endpoint"], "custom-endpoint")
        self.assertEqual(result["timeout_ms"], 5000)

    def test_load_from_env_file(self):
        """Test loading configuration from .env file"""
        with open(self.env_file, "w") as f:
            f.write(
                "AGENTBAY_ENDPOINT=env-endpoint\n"
                "AGENTBAY_TIMEOUT_MS=10000\n"
            )

        with os.scandir(self.test_dir.name) as it:
            print("Files in temp dir:", [entry.name for entry in it])

        os.environ.pop("AGENTBAY_ENDPOINT", None)
        os.environ.pop("AGENTBAY_TIMEOUT_MS", None)

        os.chdir(self.test_dir.name)
        result = load_config(None)

        self.assertEqual(result["endpoint"], "env-endpoint")
        self.assertEqual(result["timeout_ms"], 10000)

    @patch("pathlib.Path.is_file", return_value=False)
    def test_load_from_system_env_vars(self, mock_is_file):
        """Test loading configuration from system environment variables"""
        os.chdir(self.test_dir.name)
        os.environ["AGENTBAY_ENDPOINT"] = "sys-endpoint"
        os.environ["AGENTBAY_TIMEOUT_MS"] = "15000"

        result = load_config(None)

        self.assertEqual(result["endpoint"], "sys-endpoint")
        self.assertEqual(result["timeout_ms"], 15000)

    @patch("pathlib.Path.is_file", return_value=False)
    def test_use_default_config_when_no_source_provided(self, mock_is_file):
        """Test using default values when no configuration source is provided"""
        # Clear all related environment variables
        os.chdir(self.test_dir.name)
        os.environ.pop("AGENTBAY_ENDPOINT", None)
        os.environ.pop("AGENTBAY_TIMEOUT_MS", None)

        result = load_config(None)

        default = default_config()
        self.assertEqual(result["endpoint"], default["endpoint"])
        self.assertEqual(result["timeout_ms"], default["timeout_ms"])

    def test_config_precedence_order(self):
        """Test configuration priority order"""
        # Create .env file
        os.chdir(self.test_dir.name)
        with open(self.env_file, "w") as f:
            f.write(
                "AGENTBAY_ENDPOINT=env-endpoint\n"
                "AGENTBAY_TIMEOUT_MS=10000\n"
            )

        os.chdir(self.test_dir.name)
        # Set environment variables
        os.environ["AGENTBAY_ENDPOINT"] = "sys-endpoint"
        os.environ["AGENTBAY_TIMEOUT_MS"] = "15000"

        # Default configuration
        default = default_config()

        # 1. Test that explicitly passed configuration has highest priority
        custom_cfg = Config(
            endpoint="explicit-endpoint",
            timeout_ms=2000,
        )
        result = load_config(custom_cfg)
        self.assertEqual(result["endpoint"], "explicit-endpoint")
        self.assertEqual(result["timeout_ms"], 2000)

        # 2. When explicit configuration is None, should use environment variables
        result = load_config(None)
        self.assertEqual(result["endpoint"], "sys-endpoint")
        self.assertEqual(result["timeout_ms"], 15000)

        # 3. After clearing environment variables, should use .env file
        os.environ.pop("AGENTBAY_ENDPOINT")
        os.environ.pop("AGENTBAY_TIMEOUT_MS")
        result = load_config(None)
        self.assertEqual(result["endpoint"], "env-endpoint")
        self.assertEqual(result["timeout_ms"], 10000)


if __name__ == "__main__":
    unittest.main()
