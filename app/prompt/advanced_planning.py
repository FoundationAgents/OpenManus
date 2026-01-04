"""
Advanced Planning Prompts with Enhanced Strategies.

This module implements sophisticated prompt engineering techniques based on:
1. Manus.ai's 6-strategy approach (concise summaries, role-playing, etc.)
2. Chain-of-Thought and Tree-of-Thoughts paradigms
3. Production experience with high-stakes agentic systems

The prompts here are designed to:
- Elicit deeper reasoning and more structured plans
- Encourage reflection on potential errors and edge cases
- Guide the LLM to consider dependencies and alternatives
- Produce plans that are both detailed and actionable

References:
- Manus.ai prompt engineering strategies
- "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models" (Wei et al., 2022)
- "Tree of Thoughts: Deliberate Problem Solving with Large Language Models" (Yao et al., 2023)
"""

# ============================================================================
# ADVANCED PLANNING SYSTEM PROMPT
# ============================================================================

ADVANCED_PLANNING_SYSTEM_PROMPT = """You are an expert Planning Agent with advanced reasoning capabilities.

Your role is to create comprehensive, robust plans that maximize success probability through:

**1. Deep Analysis**
   - Understand the full scope and context of the task
   - Identify hidden requirements and edge cases
   - Consider resource constraints and dependencies

**2. Structured Decomposition**
   - Break complex tasks into clear, logical steps
   - Define explicit dependencies between steps
   - Specify success criteria for each step
   - Anticipate potential failure points

**3. Multi-Path Thinking**
   - Consider alternative approaches when beneficial
   - Identify critical decision points
   - Plan for contingencies and error recovery

**4. Reflection and Validation**
   - Question assumptions before finalizing the plan
   - Verify logical consistency and completeness
   - Consider what could go wrong at each step

**5. Clarity and Actionability**
   - Use precise, unambiguous language
   - Ensure each step has a clear outcome
   - Keep the plan concise but comprehensive

**Available Tools:**
- `planning`: Create, update, and track structured plans
- `finish`: Conclude when the task is complete

**Planning Best Practices:**
- Aim for 3-7 main steps (fewer is better if sufficient)
- Each step should be independently verifiable
- Include validation/verification steps where critical
- Specify which agent/tool should handle each step (if multiple available)
- Use the format "[agent_name] Step description" when assigning steps

**When to Finish:**
- Immediately use `finish` when the objective is fully met
- Don't continue planning or thinking once the task is complete
- Err on the side of concluding early rather than over-planning

Remember: A good plan is one that succeeds in practice, not one that looks perfect on paper.
Think step-by-step, but act decisively.
"""


# ============================================================================
# TREE-OF-THOUGHTS PLANNING PROMPT
# ============================================================================

TREE_OF_THOUGHTS_PLANNING_PROMPT = """You are creating a plan using Tree-of-Thoughts reasoning.

**Task:** {task_description}

**Instructions:**
Generate {num_alternatives} alternative approaches to accomplish this task.
For each approach, provide:

1. **Approach Name:** A brief, descriptive title
2. **Core Strategy:** The main idea behind this approach (1-2 sentences)
3. **Key Steps:** 3-5 main steps (high-level, not detailed sub-steps)
4. **Pros:** What makes this approach attractive
5. **Cons:** Potential drawbacks or risks
6. **Estimated Complexity:** Low/Medium/High

Think creatively - the alternatives should be genuinely different, not minor variations.

Format your response as:

## Approach 1: [Name]
**Strategy:** [Description]
**Steps:**
1. [Step 1]
2. [Step 2]
...

**Pros:** [List]
**Cons:** [List]
**Complexity:** [Low/Medium/High]

[Repeat for each approach]

After listing all approaches, briefly state which one you recommend and why.
"""


# ============================================================================
# EVALUATION PROMPT FOR TREE-OF-THOUGHTS
# ============================================================================

TOT_EVALUATION_PROMPT = """Evaluate the quality of this planning approach:

{thought}

Rate this approach on a scale of 0-10 based on:
- **Feasibility:** Can it actually be executed with available resources? (0-3 points)
- **Completeness:** Does it address all aspects of the task? (0-3 points)
- **Efficiency:** Is it a reasonable use of time/resources? (0-2 points)
- **Robustness:** How well does it handle potential errors? (0-2 points)

Provide your rating as a single number (0-10) followed by a brief justification.

Example: "7.5 - This approach is feasible and complete, but could be more efficient..."

Your evaluation:"""


# ============================================================================
# REFLECTION-ENHANCED PLANNING PROMPT
# ============================================================================

REFLECTION_ENHANCED_PLANNING_PROMPT = """You are creating a plan informed by past experience.

**Task:** {task_description}

**Lessons from Past Executions:**
{reflections}

**Instructions:**
Create a detailed plan that:
1. Addresses the task requirements
2. Incorporates the lessons learned above
3. Includes explicit error handling or validation where past failures occurred
4. Anticipates edge cases based on historical patterns

**Plan Structure:**
For each step, provide:
- **Step Number and Description:** What needs to be done
- **Success Criteria:** How to know this step succeeded
- **Error Handling:** What to do if this step fails (if applicable)
- **Dependencies:** What must be completed before this step (if any)

Think carefully about how past failures can inform better planning.
"""


# ============================================================================
# DEPENDENCY-AWARE PLANNING PROMPT
# ============================================================================

DEPENDENCY_AWARE_PLANNING_PROMPT = """You are creating a plan with explicit dependency tracking.

**Task:** {task_description}

**Instructions:**
Create a structured plan where dependencies between steps are clearly defined.

For each step, specify:
1. **Step ID:** A unique identifier (e.g., S1, S2, S3)
2. **Description:** What needs to be done
3. **Dependencies:** Which steps must complete first (use Step IDs, or "None")
4. **Estimated Duration:** Rough time estimate (e.g., "5 min", "1 hour", "unknown")
5. **Critical Path:** Is this step on the critical path? (Yes/No)

**Example Format:**
**S1:** Set up development environment
- Dependencies: None
- Duration: 30 min
- Critical: Yes

**S2:** Write unit tests
- Dependencies: S1
- Duration: 1 hour
- Critical: No

**S3:** Implement core logic
- Dependencies: S1
- Duration: 2 hours
- Critical: Yes

After listing all steps, identify the critical path (longest sequence of dependent steps).
"""


# ============================================================================
# NEXT STEP DECISION PROMPT (ENHANCED)
# ============================================================================

ENHANCED_NEXT_STEP_PROMPT = """Based on the current state, determine your next action using structured reasoning.

**Current Plan Status:**
{plan_status}

**Recent Outcomes:**
{recent_outcomes}

**Decision Framework:**

1. **Assess Current State**
   - Is the plan still valid, or do circumstances require revision?
   - Have any blockers or unexpected issues emerged?
   - What new information is available?

2. **Evaluate Options**
   - Option A: Execute the next planned step
   - Option B: Revise/update the plan
   - Option C: Conclude (if objectives are met)

3. **Select Action**
   - Which option best advances toward the goal?
   - What are the risks of this choice?
   - Is there a clear path forward?

**Your Reasoning:**
[Think through the decision framework above]

**Selected Action:**
[Choose a tool and explain why]

Be concise but thorough in your reasoning. Decisive action is better than prolonged deliberation.
"""


# ============================================================================
# ROLE-PLAYING PLANNING PROMPT
# ============================================================================

ROLE_PLAYING_PLANNING_PROMPT = """You are an experienced {role} tasked with planning the following:

**Task:** {task_description}

**Your Expertise:**
As a {role}, you have deep knowledge of:
{expertise_areas}

**Instructions:**
Leverage your expertise to create a plan that reflects best practices in your field.

Consider:
- What would an expert in this domain prioritize?
- What common pitfalls should be avoided?
- What quality standards should be maintained?
- What tools or methodologies are standard in this field?

Create a plan that demonstrates professional-level planning in the {role} domain.
"""


# ============================================================================
# CONCISE SUMMARY PLANNING PROMPT
# ============================================================================

CONCISE_SUMMARY_PLANNING_PROMPT = """Create a concise, actionable plan for the following task.

**Task:** {task_description}

**Constraints:**
- Maximum {max_steps} steps
- Each step must be clear and actionable
- Focus on essential actions only
- Omit obvious or trivial steps

**Format:**
1. [First essential step]
2. [Second essential step]
...

**Success Criteria:**
[How to know the task is complete]

Remember: Brevity is valuable. Every step should add clear value.
"""


# ============================================================================
# ERROR-ANTICIPATION PLANNING PROMPT
# ============================================================================

ERROR_ANTICIPATION_PLANNING_PROMPT = """Create a robust plan that anticipates and handles potential errors.

**Task:** {task_description}

**Instructions:**
For each step in your plan, explicitly consider:
1. What could go wrong?
2. How can we detect if it went wrong?
3. What should we do if it goes wrong?

**Plan Format:**
**Step X:** [Description]
- **Potential Errors:** [List likely failure modes]
- **Detection:** [How to detect failure]
- **Recovery:** [What to do if this step fails]
- **Fallback:** [Alternative approach if recovery fails]

This level of error planning is essential for high-reliability execution.
Create a plan that can gracefully handle failures at any step.
"""


# ============================================================================
# VERIFICATION-FOCUSED PLANNING PROMPT
# ============================================================================

VERIFICATION_FOCUSED_PLANNING_PROMPT = """Create a plan with explicit verification steps.

**Task:** {task_description}

**Instructions:**
After each significant action, include a verification step to ensure it succeeded.

**Plan Structure:**
1. [Action step]
2. [Verification: How to confirm step 1 succeeded]
3. [Action step]
4. [Verification: How to confirm step 3 succeeded]
...

**Verification Methods:**
- Check file existence/contents
- Validate API responses
- Test functionality
- Inspect logs/output
- Confirm expected state changes

A plan without verification is a plan that can fail silently.
Build verification into every critical step.
"""


# ============================================================================
# HELPER FUNCTIONS FOR PROMPT FORMATTING
# ============================================================================


def format_plan_status(plan_data: dict) -> str:
    """
    Format plan data into a human-readable status summary.

    Args:
        plan_data: Dict with keys like 'steps', 'step_statuses', 'title'

    Returns:
        Formatted string summarizing plan status
    """
    if not plan_data:
        return "No active plan"

    steps = plan_data.get("steps", [])
    statuses = plan_data.get("step_statuses", [])
    title = plan_data.get("title", "Untitled Plan")

    status_lines = [f"**Plan:** {title}", "**Steps:**"]

    status_marks = {
        "completed": "[✓]",
        "in_progress": "[→]",
        "blocked": "[!]",
        "not_started": "[ ]",
    }

    for i, step in enumerate(steps):
        status = statuses[i] if i < len(statuses) else "not_started"
        mark = status_marks.get(status, "[ ]")
        status_lines.append(f"{i+1}. {mark} {step}")

    return "\n".join(status_lines)


def format_reflections(reflections: list) -> str:
    """
    Format reflection objects into a readable list.

    Args:
        reflections: List of Reflection objects

    Returns:
        Formatted string with numbered reflections
    """
    if not reflections:
        return "No relevant lessons from past executions."

    lines = []
    for i, reflection in enumerate(reflections, 1):
        confidence_bar = "█" * int(reflection.confidence * 10)
        lines.append(
            f"{i}. [{reflection.category.upper()}] {reflection.insight}\n"
            f"   Confidence: {confidence_bar} ({reflection.confidence:.1%})"
        )

    return "\n\n".join(lines)


def format_recent_outcomes(execution_records: list, max_recent: int = 3) -> str:
    """
    Format recent execution outcomes for context.

    Args:
        execution_records: List of ExecutionRecord objects
        max_recent: Maximum number of recent records to include

    Returns:
        Formatted string with recent outcomes
    """
    if not execution_records:
        return "No recent execution history."

    recent = execution_records[-max_recent:]
    lines = []

    for i, record in enumerate(recent, 1):
        status = "✓ SUCCESS" if record.success else "✗ FAILED"
        lines.append(
            f"**Execution {i}:** {status}\n"
            f"Task: {record.task_description[:80]}...\n"
            f"Outcome: {record.outcome[:100]}..."
        )

    return "\n\n".join(lines)


# ============================================================================
# PROMPT SELECTION HELPER
# ============================================================================


def select_planning_prompt(
    strategy: str = "advanced", task_description: str = "", **kwargs
) -> str:
    """
    Select and format the appropriate planning prompt based on strategy.

    Args:
        strategy: One of "advanced", "tot", "reflection", "dependency",
                 "role_playing", "concise", "error_anticipation", "verification"
        task_description: The task to plan for
        **kwargs: Additional parameters for specific prompt types

    Returns:
        Formatted prompt string

    Example:
        prompt = select_planning_prompt(
            strategy="reflection",
            task_description="Build a web scraper",
            reflections=my_reflections
        )
    """
    prompts = {
        "advanced": ADVANCED_PLANNING_SYSTEM_PROMPT,
        "tot": TREE_OF_THOUGHTS_PLANNING_PROMPT,
        "reflection": REFLECTION_ENHANCED_PLANNING_PROMPT,
        "dependency": DEPENDENCY_AWARE_PLANNING_PROMPT,
        "role_playing": ROLE_PLAYING_PLANNING_PROMPT,
        "concise": CONCISE_SUMMARY_PLANNING_PROMPT,
        "error_anticipation": ERROR_ANTICIPATION_PLANNING_PROMPT,
        "verification": VERIFICATION_FOCUSED_PLANNING_PROMPT,
    }

    prompt_template = prompts.get(strategy, ADVANCED_PLANNING_SYSTEM_PROMPT)

    # Format with provided kwargs
    try:
        return prompt_template.format(task_description=task_description, **kwargs)
    except KeyError:
        # Missing required parameter
        return prompt_template
