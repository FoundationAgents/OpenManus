from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
import re


class UploadStrategy(Enum):
    """Upload strategy for context synchronization"""

    UPLOAD_BEFORE_RESOURCE_RELEASE = "UploadBeforeResourceRelease"


class DownloadStrategy(Enum):
    """Download strategy for context synchronization"""

    DOWNLOAD_ASYNC = "DownloadAsync"


class Lifecycle(Enum):
    """Lifecycle options for recycle policy"""
    
    LIFECYCLE_1DAY = "Lifecycle_1Day"
    LIFECYCLE_3DAYS = "Lifecycle_3Days"
    LIFECYCLE_5DAYS = "Lifecycle_5Days"
    LIFECYCLE_10DAYS = "Lifecycle_10Days"
    LIFECYCLE_15DAYS = "Lifecycle_15Days"
    LIFECYCLE_30DAYS = "Lifecycle_30Days"
    LIFECYCLE_90DAYS = "Lifecycle_90Days"
    LIFECYCLE_180DAYS = "Lifecycle_180Days"
    LIFECYCLE_360DAYS = "Lifecycle_360Days"
    LIFECYCLE_FOREVER = "Lifecycle_Forever"


@dataclass
class UploadPolicy:
    """
    Defines the upload policy for context synchronization

    Attributes:
        auto_upload: Enables automatic upload
        upload_strategy: Defines the upload strategy
    """

    auto_upload: bool = True
    upload_strategy: UploadStrategy = UploadStrategy.UPLOAD_BEFORE_RESOURCE_RELEASE

    @classmethod
    def default(cls):
        """Creates a new upload policy with default values"""
        return cls()

    def __dict__(self):
        return {
            "autoUpload": self.auto_upload,
            "uploadStrategy": (
                self.upload_strategy.value if self.upload_strategy else None
            ),
        }


@dataclass
class DownloadPolicy:
    """
    Defines the download policy for context synchronization

    Attributes:
        auto_download: Enables automatic download
        download_strategy: Defines the download strategy
    """

    auto_download: bool = True
    download_strategy: DownloadStrategy = DownloadStrategy.DOWNLOAD_ASYNC

    @classmethod
    def default(cls):
        """Creates a new download policy with default values"""
        return cls()

    def __dict__(self):
        return {
            "autoDownload": self.auto_download,
            "downloadStrategy": (
                self.download_strategy.value if self.download_strategy else None
            ),
        }


@dataclass
class DeletePolicy:
    """
    Defines the delete policy for context synchronization

    Attributes:
        sync_local_file: Enables synchronization of local file deletions
    """

    sync_local_file: bool = True

    @classmethod
    def default(cls):
        """Creates a new delete policy with default values"""
        return cls()

    def __dict__(self):
        return {"syncLocalFile": self.sync_local_file}


@dataclass
class ExtractPolicy:
    """
    Defines the extract policy for context synchronization

    Attributes:
        extract: Enables file extraction
        delete_src_file: Enables deletion of source file after extraction
    """

    extract: bool = True
    delete_src_file: bool = True
    extract_current_folder: bool = False

    @classmethod
    def default(cls):
        """Creates a new extract policy with default values"""
        return cls()

    def __dict__(self):
        return {"extract": self.extract, "deleteSrcFile": self.delete_src_file, "extractToCurrentFolder": self.extract_current_folder}


@dataclass
class RecyclePolicy:
    """
    Defines the recycle policy for context synchronization
    
    Attributes:
        lifecycle: Defines how long the context data should be retained
            Available options:
            - LIFECYCLE_1DAY: Keep data for 1 day
            - LIFECYCLE_3DAYS: Keep data for 3 days
            - LIFECYCLE_5DAYS: Keep data for 5 days
            - LIFECYCLE_10DAYS: Keep data for 10 days
            - LIFECYCLE_15DAYS: Keep data for 15 days
            - LIFECYCLE_30DAYS: Keep data for 30 days
            - LIFECYCLE_90DAYS: Keep data for 90 days
            - LIFECYCLE_180DAYS: Keep data for 180 days
            - LIFECYCLE_360DAYS: Keep data for 360 days
            - LIFECYCLE_FOREVER: Keep data permanently (default)
        paths: Specifies which directories or files should be subject to the recycle policy
            Rules:
            - Must use exact directory/file paths
            - Wildcard patterns (* ? [ ]) are NOT supported
            - Empty string "" means apply to all paths in the context
            - Multiple paths can be specified as a list
            Default: [""] (applies to all paths)
    """
    
    lifecycle: Lifecycle = Lifecycle.LIFECYCLE_FOREVER
    paths: List[str] = field(default_factory=lambda: [""])

    def __post_init__(self):
        """Validate lifecycle and paths configuration"""
        # Validate lifecycle value
        if not isinstance(self.lifecycle, Lifecycle):
            valid_values = [e.value for e in Lifecycle]
            raise ValueError(
                f"Invalid lifecycle value: {self.lifecycle}. "
                f"Valid values are: {', '.join(valid_values)}"
            )
        
        # Validate that paths don't contain wildcard patterns
        for path in self.paths:
            if path and path.strip() != "" and self._contains_wildcard(path):
                raise ValueError(
                    f"Wildcard patterns are not supported in recycle policy paths. Got: {path}. "
                    "Please use exact directory paths instead."
                )

    @staticmethod
    def _contains_wildcard(path: str) -> bool:
        """Check if path contains wildcard characters"""
        return bool(re.search(r'[*?\[\]]', path))

    @classmethod
    def default(cls):
        """Creates a new recycle policy with default values"""
        return cls()

    def __dict__(self):
        return {
            "lifecycle": self.lifecycle.value if self.lifecycle else None,
            "paths": self.paths
        }


@dataclass
class WhiteList:
    """
    Defines the white list configuration

    Attributes:
        path: Path to include in the white list
        exclude_paths: Paths to exclude from the white list
    """

    path: str = ""
    exclude_paths: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate that paths don't contain wildcard patterns"""
        if self._contains_wildcard(self.path):
            raise ValueError(
                f"Wildcard patterns are not supported in path. Got: {self.path}. "
                "Please use exact directory paths instead."
            )
        for exclude_path in self.exclude_paths:
            if self._contains_wildcard(exclude_path):
                raise ValueError(
                    f"Wildcard patterns are not supported in exclude_paths. Got: {exclude_path}. "
                    "Please use exact directory paths instead."
                )

    @staticmethod
    def _contains_wildcard(path: str) -> bool:
        """Check if path contains wildcard characters"""
        return bool(re.search(r'[*?\[\]]', path))

    def __dict__(self):
        return {"path": self.path, "excludePaths": self.exclude_paths}


@dataclass
class BWList:
    """
    Defines the black and white list configuration

    Attributes:
        white_lists: Defines the white lists
    """

    white_lists: List[WhiteList] = field(default_factory=list)

    def __dict__(self):
        return {
            "whiteLists": (
                [wl.__dict__() for wl in self.white_lists] if self.white_lists else []
            )
        }


@dataclass
class SyncPolicy:
    """
    Defines the synchronization policy

    Attributes:
        upload_policy: Defines the upload policy
        download_policy: Defines the download policy
        delete_policy: Defines the delete policy
        extract_policy: Defines the extract policy
        recycle_policy: Defines the recycle policy
        bw_list: Defines the black and white list
    """

    upload_policy: Optional[UploadPolicy] = None
    download_policy: Optional[DownloadPolicy] = None
    delete_policy: Optional[DeletePolicy] = None
    extract_policy: Optional[ExtractPolicy] = None
    recycle_policy: Optional[RecyclePolicy] = None
    bw_list: Optional[BWList] = None

    def __post_init__(self):
        """Post-initialization to ensure all policies have default values if not provided"""
        if self.upload_policy is None:
            self.upload_policy = UploadPolicy.default()
        if self.download_policy is None:
            self.download_policy = DownloadPolicy.default()
        if self.delete_policy is None:
            self.delete_policy = DeletePolicy.default()
        if self.extract_policy is None:
            self.extract_policy = ExtractPolicy.default()
        if self.recycle_policy is None:
            self.recycle_policy = RecyclePolicy.default()
        if self.bw_list is None:
            self.bw_list = BWList(white_lists=[WhiteList(path="", exclude_paths=[])])

    @classmethod
    def default(cls):
        """Creates a new sync policy with default values"""
        return cls(
            upload_policy=UploadPolicy.default(),
            download_policy=DownloadPolicy.default(),
            delete_policy=DeletePolicy.default(),
            extract_policy=ExtractPolicy.default(),
            recycle_policy=RecyclePolicy.default(),
            bw_list=BWList(white_lists=[WhiteList(path="", exclude_paths=[])]),
        )

    def __dict__(self):
        result = {}
        if self.upload_policy:
            result["uploadPolicy"] = self.upload_policy.__dict__()
        if self.download_policy:
            result["downloadPolicy"] = self.download_policy.__dict__()
        if self.delete_policy:
            result["deletePolicy"] = self.delete_policy.__dict__()
        if self.extract_policy:
            result["extractPolicy"] = self.extract_policy.__dict__()
        if self.recycle_policy:
            result["recyclePolicy"] = self.recycle_policy.__dict__()
        if self.bw_list:
            result["bwList"] = self.bw_list.__dict__()
        return result


@dataclass
class ContextSync:
    """
    Defines the context synchronization configuration

    Attributes:
        context_id: ID of the context to synchronize
        path: Path where the context should be mounted
        policy: Defines the synchronization policy
    """

    context_id: str
    path: str
    policy: Optional[SyncPolicy] = None

    @classmethod
    def new(cls, context_id: str, path: str, policy: Optional[SyncPolicy] = None):
        """Creates a new context sync configuration"""
        return cls(context_id=context_id, path=path, policy=policy)

    def with_policy(self, policy: SyncPolicy):
        """Sets the policy"""
        self.policy = policy
        return self