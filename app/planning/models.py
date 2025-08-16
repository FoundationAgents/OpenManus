from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class Step(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    title: str
    description: str
    depends_on: List[str] = Field(default_factory=list)
    tool: str  # ex.: "browser_use", "python", "code_interpreter"
    inputs: Dict[str, Any] = Field(default_factory=dict)
    expected_output: str


class Plan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str
    objective: str
    constraints: List[str] = Field(default_factory=list)
    success_criteria: List[str] = Field(default_factory=list)
    steps: List[Step]
    notes: Optional[str] = None
