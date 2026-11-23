import json
from pathlib import Path

import pytest


_CONFIG_PATH = Path(__file__).parents[2] / "config" / "config.toml"
_CREATED_TEST_CONFIG = not _CONFIG_PATH.exists()
if _CREATED_TEST_CONFIG:
    _CONFIG_PATH.write_text(
        '[llm]\nmodel = "test"\nbase_url = "http://localhost"\napi_key = "test"\n'
        '\n[daytona]\ndaytona_api_key = "test"\n'
    )

try:
    from app.tool.chart_visualization.data_visualization import DataVisualization
finally:
    if _CREATED_TEST_CONFIG:
        _CONFIG_PATH.unlink()


@pytest.mark.asyncio
@pytest.mark.parametrize("failed", [False, True])
@pytest.mark.parametrize("include_skipped", [False, True])
async def test_insight_results_refer_to_the_selected_chart(
    tmp_path, monkeypatch, failed, include_skipped
):
    tool = DataVisualization.model_construct(llm=None)
    skipped = tmp_path / "skipped.html"
    selected = tmp_path / "selected.html"
    skipped.write_text("untouched", encoding="utf-8")
    selected.write_text("original", encoding="utf-8")
    info = tmp_path / "insights.json"
    entries = [{"chartPath": str(selected), "insights_id": [1]}]
    if include_skipped:
        entries.insert(0, {"chartPath": str(skipped)})
    info.write_text(json.dumps(entries), encoding="utf-8")
    invocations = []

    async def invoke(self, **kwargs):
        invocations.append(kwargs)
        if failed:
            return {"error": "render failed"}
        selected.write_text("updated", encoding="utf-8")
        return {"chart_path": str(selected)}

    monkeypatch.setattr(DataVisualization, "invoke_vmind", invoke)

    result = await tool.execute(json_path=str(info), tool_type="insight")

    assert len(invocations) == 1
    assert invocations[0]["file_name"] == "selected"
    assert invocations[0]["insights_id"] == [1]
    assert str(selected) in result["observation"]
    assert str(skipped) not in result["observation"]
    assert skipped.read_text(encoding="utf-8") == "untouched"
    if failed:
        assert result["success"] is False
        assert "render failed" in result["observation"]
    else:
        assert selected.read_text(encoding="utf-8") == "updated"
