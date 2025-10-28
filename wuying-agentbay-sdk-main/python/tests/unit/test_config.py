import unittest
from unittest.mock import mock_open, patch

from agentbay.config import default_config, load_config


class TestConfig(unittest.TestCase):
    """Test the configuration module functionality"""

    def test_default_config(self):
        """Test the default configuration values"""
        config = default_config()
        self.assertIsInstance(config, dict)
        self.assertEqual(config["endpoint"], "wuyingai.cn-shanghai.aliyuncs.com")
        self.assertEqual(config["timeout_ms"], 60000)

    @patch("os.getenv", return_value=None)
    @patch("os.path.exists", return_value=False)
    def test_load_config_fallback_to_default(self, mock_exists, mock_getenv):
        """Test fallback to default configuration when no config file is found"""
        config = load_config(None)

        default = default_config()
        self.assertEqual(config["endpoint"], default["endpoint"])
        self.assertEqual(config["timeout_ms"], default["timeout_ms"])


if __name__ == "__main__":
    unittest.main()
