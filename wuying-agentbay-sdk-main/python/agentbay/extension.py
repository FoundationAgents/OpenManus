import os
import uuid
import time
import requests
from typing import TYPE_CHECKING, List, Optional

from agentbay.exceptions import AgentBayError
from agentbay.model.response import OperationResult
from agentbay.logger import get_logger

if TYPE_CHECKING:
    from agentbay.agentbay import AgentBay
    from agentbay.context import ContextService

# Initialize logger for this module
logger = get_logger("extension")

# ==============================================================================
# Constants
# ==============================================================================
EXTENSIONS_BASE_PATH = "/tmp/extensions"

# ==============================================================================
# 1. Data Models
# ==============================================================================
class Extension:
    """Represents a browser extension as a cloud resource."""
    def __init__(self, id: str, name: str, created_at: Optional[str] = None):
        self.id = id
        self.name = name
        self.created_at = created_at # Retrieved from the cloud


class ExtensionOption:
    """
    Configuration options for browser extension integration.
    
    This class encapsulates the necessary parameters for setting up
    browser extension synchronization and context management.
    
    Attributes:
        context_id (str): ID of the extension context for browser extensions
        extension_ids (List[str]): List of extension IDs to be loaded/synchronized
    """
    
    def __init__(self, context_id: str, extension_ids: List[str]):
        """
        Initialize ExtensionOption with context and extension configuration.
        
        Args:
            context_id (str): ID of the extension context for browser extensions.
                             This should match the context where extensions are stored.
            extension_ids (List[str]): List of extension IDs to be loaded in the browser session.
                                     Each ID should correspond to a valid extension in the context.
        
        Raises:
            ValueError: If context_id is empty or extension_ids is empty.
        """
        if not context_id or not context_id.strip():
            raise ValueError("context_id cannot be empty")
        
        if not extension_ids or len(extension_ids) == 0:
            raise ValueError("extension_ids cannot be empty")
        
        self.context_id = context_id
        self.extension_ids = extension_ids
    
    def __repr__(self) -> str:
        """String representation of ExtensionOption."""
        return f"ExtensionOption(context_id='{self.context_id}', extension_ids={self.extension_ids})"
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"Extension Config: {len(self.extension_ids)} extension(s) in context '{self.context_id}'"
    
    def validate(self) -> bool:
        """
        Validate the extension option configuration.
        
        Returns:
            bool: True if configuration is valid, False otherwise.
        """
        try:
            # Check context_id
            if not self.context_id or not self.context_id.strip():
                return False
            
            # Check extension_ids
            if not self.extension_ids or len(self.extension_ids) == 0:
                return False
            
            # Check that all extension IDs are non-empty strings
            for ext_id in self.extension_ids:
                if not isinstance(ext_id, str) or not ext_id.strip():
                    return False
            
            return True
        except Exception:
            return False

# ==============================================================================
# 2. Core Service Class (Scoped Stateless Model)
# ==============================================================================

class ExtensionsService:
    """
    Provides methods to manage user browser extensions.
    This service integrates with the existing context functionality for file operations.
    
    **Usage** (Simplified - Auto-detection):
    ```python
    # Service automatically detects if context exists and creates if needed
    extensions_service = ExtensionsService(agent_bay, "browser_extensions")
    
    # Or use with empty context_id to auto-generate context name
    extensions_service = ExtensionsService(agent_bay)  # Uses default generated name
    
    # Use the service immediately
    extension = extensions_service.create("/path/to/plugin.zip")
    ```
    
    **Integration with ExtensionOption (Simplified)**:
    ```python
    # Create extensions and configure for browser sessions
    extensions_service = ExtensionsService(agent_bay, "my_extensions")
    ext1 = extensions_service.create("/path/to/ext1.zip")
    ext2 = extensions_service.create("/path/to/ext2.zip")
    
    # Create extension option for browser integration (no context_id needed!)
    ext_option = extensions_service.create_extension_option([ext1.id, ext2.id])
    
    # Use with BrowserContext for session creation
    browser_context = BrowserContext(
        context_id="browser_session",
        auto_upload=True,
        extension_option=ext_option  # All extension config encapsulated
    )
    ```
    
    **Context Management**:
    - If context_id provided and exists: Uses the existing context
    - If context_id provided but doesn't exist: Creates context with provided name
    - If context_id empty or not provided: Generates default name and creates context
    - No need to manually manage context creation
    """

    def __init__(self, agent_bay: "AgentBay", context_id: str = ""):
        """
        Initializes the ExtensionsService with a context.

        Args:
            agent_bay (AgentBay): The AgentBay client instance.
            context_id (str, optional): The context ID or name. If empty or not provided,
                                       a default context name will be generated automatically.
                                       If the context doesn't exist, it will be automatically created.
                             
        Note:
            The service automatically detects if the context exists. If not,
            it creates a new context with the provided name or a generated default name.
        """
        self.agent_bay = agent_bay
        self.context_service: "ContextService" = agent_bay.context
        
        # Generate default context name if context_id is empty
        if not context_id or context_id.strip() == "":
            import time
            context_id = f"extensions-{int(time.time())}"
            logger.info(f"Generated default context name: {context_id}")
        
        # Context doesn't exist, create it
        context_result = self.context_service.get(context_id, create=True)
        if not context_result.success or not context_result.context:
            raise AgentBayError(f"Failed to create extension repository context: {context_id}")
        
        self.extension_context = context_result.context
        self.context_id = self.extension_context.id
        self.context_name = context_id
        self.auto_created = True

    def _upload_to_cloud(self, local_path: str, remote_path: str):
        """
        An internal helper method that encapsulates the flow of "get upload URL for a specific path and upload".
        Uses the existing context service for file operations.

        Args:
            local_path (str): The path to the local file.
            remote_path (str): The path of the file in context storage.
        
        Raises:
            AgentBayError: If getting the credential or uploading fails.
        """
        # 1. Get upload URL using context service
        try:
            url_result = self.context_service.get_file_upload_url(self.context_id, remote_path);
            if not url_result.success or not url_result.url:
                raise AgentBayError(f"Failed to get upload URL: {url_result.url if url_result.url else 'No URL returned'}")
            
            pre_signed_url = url_result.url
        except Exception as e:
            raise AgentBayError(f"An error occurred while requesting the upload URL: {e}") from e

        # 2. Use the presigned URL to upload the file directly
        try:
            with open(local_path, 'rb') as f:
                response = requests.put(pre_signed_url, data=f)
                response.raise_for_status()  # This will raise an HTTPError if the status is 4xx or 5xx
        except requests.exceptions.RequestException as e:
            raise AgentBayError(f"An error occurred while uploading the file: {e}") from e

    def list(self) -> List[Extension]:
        """
        Lists all available browser extensions within this context from the cloud.
        Uses the context service to list files under the extensions directory.
        """
        try:
            # Use context service to list files in the extensions directory
            file_list_result = self.context_service.list_files(
                context_id=self.context_id,
                parent_folder_path=EXTENSIONS_BASE_PATH,
                page_number=1,
                page_size=100  # Reasonable limit for extensions
            )

            if not file_list_result.success:
                raise AgentBayError("Failed to list extensions: Context file listing failed.")

            extensions = []
            for file_entry in file_list_result.entries:
                # Extract the extension ID from the file name
                extension_id = file_entry.file_name
                extensions.append(Extension(
                    id=extension_id,
                    name=file_entry.file_name,
                    created_at=file_entry.gmt_create
                ))
            return extensions
        except Exception as e:
            raise AgentBayError(f"An error occurred while listing browser extensions: {e}") from e

    def create(self, local_path: str) -> Extension:
        """Uploads a new browser extension from a local path into the current context."""
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"The specified local file was not found: {local_path}")
        
        # Determine the ID and cloud path before uploading
        # Validate file type - only ZIP format is supported
        file_extension = os.path.splitext(local_path)[1].lower()
        if file_extension != '.zip':
            raise ValueError(f"Unsupported plugin format '{file_extension}'. Only ZIP format (.zip) is supported.")
        
        extension_id = f"ext_{uuid.uuid4().hex}{file_extension}"
        extension_name = os.path.basename(local_path)
        remote_path = f"{EXTENSIONS_BASE_PATH}/{extension_id}"

        # Use the helper method to perform the cloud upload
        self._upload_to_cloud(local_path, remote_path)
        
        # Upload implies creation. Return a locally constructed object with basic info.
        return Extension(id=extension_id, name=extension_name)

    def update(self, extension_id: str, new_local_path: str) -> Extension:
        """Updates an existing browser extension in the current context with a new file."""
        if not os.path.exists(new_local_path):
            raise FileNotFoundError(f"The specified new local file was not found: {new_local_path}")

        # Validate that the extension exists by checking the file list
        existing_extensions = {ext.id: ext for ext in self.list()}
        if extension_id not in existing_extensions:
            raise ValueError(f"Browser extension with ID '{extension_id}' not found in the context. Cannot update.")

        remote_path = f"{EXTENSIONS_BASE_PATH}/{extension_id}"
        
        # Use the helper method to perform the cloud upload (overwrite)
        self._upload_to_cloud(new_local_path, remote_path)

        return Extension(id=extension_id, name=os.path.basename(new_local_path))

    def _get_extension_info(self, extension_id: str) -> Optional[Extension]:
        """
        Gets detailed information about a specific browser extension.
        
        Args:
            extension_id (str): The ID of the extension to get info for.
            
        Returns:
            Optional[Extension]: Extension object if found, None otherwise.
        """
        try:
            extensions = self.list()
            for ext in extensions:
                if ext.id == extension_id:
                    return ext
            return None
        except Exception as e:
            logger.error(f"An error occurred while getting extension info for '{extension_id}': {e}")
            return None

    def cleanup(self) -> bool:
        """
        Cleans up the auto-created context if it was created by this service.
        
        Returns:
            bool: True if cleanup was successful or not needed, False if cleanup failed.
            
        Note:
            This method only works if the context was auto-created by this service.
            For existing contexts, no cleanup is performed.
        """
        if not self.auto_created:
            # Context was not auto-created by this service, no cleanup needed
            return True
            
        try:
            delete_result = self.context_service.delete(self.extension_context)
            if delete_result:
                logger.info(f"Extension context deleted: {self.context_name} (ID: {self.context_id})")
                return True
            else:
                logger.warning(f"Failed to delete extension context: {self.context_name}")
                return False
        except Exception as e:
            logger.warning(f"Failed to delete extension context: {e}")
            return False

    def delete(self, extension_id: str) -> bool:
        """Deletes a browser extension from the current context."""
        remote_path = f"{EXTENSIONS_BASE_PATH}/{extension_id}"
        try:
            # Use context service to delete the file
            delete_result = self.context_service.delete_file(self.context_id, remote_path)
            
            return delete_result.success
        except Exception as e:
            logger.error(f"An error occurred while deleting browser extension '{extension_id}': {e}")
            return False
    
    def create_extension_option(self, extension_ids: List[str]) -> ExtensionOption:
        """
        Create an ExtensionOption for the current context with specified extension IDs.
        
        This is a convenience method that creates an ExtensionOption using the current
        service's context_id and the provided extension IDs. This option can then be
        used with BrowserContext for browser session creation.
        
        Args:
            extension_ids (List[str]): List of extension IDs to include in the option.
                                     These should be extensions that exist in the current context.
        
        Returns:
            ExtensionOption: Configuration object for browser extension integration.
        
        Raises:
            ValueError: If extension_ids is empty or invalid.
            
        Example:
            ```python
            # Create extensions
            ext1 = extensions_service.create("/path/to/ext1.zip")
            ext2 = extensions_service.create("/path/to/ext2.zip")
            
            # Create extension option for browser integration
            ext_option = extensions_service.create_extension_option([ext1.id, ext2.id])
            
            # Use with BrowserContext
            browser_context = BrowserContext(
                context_id="browser_session",
                auto_upload=True,
                extension_context_id=ext_option.context_id,
                extension_ids=ext_option.extension_ids
            )
            ```
        """
        return ExtensionOption(
            context_id=self.context_id,
            extension_ids=extension_ids
        )
