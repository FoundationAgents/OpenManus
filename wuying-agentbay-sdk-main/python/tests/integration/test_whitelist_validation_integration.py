import os
import pytest
from agentbay import AgentBay, ContextSync, SyncPolicy, BWList, WhiteList, CreateSessionParams


def get_test_api_key():
    api_key = os.environ.get("AGENTBAY_API_KEY")
    if not api_key:
        pytest.skip("AGENTBAY_API_KEY environment variable not set")
    return api_key


class TestWhiteListValidationIntegration:
    @pytest.fixture
    def agent_bay(self):
        api_key = get_test_api_key()
        return AgentBay(api_key=api_key)

    @pytest.fixture
    def test_context(self, agent_bay):
        context_result = agent_bay.context.get("test-wildcard-validation", create=True)
        assert context_result.success
        yield context_result.context
        agent_bay.context.delete(context_result.context)

    def test_create_session_with_wildcard_in_path_should_fail(self, agent_bay, test_context):
        with pytest.raises(ValueError) as exc_info:
            policy = SyncPolicy(
                bw_list=BWList(
                    white_lists=[WhiteList(path="*.json")]
                )
            )
            context_sync = ContextSync.new(test_context.id, "/tmp/data", policy)
            agent_bay.create(CreateSessionParams(context_syncs=[context_sync]))
        
        assert "Wildcard patterns are not supported in path" in str(exc_info.value)
        assert "*.json" in str(exc_info.value)

    def test_create_session_with_wildcard_in_exclude_paths_should_fail(self, agent_bay, test_context):
        with pytest.raises(ValueError) as exc_info:
            policy = SyncPolicy(
                bw_list=BWList(
                    white_lists=[WhiteList(path="/src", exclude_paths=["*.log"])]
                )
            )
            context_sync = ContextSync.new(test_context.id, "/tmp/data", policy)
            agent_bay.create(CreateSessionParams(context_syncs=[context_sync]))
        
        assert "Wildcard patterns are not supported in exclude_paths" in str(exc_info.value)
        assert "*.log" in str(exc_info.value)

    def test_create_session_with_glob_pattern_should_fail(self, agent_bay, test_context):
        with pytest.raises(ValueError) as exc_info:
            policy = SyncPolicy(
                bw_list=BWList(
                    white_lists=[WhiteList(path="/data/*")]
                )
            )
            context_sync = ContextSync.new(test_context.id, "/tmp/data", policy)
            agent_bay.create(CreateSessionParams(context_syncs=[context_sync]))
        
        assert "Wildcard patterns are not supported in path" in str(exc_info.value)
        assert "/data/*" in str(exc_info.value)

    def test_create_session_with_double_asterisk_should_fail(self, agent_bay, test_context):
        with pytest.raises(ValueError) as exc_info:
            policy = SyncPolicy(
                bw_list=BWList(
                    white_lists=[WhiteList(path="/logs/**/*.txt")]
                )
            )
            context_sync = ContextSync.new(test_context.id, "/tmp/data", policy)
            agent_bay.create(CreateSessionParams(context_syncs=[context_sync]))
        
        assert "Wildcard patterns are not supported in path" in str(exc_info.value)

    def test_create_session_with_valid_paths_should_succeed(self, agent_bay, test_context):
        policy = SyncPolicy(
            bw_list=BWList(
                white_lists=[
                    WhiteList(path="/src", exclude_paths=["/node_modules", "/temp"])
                ]
            )
        )
        context_sync = ContextSync.new(test_context.id, "/tmp/data", policy)
        session_result = agent_bay.create(CreateSessionParams(context_syncs=[context_sync]))
        
        assert session_result.success
        assert session_result.session is not None
        
        agent_bay.delete(session_result.session)

    def test_validation_happens_before_api_call(self, agent_bay, test_context):
        with pytest.raises(ValueError) as exc_info:
            policy = SyncPolicy(
                bw_list=BWList(
                    white_lists=[WhiteList(path="*.txt")]
                )
            )
            ContextSync.new(test_context.id, "/tmp/data", policy)
        
        assert "Wildcard patterns are not supported in path" in str(exc_info.value)
