import sys
from pathlib import Path

import pytest

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# Test configuration
@pytest.fixture(scope="session")
def test_data_dir():
    """Provide test data directory path."""
    return Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def mock_graphrag_dir(tmp_path_factory):
    """Create a mock GraphRAG directory for testing."""
    tmp_dir = tmp_path_factory.mktemp("graphrag_test")

    # Create mock yh_rag structure
    yh_rag = tmp_dir / "yh_rag"
    yh_rag.mkdir()

    # Create settings.yaml
    settings_content = """
llm:
  api_key: test_key
  type: openai_chat
  model: gpt-4

embeddings:
  llm:
    api_key: test_key
    type: openai_embedding
    model: text-embedding-ada-002

input:
  type: file
  file_type: text
  base_dir: "input"
  file_encoding: utf-8
  file_pattern: ".*\\.txt$"

cache:
  type: file
  base_dir: "cache"

storage:
  type: file
  base_dir: "output"

reporting:
  type: file
  base_dir: "reports"

entity_extraction:
  prompt: "prompts/entity_extraction.txt"
  entity_types: [person, organization, geo]
  max_gleanings: 0

summarize_descriptions:
  prompt: "prompts/summarize_descriptions.txt"
  max_length: 500

claim_extraction:
  prompt: "prompts/claim_extraction.txt"
  description: "Any claims or facts that could be relevant to information discovery."
  max_gleanings: 0

community_report:
  prompt: "prompts/community_report.txt"
  max_length: 2000
  max_input_length: 8000

cluster_graph:
  max_cluster_size: 10

embed_graph:
  enabled: false

umap:
  enabled: false

snapshots:
  graphml: false
  raw_entities: false
  top_level_nodes: false

local_search:
  text_unit_prop: 0.5
  community_prop: 0.1
  conversation_history_max_turns: 5
  top_k_mapped_entities: 10
  top_k_relationships: 10
  max_tokens: 12000

global_search:
  max_tokens: 12000
  data_max_tokens: 12000
  map_max_tokens: 1000
  reduce_max_tokens: 2000
  concurrency: 32
"""

    (yh_rag / "settings.yaml").write_text(settings_content)

    # Create output directory structure
    output_dir = yh_rag / "output"
    output_dir.mkdir()

    # Create input directory
    input_dir = yh_rag / "input"
    input_dir.mkdir()

    # Create sample input file
    (input_dir / "sample.txt").write_text("This is a sample document for testing GraphRAG functionality.")

    return str(yh_rag)


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "requires_graphrag: mark test as requiring GraphRAG installation")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names."""
    for item in items:
        # Add integration marker to integration tests
        if "integration" in item.nodeid.lower():
            item.add_marker(pytest.mark.integration)

        # Add slow marker to tests that might be slow
        if any(keyword in item.name.lower() for keyword in ["real_", "integration_", "full_"]):
            item.add_marker(pytest.mark.slow)

        # Add requires_graphrag marker to tests that need GraphRAG
        if "real_graphrag" in item.name.lower() or "real_yh_rag" in item.name.lower():
            item.add_marker(pytest.mark.requires_graphrag)
