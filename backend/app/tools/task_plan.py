"""create_task_plan tool — turn a goal into ordered subtasks.

Uses the model when one is provided, else a heuristic decomposition. Returns a
structured plan the orchestrator (and the user) can act on.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from .base import Tool


class TaskPlanInput(BaseModel):
    goal: str
    max_steps: int = Field(7, ge=1, le=20)


def heuristic_plan(goal: str, max_steps: int = 7) -> list[str]:
    """A generic decomposition skeleton — honest, not magic."""
    steps = [
        f"Clarify the objective and success criteria for: {goal}",
        "Identify required information, tools and constraints",
        "Gather inputs (web research / files / memory) if needed",
        "Draft an initial solution or answer",
        "Verify key claims and check edge cases",
        "Critique and revise for gaps, risks and clarity",
        "Finalize with sources, confidence and next actions",
    ]
    return steps[:max_steps]


class CreateTaskPlanTool(Tool):
    name = "create_task_plan"
    description = "Decompose a goal into an ordered list of actionable subtasks."
    InputModel = TaskPlanInput

    def execute(self, params: TaskPlanInput):
        steps = heuristic_plan(params.goal, params.max_steps)
        plan = [{"id": i + 1, "description": s, "done": False} for i, s in enumerate(steps)]
        return {"goal": params.goal, "steps": plan}, f"{len(plan)}-step plan"
