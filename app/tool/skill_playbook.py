"""Concise built-in workflow skills inspired by modern coding-agent harnesses."""

from __future__ import annotations

from typing import Literal, Optional

from app.skills import load_skills
from app.task_context import get_current_workspace
from app.tool.base import BaseTool, ToolResult


SkillName = Literal[
    "coding",
    "debugging",
    "frontend",
    "testing",
    "research",
    "security",
    "latex",
    "data",
    "git",
]


SKILLS: dict[str, str] = {
    "coding": """Coding workflow:
1. Run codebase_overview, then glob/grep/read_files to locate the exact files.
2. Make the smallest coherent change that satisfies the request.
3. Prefer existing project patterns over new abstractions.
4. Run the narrowest meaningful verification command, then broader checks if shared behavior changed.
5. Inspect outputs/diffs before terminate.""",
    "debugging": """Debugging workflow:
1. Reproduce or locate the failing symptom in logs/tests.
2. Trace from error message to owner code using grep and read_files.
3. Fix the cause, not only the visible error.
4. Re-run the failing command and inspect the new output.
5. If still failing, change strategy; do not repeat the same failed command blindly.""",
    "frontend": """Frontend workflow:
1. Inspect existing components, styling utilities, and routing before changing UI.
2. Keep controls stable, scrollable, and responsive; avoid text overflow.
3. Use existing icons/components where available.
4. Build and, when possible, verify in browser with screenshots or visible output.
5. Report any remaining visual risk clearly.""",
    "testing": """Testing workflow:
1. Discover project test commands from package/config files.
2. Run targeted tests first, then build/type checks.
3. Treat test environment failures separately from product failures.
4. If tests cannot run, capture the exact blocker and still run syntax/static checks where possible.""",
    "research": """Research workflow:
1. Browse current primary sources for unstable or external facts.
2. Cross-check important claims with more than one reliable source.
3. Distill findings into decisions or implementation constraints.
4. Avoid copying large external text; adapt concepts to this codebase.""",
    "security": """Security workflow:
1. Avoid exposing secrets, tokens, private keys, or local credentials.
2. Validate filesystem paths and user-controlled inputs.
3. Avoid destructive commands unless explicitly required.
4. Prefer least-privilege behavior and clear failure states.
5. Run available security/static checks when touching auth, shell, paths, or network code.""",
    "latex": """LaTeX workflow:
1. Write .tex and assets into the current conversation workspace.
2. Compile with latexmk or pdflatex in nonstop mode.
3. Confirm a PDF exists before claiming success.
4. If no PDF exists, inspect the .log and fix/report the exact error.""",
    "data": """Data workflow:
1. Inspect file schemas/samples before transforming.
2. Use Python for structured parsing instead of ad hoc shell when data is nontrivial.
3. Save outputs in the workspace with clear filenames.
4. Validate counts, columns, and sample rows after transformation.""",
    "git": """Git workflow:
1. Inspect git status before edits if the task touches repository state.
2. Never revert unrelated user changes.
3. Keep diffs scoped and review them before finishing.
4. Do not commit or push unless explicitly asked.""",
}


class SkillPlaybook(BaseTool):
    """Return concise workflow guidance for a specific task type."""

    name: str = "skill_playbook"
    description: str = (
        "Load a concise built-in or .openhands skill. Use this before specialized "
        "coding, debugging, frontend, testing, research, security, latex, data, docker, "
        "or git work. Pass list_available=true to see skills discovered in the current workspace."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "skill": {
                "type": "string",
                "description": "Built-in skill name or discovered .openhands skill name.",
            },
            "task": {
                "type": "string",
                "description": "Optional current task summary for context.",
            },
            "list_available": {
                "type": "boolean",
                "description": "Return available built-in and .openhands skills instead of loading one.",
            },
        },
        "required": [],
    }

    async def execute(
        self,
        skill: Optional[str] = None,
        task: Optional[str] = None,
        list_available: bool = False,
        **kwargs,
    ) -> ToolResult:
        workspace = get_current_workspace()
        discovered = load_skills(workspace)
        if list_available:
            names = [f"- {name} (built-in)" for name in sorted(SKILLS.keys())]
            names.extend(
                f"- {item.name} ({item.type}; triggers: {', '.join(item.triggers or []) or 'always'})"
                for item in discovered
            )
            return ToolResult(output="Available skills:\n" + "\n".join(names))

        if not skill:
            return ToolResult(error="skill is required unless list_available=true")

        text = SKILLS.get(skill)
        if not text:
            found = next((item for item in discovered if item.name == skill), None)
            if found is not None:
                text = found.body
        if not text:
            return ToolResult(error=f"Unknown skill: {skill}. Try list_available=true.")
        if task:
            text = f"Task focus: {task}\n\n{text}"
        return ToolResult(output=text)
