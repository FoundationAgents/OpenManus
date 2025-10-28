import unittest
from unittest.mock import MagicMock

from agentbay.application.application import (
    ApplicationManager,
    AppOperationResult,
    InstalledApp,
    InstalledAppListResult,
    Process,
    ProcessListResult,
)
from agentbay.model import OperationResult


class TestApplicationApi(unittest.TestCase):
    def setUp(self):
        self.mock_session = MagicMock()
        self.app_manager = ApplicationManager(self.mock_session)

    def test_get_installed_apps_success(self):
        self.app_manager._call_mcp_tool = MagicMock(
            return_value=OperationResult(
                request_id="request-123",
                success=True,
                data="""[
    {
        "name" : "美团",
        "start_cmd" : "monkey -p com.sankuai.meituan -c android.intent.category.LAUNCHER 1",
        "stop_cmd" : "am force-stop com.sankuai.meituan",
        "work_directory" : ""
    },
    {
        "name" : "小红书",
        "start_cmd" : "monkey -p com.xingin.xhs -c android.intent.category.LAUNCHER 1",
        "stop_cmd" : "am force-stop com.xingin.xhs",
        "work_directory" : ""
    },
    {
        "name" : "高德地图",
        "start_cmd" : "monkey -p com.autonavi.minimap -c android.intent.category.LAUNCHER 1",
        "stop_cmd" : "am force-stop com.autonavi.minimap",
        "work_directory" : ""
    }
]""",
            )
        )
        result = self.app_manager.get_installed_apps(True, True, True)
        self.assertIsInstance(result, InstalledAppListResult)
        self.assertTrue(result.success)
        self.assertEqual(len(result.data), 3)
        self.assertIsInstance(result.data[0], InstalledApp)
        self.assertEqual(result.data[0].name, "美团")
        self.assertEqual(result.data[1].name, "小红书")
        self.assertEqual(result.data[2].name, "高德地图")
        self.assertEqual(result.request_id, "request-123")

    def test_get_installed_apps_failure(self):
        self.app_manager._call_mcp_tool = MagicMock(
            return_value=OperationResult(
                request_id="request-123",
                success=False,
                error_message="Failed to get installed apps",
            )
        )
        result = self.app_manager.get_installed_apps(True, False, True)
        self.assertIsInstance(result, InstalledAppListResult)
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Failed to get installed apps")
        self.assertEqual(result.request_id, "request-123")

    def test_start_app_success(self):
        self.app_manager._call_mcp_tool = MagicMock(
            return_value=OperationResult(
                request_id="request-123",
                success=True,
                data="""[
            {
                "pname": "com.autonavi.minimap",
                "pid": 12345,
                "cmdline": "monkey -p com.autonavi.minimap -c android.intent.category.LAUNCHER 1"
            }
        ]""",
            )
        )
        result = self.app_manager.start_app(
            "monkey -p com.autonavi.minimap -c android.intent.category.LAUNCHER 1"
        )
        self.assertIsInstance(result, ProcessListResult)
        self.assertTrue(result.success)
        self.assertEqual(len(result.data), 1)
        self.assertEqual(result.data[0].pname, "com.autonavi.minimap")
        self.assertEqual(result.data[0].pid, 12345)
        self.assertEqual(
            result.data[0].cmdline,
            "monkey -p com.autonavi.minimap -c android.intent.category.LAUNCHER 1",
        )
        self.assertEqual(result.request_id, "request-123")

    def test_start_app_failure(self):
        self.app_manager._call_mcp_tool = MagicMock(
            return_value=OperationResult(
                request_id="request-123",
                success=False,
                error_message="Failed to start app",
            )
        )
        result = self.app_manager.start_app(
            "monkey -p com.autonavi.minimap -c android.intent.category.LAUNCHER 1"
        )
        self.assertIsInstance(result, ProcessListResult)
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Failed to start app")
        self.assertEqual(result.request_id, "request-123")

    def test_stop_app_by_cmd_success(self):
        self.app_manager._call_mcp_tool = MagicMock(
            return_value=OperationResult(
                request_id="request-123", success=True, data=None
            )
        )
        result = self.app_manager.stop_app_by_cmd("am force-stop com.autonavi.minimap")
        self.assertIsInstance(result, AppOperationResult)
        self.assertTrue(result.success)
        self.assertEqual(result.request_id, "request-123")

    def test_stop_app_by_cmd_failure(self):
        self.app_manager._call_mcp_tool = MagicMock(
            return_value=OperationResult(
                request_id="request-123",
                success=False,
                error_message="Failed to stop app",
            )
        )
        result = self.app_manager.stop_app_by_cmd("am force-stop com.autonavi.minimap")
        self.assertIsInstance(result, AppOperationResult)
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Failed to stop app")
        self.assertEqual(result.request_id, "request-123")

    def test_stop_app_by_pname_success(self):
        self.app_manager._call_mcp_tool = MagicMock(
            return_value=OperationResult(
                request_id="request-123", success=True, data=None
            )
        )
        result = self.app_manager.stop_app_by_pname("com.autonavi.minimap")
        self.assertIsInstance(result, AppOperationResult)
        self.assertTrue(result.success)
        self.assertEqual(result.request_id, "request-123")

    def test_stop_app_by_pname_failure(self):
        self.app_manager._call_mcp_tool = MagicMock(
            return_value=OperationResult(
                request_id="request-123",
                success=False,
                error_message="Failed to stop app by pname",
            )
        )
        result = self.app_manager.stop_app_by_pname("com.autonavi.minimap")
        self.assertIsInstance(result, AppOperationResult)
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Failed to stop app by pname")
        self.assertEqual(result.request_id, "request-123")

    def test_stop_app_by_pid_success(self):
        self.app_manager._call_mcp_tool = MagicMock(
            return_value=OperationResult(
                request_id="request-123", success=True, data=None
            )
        )
        result = self.app_manager.stop_app_by_pid(12345)
        self.assertIsInstance(result, AppOperationResult)
        self.assertTrue(result.success)
        self.assertEqual(result.request_id, "request-123")

    def test_stop_app_by_pid_failure(self):
        self.app_manager._call_mcp_tool = MagicMock(
            return_value=OperationResult(
                request_id="request-123",
                success=False,
                error_message="Failed to stop app by pid",
            )
        )
        result = self.app_manager.stop_app_by_pid(12345)
        self.assertIsInstance(result, AppOperationResult)
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Failed to stop app by pid")
        self.assertEqual(result.request_id, "request-123")

    def test_list_visible_apps_success(self):
        self.app_manager._call_mcp_tool = MagicMock(
            return_value=OperationResult(
                request_id="request-123",
                success=True,
                data="""[
            {"pname": "com.autonavi.minimap", "pid": 12345, "cmdline": "cmd1"},
            {"pname": "com.xingin.xhs", "pid": 23456, "cmdline": "cmd2"}
        ]""",
            )
        )
        result = self.app_manager.list_visible_apps()
        self.assertIsInstance(result, ProcessListResult)
        self.assertTrue(result.success)
        self.assertEqual(len(result.data), 2)
        self.assertIsInstance(result.data[0], Process)
        self.assertEqual(result.data[0].pname, "com.autonavi.minimap")
        self.assertEqual(result.data[1].pname, "com.xingin.xhs")
        self.assertEqual(result.request_id, "request-123")

    def test_list_visible_apps_failure(self):
        self.app_manager._call_mcp_tool = MagicMock(
            return_value=OperationResult(
                request_id="request-123",
                success=False,
                error_message="Failed to list visible apps",
            )
        )
        result = self.app_manager.list_visible_apps()
        self.assertIsInstance(result, ProcessListResult)
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Failed to list visible apps")
        self.assertEqual(result.request_id, "request-123")

    def test_start_app_with_activity_success(self):
        self.app_manager._call_mcp_tool = MagicMock(
            return_value=OperationResult(
                request_id="request-123",
                success=True,
                data="""[
            {
                "pname": "com.autonavi.minimap",
                "pid": 12345,
                "cmdline": "monkey -p com.autonavi.minimap -c android.intent.category.LAUNCHER 1"
            }
        ]""",
            )
        )
        result = self.app_manager.start_app(
            "monkey -p com.autonavi.minimap -c android.intent.category.LAUNCHER 1",
            activity=".SettingsActivity",
        )
        self.assertIsInstance(result, ProcessListResult)
        self.assertTrue(result.success)
        self.assertEqual(len(result.data), 1)
        self.assertEqual(result.data[0].pname, "com.autonavi.minimap")
        self.assertEqual(result.data[0].pid, 12345)
        self.assertEqual(
            result.data[0].cmdline,
            "monkey -p com.autonavi.minimap -c android.intent.category.LAUNCHER 1",
        )
        self.assertEqual(result.request_id, "request-123")

        # Verify that activity was passed correctly
        self.app_manager._call_mcp_tool.assert_called_with(
            "start_app",
            {
                "start_cmd": "monkey -p com.autonavi.minimap -c android.intent.category.LAUNCHER 1",
                "activity": ".SettingsActivity",
            },
        )

    def test_start_app_with_activity_and_work_directory(self):
        self.app_manager._call_mcp_tool = MagicMock(
            return_value=OperationResult(
                request_id="request-456",
                success=True,
                data="""[
            {
                "pname": "com.xingin.xhs",
                "pid": 23456,
                "cmdline": "monkey -p com.xingin.xhs -c android.intent.category.LAUNCHER 1"
            }
        ]""",
            )
        )
        result = self.app_manager.start_app(
            "monkey -p com.xingin.xhs -c android.intent.category.LAUNCHER 1",
            work_directory="/storage/emulated/0",
            activity="com.xingin.xhs/.MainActivity",
        )
        self.assertTrue(result.success)
        self.assertEqual(len(result.data), 1)
        self.assertEqual(result.data[0].pname, "com.xingin.xhs")

        # Verify all parameters were passed correctly
        self.app_manager._call_mcp_tool.assert_called_with(
            "start_app",
            {
                "start_cmd": "monkey -p com.xingin.xhs -c android.intent.category.LAUNCHER 1",
                "work_directory": "/storage/emulated/0",
                "activity": "com.xingin.xhs/.MainActivity",
            },
        )


if __name__ == "__main__":
    unittest.main()
