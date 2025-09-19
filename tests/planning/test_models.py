import pytest
from pydantic import ValidationError

from app.planning.models import Plan, Step


def test_extra_fields_forbidden():
    with pytest.raises(ValidationError):
        Step.model_validate(
            {
                "id": "s",
                "title": "t",
                "description": "d",
                "depends_on": [],
                "tool": "python",
                "inputs": {},
                "expected_output": "y",
                "extra": 123,  # deve falhar (extra='forbid')
            }
        )


def test_plan_basic_validate():
    s1 = Step(id="1", title="A", description="B", tool="python", expected_output="Z")
    p = Plan(version="1.0", objective="O", steps=[s1])
    assert p.objective == "O"
