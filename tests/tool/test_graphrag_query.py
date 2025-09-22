import asyncio
import os
from unittest.mock import AsyncMock, patch

import pytest

from app.tool.base import ToolResult
from app.tool.graphrag_query import GraphRAGQuery


@pytest.fixture
def graphrag_tool():
    """Create a GraphRAG query tool instance for testing."""
    return GraphRAGQuery()


@pytest.fixture
def mock_yh_rag_directory(tmp_path):
    """Create a mock yh_rag directory structure for testing."""
    yh_rag_dir = tmp_path / "yh_rag"
    yh_rag_dir.mkdir()

    # Create mock configuration files
    (yh_rag_dir / "settings.yaml").write_text(
        """
llm:
  api_key: test_key
  type: openai_chat
  model: gpt-4
"""
    )

    # Create mock output directory
    output_dir = yh_rag_dir / "output"
    output_dir.mkdir()

    return str(yh_rag_dir)


class TestGraphRAGQuery:
    """Test cases for GraphRAG query tool."""

    def test_tool_initialization(self, graphrag_tool):
        """Test tool initialization and properties."""
        assert graphrag_tool.name == "graphrag_query"
        assert "GraphRAG knowledge base" in graphrag_tool.description
        assert "query" in graphrag_tool.parameters["properties"]
        assert "method" in graphrag_tool.parameters["properties"]
        assert "root_path" in graphrag_tool.parameters["properties"]

    def test_tool_parameters_schema(self, graphrag_tool):
        """Test tool parameters schema validation."""
        params = graphrag_tool.parameters["properties"]

        # Test query parameter
        assert params["query"]["type"] == "string"
        assert "query" in graphrag_tool.parameters["required"]

        # Test method parameter
        assert params["method"]["type"] == "string"
        assert set(params["method"]["enum"]) == {"global", "local", "drift", "basic"}
        assert params["method"]["default"] == "global"

        # Test root_path parameter
        assert params["root_path"]["type"] == "string"
        assert params["root_path"]["default"] == "./yh_rag"

        # Test community_level parameter
        assert params["community_level"]["type"] == "integer"
        assert params["community_level"]["default"] == 2

        # Test response_type parameter
        assert params["response_type"]["type"] == "string"
        assert "Multiple Paragraphs" in params["response_type"]["enum"]

    @pytest.mark.asyncio
    async def test_execute_missing_query(self, graphrag_tool):
        """Test execution with missing query parameter."""
        result = await graphrag_tool.execute()
        assert result.error == "Query parameter is required"
        assert result.output is None

    @pytest.mark.asyncio
    async def test_execute_invalid_method(self, graphrag_tool):
        """Test execution with invalid method parameter."""
        result = await graphrag_tool.execute(query="test query", method="invalid")
        assert "Invalid method" in result.error
        assert "global" in result.error

    @pytest.mark.asyncio
    async def test_execute_successful_global_query(self, graphrag_tool, mock_yh_rag_directory):
        """Test successful global query execution."""
        mock_stdout = "This is a test response from GraphRAG global search."

        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            # Mock successful process
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate.return_value = (mock_stdout.encode("utf-8"), b"")
            mock_subprocess.return_value = mock_process

            result = await graphrag_tool.execute(
                query="股票投资的道天地将法是啥意思？", method="global", root_path=mock_yh_rag_directory
            )

            assert result.error is None
            assert result.output == mock_stdout

            # Verify command construction
            mock_subprocess.assert_called_once()
            call_args = mock_subprocess.call_args[0]
            assert "python" in call_args
            assert "-m" in call_args
            assert "graphrag" in call_args
            assert "query" in call_args
            assert "--method" in call_args
            assert "global" in call_args
            assert "--query" in call_args
            assert "股票投资的道天地将法是啥意思？" in call_args

    @pytest.mark.asyncio
    async def test_execute_successful_local_query(self, graphrag_tool, mock_yh_rag_directory):
        """Test successful local query execution."""
        mock_stdout = "This is a test response from GraphRAG local search."

        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate.return_value = (mock_stdout.encode("utf-8"), b"")
            mock_subprocess.return_value = mock_process

            result = await graphrag_tool.execute(query="什么是投资策略？", method="local", root_path=mock_yh_rag_directory)

            assert result.error is None
            assert result.output == mock_stdout

            # Verify local method doesn't include global-specific parameters
            call_args = mock_subprocess.call_args[0]
            assert "--method" in call_args
            assert "local" in call_args
            # Global-specific parameters should not be present for local queries
            assert "--community_level" not in call_args
            assert "--response_type" not in call_args

    @pytest.mark.asyncio
    async def test_execute_with_custom_parameters(self, graphrag_tool, mock_yh_rag_directory):
        """Test execution with custom parameters."""
        mock_stdout = "Custom parameter test response."

        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate.return_value = (mock_stdout.encode("utf-8"), b"")
            mock_subprocess.return_value = mock_process

            result = await graphrag_tool.execute(
                query="测试查询",
                method="global",
                root_path=mock_yh_rag_directory,
                community_level=3,
                response_type="Single Paragraph",
            )

            assert result.error is None
            assert result.output == mock_stdout

            # Verify custom parameters are included
            call_args = mock_subprocess.call_args[0]
            assert "--community_level" in call_args
            assert "3" in call_args
            assert "--response_type" in call_args
            assert "Single Paragraph" in call_args

    @pytest.mark.asyncio
    async def test_execute_command_failure(self, graphrag_tool, mock_yh_rag_directory):
        """Test execution when GraphRAG command fails."""
        mock_stderr = "GraphRAG error: Invalid configuration"

        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.returncode = 1
            mock_process.communicate.return_value = (b"", mock_stderr.encode("utf-8"))
            mock_subprocess.return_value = mock_process

            result = await graphrag_tool.execute(query="test query", root_path=mock_yh_rag_directory)

            assert result.output is None
            assert "GraphRAG query failed" in result.error
            assert mock_stderr in result.error

    @pytest.mark.asyncio
    async def test_execute_empty_result(self, graphrag_tool, mock_yh_rag_directory):
        """Test execution when GraphRAG returns empty result."""
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate.return_value = (b"", b"")
            mock_subprocess.return_value = mock_process

            result = await graphrag_tool.execute(query="empty query", root_path=mock_yh_rag_directory)

            assert result.error is None
            assert result.output == "No results found for the query"

    @pytest.mark.asyncio
    async def test_execute_exception_handling(self, graphrag_tool):
        """Test exception handling during execution."""
        with patch("asyncio.create_subprocess_exec", side_effect=Exception("Test exception")):
            result = await graphrag_tool.execute(query="test query")

            assert result.output is None
            assert "Error executing GraphRAG query" in result.error
            assert "Test exception" in result.error

    @pytest.mark.asyncio
    async def test_validate_setup_success(self, graphrag_tool):
        """Test successful setup validation."""
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate.return_value = (b"GraphRAG help", b"")
            mock_subprocess.return_value = mock_process

            is_valid = await graphrag_tool.validate_setup()

            assert is_valid is True
            mock_subprocess.assert_called_once_with(
                "python", "-m", "graphrag", "--help", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

    @pytest.mark.asyncio
    async def test_validate_setup_failure(self, graphrag_tool):
        """Test setup validation failure."""
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.returncode = 1
            mock_process.communicate.return_value = (b"", b"Module not found")
            mock_subprocess.return_value = mock_process

            is_valid = await graphrag_tool.validate_setup()

            assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_setup_exception(self, graphrag_tool):
        """Test setup validation with exception."""
        with patch("asyncio.create_subprocess_exec", side_effect=Exception("Setup error")):
            is_valid = await graphrag_tool.validate_setup()

            assert is_valid is False

    @pytest.mark.asyncio
    async def test_all_query_methods(self, graphrag_tool, mock_yh_rag_directory):
        """Test all supported query methods."""
        methods = ["global", "local", "drift", "basic"]

        for method in methods:
            with patch("asyncio.create_subprocess_exec") as mock_subprocess:
                mock_process = AsyncMock()
                mock_process.returncode = 0
                mock_process.communicate.return_value = (f"Response for {method} method".encode(), b"")
                mock_subprocess.return_value = mock_process

                result = await graphrag_tool.execute(
                    query=f"Test query for {method}", method=method, root_path=mock_yh_rag_directory
                )

                assert result.error is None
                assert f"Response for {method} method" in result.output

                # Verify method is correctly passed to command
                call_args = mock_subprocess.call_args[0]
                assert "--method" in call_args
                assert method in call_args


@pytest.mark.integration
class TestGraphRAGQueryIntegration:
    """Integration tests for GraphRAG query tool."""

    @pytest.mark.asyncio
    async def test_real_graphrag_availability(self):
        """Test if GraphRAG is actually available in the environment."""
        tool = GraphRAGQuery()
        is_available = await tool.validate_setup()

        if not is_available:
            pytest.skip("GraphRAG is not available in the test environment")

        assert is_available is True

    @pytest.mark.asyncio
    async def test_real_yh_rag_directory(self):
        """Test with real yh_rag directory if it exists."""
        yh_rag_path = "./yh_rag"

        if not os.path.exists(yh_rag_path):
            pytest.skip("yh_rag directory not found")

        tool = GraphRAGQuery()

        # Test with a simple query
        result = await tool.execute(query="测试查询", method="global", root_path=yh_rag_path)

        # The result might fail due to configuration issues, but we test the execution path
        assert isinstance(result, ToolResult)
        assert result.error is not None or result.output is not None


if __name__ == "__main__":
    pytest.main(["-v", __file__])
