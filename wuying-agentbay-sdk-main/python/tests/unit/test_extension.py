"""
Unit tests for extension management functionality.

This module contains comprehensive unit tests for:
- ExtensionsService class
- ExtensionOption class  
- Extension class
- Error handling and validation
"""

import os
import unittest
from unittest.mock import Mock, patch, MagicMock
from agentbay.extension import ExtensionsService, ExtensionOption, Extension
from agentbay.exceptions import AgentBayError


class TestExtension(unittest.TestCase):
    """Test cases for Extension class."""
    
    def test_extension_creation(self):
        """Test Extension object creation."""
        ext = Extension(id="ext_123", name="test-extension.zip")
        
        self.assertEqual(ext.id, "ext_123")
        self.assertEqual(ext.name, "test-extension.zip")
        self.assertIsNone(ext.created_at)
    
    def test_extension_creation_with_timestamp(self):
        """Test Extension creation with timestamp."""
        timestamp = "2024-01-01T00:00:00Z"
        ext = Extension(id="ext_456", name="test.zip", created_at=timestamp)
        
        self.assertEqual(ext.created_at, timestamp)

class TestExtensionOption(unittest.TestCase):
    """Test cases for ExtensionOption class."""
    
    def test_extension_option_creation(self):
        """Test ExtensionOption creation with valid parameters."""
        ext_option = ExtensionOption(
            context_id="ctx_123",
            extension_ids=["ext_1", "ext_2"]
        )
        
        self.assertEqual(ext_option.context_id, "ctx_123")
        self.assertEqual(ext_option.extension_ids, ["ext_1", "ext_2"])
    
    def test_extension_option_empty_context_id(self):
        """Test ExtensionOption creation with empty context_id."""
        with self.assertRaises(ValueError) as context:
            ExtensionOption(context_id="", extension_ids=["ext_1"])
        
        self.assertIn("context_id cannot be empty", str(context.exception))
    
    def test_extension_option_whitespace_context_id(self):
        """Test ExtensionOption creation with whitespace context_id."""
        with self.assertRaises(ValueError) as context:
            ExtensionOption(context_id="   ", extension_ids=["ext_1"])
        
        self.assertIn("context_id cannot be empty", str(context.exception))
    
    def test_extension_option_empty_extension_ids(self):
        """Test ExtensionOption creation with empty extension_ids."""
        with self.assertRaises(ValueError) as context:
            ExtensionOption(context_id="ctx_123", extension_ids=[])
        
        self.assertIn("extension_ids cannot be empty", str(context.exception))
    
    def test_extension_option_none_extension_ids(self):
        """Test ExtensionOption creation with None extension_ids."""
        with self.assertRaises(ValueError) as context:
            ExtensionOption(context_id="ctx_123", extension_ids=None)
        
        self.assertIn("extension_ids cannot be empty", str(context.exception))
    
    def test_extension_option_validate_valid(self):
        """Test validate method with valid configuration."""
        ext_option = ExtensionOption(
            context_id="ctx_123",
            extension_ids=["ext_1", "ext_2"]
        )
        
        self.assertTrue(ext_option.validate())
    
    def test_extension_option_validate_invalid_context(self):
        """Test validate method with invalid context."""
        ext_option = ExtensionOption(
            context_id="ctx_123",
            extension_ids=["ext_1"]
        )
        
        # Manually corrupt the context_id to test validation
        ext_option.context_id = ""
        
        self.assertFalse(ext_option.validate())
    
    def test_extension_option_validate_invalid_extensions(self):
        """Test validate method with invalid extension_ids."""
        ext_option = ExtensionOption(
            context_id="ctx_123",
            extension_ids=["ext_1"]
        )
        
        # Manually corrupt the extension_ids to test validation
        ext_option.extension_ids = [""]
        
        self.assertFalse(ext_option.validate())
    
    def test_extension_option_str_representation(self):
        """Test ExtensionOption string representation."""
        ext_option = ExtensionOption(
            context_id="ctx_123",
            extension_ids=["ext_1", "ext_2"]
        )
        
        str_repr = str(ext_option)
        self.assertIn("2 extension(s)", str_repr)
        self.assertIn("ctx_123", str_repr)
    
    def test_extension_option_repr(self):
        """Test ExtensionOption repr representation."""
        ext_option = ExtensionOption(
            context_id="ctx_123",
            extension_ids=["ext_1", "ext_2"]
        )
        
        repr_str = repr(ext_option)
        self.assertIn("ExtensionOption", repr_str)
        self.assertIn("ctx_123", repr_str)
        self.assertIn("ext_1", repr_str)


class TestExtensionsService(unittest.TestCase):
    """Test cases for ExtensionsService class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_agent_bay = Mock()
        self.mock_context_service = Mock()
        self.mock_agent_bay.context = self.mock_context_service
        
        # Mock successful context creation
        self.mock_context = Mock()
        self.mock_context.id = "ctx_test_123"
        
        self.mock_context_result = Mock()
        self.mock_context_result.success = True
        self.mock_context_result.context = self.mock_context
        
        self.mock_context_service.get.return_value = self.mock_context_result
    
    def test_extensions_service_creation_with_context_id(self):
        """Test ExtensionsService creation with explicit context_id."""
        service = ExtensionsService(self.mock_agent_bay, "test_context")
        
        self.assertEqual(service.context_id, "ctx_test_123")
        self.assertEqual(service.context_name, "test_context")
        self.assertTrue(service.auto_created)
        self.mock_context_service.get.assert_called_once_with("test_context", create=True)
    
    @patch('time.time')
    def test_extensions_service_creation_auto_context(self, mock_time):
        """Test ExtensionsService creation with auto-generated context."""
        mock_time.return_value = 1234567890
        
        service = ExtensionsService(self.mock_agent_bay, "")
        
        expected_context_name = "extensions-1234567890"
        self.mock_context_service.get.assert_called_once_with(expected_context_name, create=True)
    
    def test_extensions_service_creation_context_failure(self):
        """Test ExtensionsService creation when context creation fails."""
        # Mock failed context creation
        self.mock_context_result.success = False
        self.mock_context_result.context = None
        
        with self.assertRaises(AgentBayError) as context:
            ExtensionsService(self.mock_agent_bay, "test_context")
        
        self.assertIn("Failed to create extension repository context", str(context.exception))
    
    @patch('os.path.exists')
    @patch('builtins.open', create=True)
    @patch('requests.put')
    def test_create_extension_success(self, mock_put, mock_open, mock_exists):
        """Test successful extension creation."""
        # Setup mocks
        mock_exists.return_value = True
        mock_put.return_value.status_code = 200
        
        # Mock file upload URL
        mock_url_result = Mock()
        mock_url_result.success = True
        mock_url_result.url = "https://presigned-url.com"
        self.mock_context_service.get_file_upload_url.return_value = mock_url_result
        
        service = ExtensionsService(self.mock_agent_bay, "test_context")
        
        # Test extension creation
        extension = service.create("/path/to/test.zip")
        
        self.assertIsInstance(extension, Extension)
        self.assertTrue(extension.id.startswith("ext_"))
        self.assertEqual(extension.name, "test.zip")
        
        # Verify upload URL was requested
        self.mock_context_service.get_file_upload_url.assert_called_once()
        
        # Verify file was uploaded
        mock_put.assert_called_once()
    
    @patch('os.path.exists')
    def test_create_extension_file_not_found(self, mock_exists):
        """Test extension creation with non-existent file."""
        mock_exists.return_value = False
        
        service = ExtensionsService(self.mock_agent_bay, "test_context")
        
        with self.assertRaises(FileNotFoundError):
            service.create("/path/to/nonexistent.zip")
    
    @patch('os.path.exists')
    def test_create_extension_invalid_format(self, mock_exists):
        """Test extension creation with invalid file format."""
        mock_exists.return_value = True
        
        service = ExtensionsService(self.mock_agent_bay, "test_context")
        
        with self.assertRaises(ValueError) as context:
            service.create("/path/to/test.txt")
        
        self.assertIn("Only ZIP format", str(context.exception))
    
    def test_list_extensions_success(self):
        """Test successful extension listing."""
        # Mock file list result
        mock_file_entry1 = Mock()
        mock_file_entry1.file_name = "ext_123.zip"
        mock_file_entry1.gmt_create = "2024-01-01T00:00:00Z"
        
        mock_file_entry2 = Mock()
        mock_file_entry2.file_name = "ext_456.zip"
        mock_file_entry2.gmt_create = "2024-01-02T00:00:00Z"
        
        mock_list_result = Mock()
        mock_list_result.success = True
        mock_list_result.entries = [mock_file_entry1, mock_file_entry2]
        
        self.mock_context_service.list_files.return_value = mock_list_result
        
        service = ExtensionsService(self.mock_agent_bay, "test_context")
        extensions = service.list()
        
        self.assertEqual(len(extensions), 2)
        self.assertEqual(extensions[0].id, "ext_123.zip")
        self.assertEqual(extensions[1].id, "ext_456.zip")
    
    def test_list_extensions_failure(self):
        """Test extension listing failure."""
        mock_list_result = Mock()
        mock_list_result.success = False
        
        self.mock_context_service.list_files.return_value = mock_list_result
        
        service = ExtensionsService(self.mock_agent_bay, "test_context")
        
        with self.assertRaises(AgentBayError):
            service.list()
    
    @patch('os.path.exists')
    @patch('builtins.open', create=True)
    @patch('requests.put')
    def test_update_extension_success(self, mock_put, mock_open, mock_exists):
        """Test successful extension update."""
        # Setup mocks
        mock_exists.return_value = True
        mock_put.return_value.status_code = 200
        
        # Mock existing extension
        mock_extension = Mock()
        mock_extension.id = "ext_123"
        mock_extension.name = "test.zip"
        
        # Mock file upload URL
        mock_url_result = Mock()
        mock_url_result.success = True
        mock_url_result.url = "https://presigned-url.com"
        self.mock_context_service.get_file_upload_url.return_value = mock_url_result
        
        service = ExtensionsService(self.mock_agent_bay, "test_context")
        
        # Mock list to return existing extension
        with patch.object(service, 'list', return_value=[mock_extension]):
            updated_ext = service.update("ext_123", "/path/to/updated.zip")
        
        self.assertEqual(updated_ext.id, "ext_123")
        self.assertEqual(updated_ext.name, "updated.zip")
    
    @patch('os.path.exists')
    def test_update_extension_not_found(self, mock_exists):
        """Test update of non-existent extension."""
        mock_exists.return_value = True
        
        service = ExtensionsService(self.mock_agent_bay, "test_context")
        
        # Mock list to return empty list
        with patch.object(service, 'list', return_value=[]):
            with self.assertRaises(ValueError) as context:
                service.update("ext_nonexistent", "/path/to/updated.zip")
            
            self.assertIn("not found in the context", str(context.exception))
    
    def test_delete_extension_success(self):
        """Test successful extension deletion."""
        mock_delete_result = Mock()
        mock_delete_result.success = True
        
        self.mock_context_service.delete_file.return_value = mock_delete_result
        
        service = ExtensionsService(self.mock_agent_bay, "test_context")
        result = service.delete("ext_123")
        
        self.assertTrue(result)
        self.mock_context_service.delete_file.assert_called_once()
    
    def test_delete_extension_failure(self):
        """Test extension deletion failure."""
        mock_delete_result = Mock()
        mock_delete_result.success = False
        
        self.mock_context_service.delete_file.return_value = mock_delete_result
        
        service = ExtensionsService(self.mock_agent_bay, "test_context")
        result = service.delete("ext_123")
        
        self.assertFalse(result)
    
    def test_create_extension_option(self):
        """Test creation of ExtensionOption."""
        service = ExtensionsService(self.mock_agent_bay, "test_context")
        
        ext_option = service.create_extension_option(["ext_1", "ext_2"])
        
        self.assertIsInstance(ext_option, ExtensionOption)
        self.assertEqual(ext_option.context_id, "ctx_test_123")
        self.assertEqual(ext_option.extension_ids, ["ext_1", "ext_2"])
    
    def test_create_extension_option_empty_ids(self):
        """Test ExtensionOption creation with empty extension IDs."""
        service = ExtensionsService(self.mock_agent_bay, "test_context")
        
        with self.assertRaises(ValueError):
            service.create_extension_option([])
    
    def test_cleanup_auto_created_context(self):
        """Test cleanup of auto-created context."""
        service = ExtensionsService(self.mock_agent_bay, "test_context")
        service.auto_created = True
        
        self.mock_context_service.delete.return_value = True
        
        result = service.cleanup()
        
        self.assertTrue(result)
        self.mock_context_service.delete.assert_called_once_with(self.mock_context)
    
    def test_cleanup_not_auto_created(self):
        """Test cleanup when context was not auto-created."""
        service = ExtensionsService(self.mock_agent_bay, "test_context")
        service.auto_created = False
        
        result = service.cleanup()
        
        self.assertTrue(result)
        self.mock_context_service.delete.assert_not_called()
    
    def test_cleanup_failure(self):
        """Test cleanup failure."""
        service = ExtensionsService(self.mock_agent_bay, "test_context")
        service.auto_created = True
        
        self.mock_context_service.delete.return_value = False
        
        result = service.cleanup()
        
        self.assertFalse(result)


class TestExtensionIntegration(unittest.TestCase):
    """Integration tests for extension functionality."""
    
    def setUp(self):
        """Set up integration test fixtures."""
        self.mock_agent_bay = Mock()
        self.mock_context_service = Mock()
        self.mock_agent_bay.context = self.mock_context_service
        
        # Mock successful context creation
        self.mock_context = Mock()
        self.mock_context.id = "ctx_integration_test"
        
        self.mock_context_result = Mock()
        self.mock_context_result.success = True
        self.mock_context_result.context = self.mock_context
        
        self.mock_context_service.get.return_value = self.mock_context_result
    
    @patch('os.path.exists')
    @patch('builtins.open', create=True)
    @patch('requests.put')
    def test_full_extension_workflow(self, mock_put, mock_open, mock_exists):
        """Test complete extension workflow: create, list, update, delete."""
        # Setup mocks
        mock_exists.return_value = True
        mock_put.return_value.status_code = 200
        
        # Mock file upload URL
        mock_url_result = Mock()
        mock_url_result.success = True
        mock_url_result.url = "https://presigned-url.com"
        self.mock_context_service.get_file_upload_url.return_value = mock_url_result
        
        # Create service
        service = ExtensionsService(self.mock_agent_bay, "integration_test")
        
        # 1. Create extension
        extension = service.create("/path/to/test.zip")
        self.assertIsInstance(extension, Extension)
        
        # Store the created extension for later mocking
        created_extension = Mock()
        created_extension.id = extension.id
        created_extension.name = extension.name
        
        # 2. Mock list to return the created extension
        with patch.object(service, 'list', return_value=[created_extension]):
            extensions = service.list()
            self.assertEqual(len(extensions), 1)

            # 3. Create extension option
            ext_option = service.create_extension_option([extension.id])
            self.assertIsInstance(ext_option, ExtensionOption)
            self.assertTrue(ext_option.validate())

            # 4. Update extension (using the same mock)
            updated_ext = service.update(extension.id, "/path/to/updated.zip")
            self.assertEqual(updated_ext.id, extension.id)
        
        # 5. Delete extension
        deleted = service.delete(extension.id)
        self.assertTrue(deleted)
        
        # 6. Cleanup
        cleanup_result = service.cleanup()
        self.assertTrue(cleanup_result)


if __name__ == '__main__':
    unittest.main()