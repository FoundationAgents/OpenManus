import pytest
from agentbay import WhiteList


class TestWhiteListValidation:
    def test_valid_path_without_wildcard(self):
        wl = WhiteList(path="/src")
        assert wl.path == "/src"

    def test_valid_path_with_exclude_without_wildcard(self):
        wl = WhiteList(path="/src", exclude_paths=["/node_modules", "/temp"])
        assert wl.path == "/src"
        assert wl.exclude_paths == ["/node_modules", "/temp"]

    def test_path_with_asterisk_wildcard_raises_error(self):
        with pytest.raises(ValueError) as exc_info:
            WhiteList(path="/data/*")
        assert "Wildcard patterns are not supported in path" in str(exc_info.value)
        assert "/data/*" in str(exc_info.value)

    def test_path_with_double_asterisk_raises_error(self):
        with pytest.raises(ValueError) as exc_info:
            WhiteList(path="/logs/**/*.txt")
        assert "Wildcard patterns are not supported in path" in str(exc_info.value)

    def test_path_with_question_mark_raises_error(self):
        with pytest.raises(ValueError) as exc_info:
            WhiteList(path="/file?.txt")
        assert "Wildcard patterns are not supported in path" in str(exc_info.value)

    def test_path_with_brackets_raises_error(self):
        with pytest.raises(ValueError) as exc_info:
            WhiteList(path="/file[0-9].txt")
        assert "Wildcard patterns are not supported in path" in str(exc_info.value)

    def test_exclude_path_with_asterisk_raises_error(self):
        with pytest.raises(ValueError) as exc_info:
            WhiteList(path="/src", exclude_paths=["*.log"])
        assert "Wildcard patterns are not supported in exclude_paths" in str(exc_info.value)
        assert "*.log" in str(exc_info.value)

    def test_exclude_path_with_pattern_raises_error(self):
        with pytest.raises(ValueError) as exc_info:
            WhiteList(path="/src", exclude_paths=["/node_modules", "**/*.tmp"])
        assert "Wildcard patterns are not supported in exclude_paths" in str(exc_info.value)

    def test_glob_pattern_raises_error(self):
        with pytest.raises(ValueError) as exc_info:
            WhiteList(path="*.json")
        assert "Wildcard patterns are not supported in path" in str(exc_info.value)

    def test_empty_path_is_valid(self):
        wl = WhiteList(path="")
        assert wl.path == ""

    def test_empty_exclude_paths_is_valid(self):
        wl = WhiteList(path="/src", exclude_paths=[])
        assert wl.exclude_paths == []
