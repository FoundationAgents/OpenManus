# Agent Skills Feature

This document describes the Agent Skills feature in OpenManus, which allows you to extend agent capabilities with specialized knowledge and behaviors, similar to Claude's Skills system.

## Overview

Skills are markdown files that teach agents how to handle specific tasks. When you ask the agent something that matches a skill's purpose, the skill's instructions are automatically applied to guide the agent's behavior.

## Features

- **Automatic Activation**: Skills are automatically activated based on user request relevance
- **Multi-File Support**: Skills can reference supporting files for detailed documentation
- **Tool Restrictions**: Skills can limit which tools the agent can use
- **Progressive Disclosure**: Skills load supporting files only when needed
- **Manual Control**: Skills can be manually activated or deactivated
- **Forked Context**: Optional isolated execution context for complex skills

## Skill Structure

A skill consists of a `SKILL.md` file with YAML metadata and Markdown instructions:

```markdown
---
name: your-skill-name
description: What this skill does and when to use it
allowed-tools:
  - ToolName1
  - ToolName2
---

# Your Skill Title

Instructions for the agent follow here...
```

### Required Fields

- `name` (string, max 64 chars): Skill identifier (lowercase letters, numbers, hyphens only)
- `description` (string, max 1024 chars): What the skill does and when to use it

### Optional Fields

- `allowed-tools` (list): Tools the agent can use without asking permission
- `model` (string): LLM model to use when this skill is active
- `context` (enum): `"inline"` (default) or `"fork"` for isolated execution
- `agent` (string): Agent type to use with forked context
- `hooks` (dict): Lifecycle hooks (PreToolUse, PostToolUse, Stop)
- `user-invocable` (bool): Show in slash command menu (default: true)
- `disable-model-invocation` (bool): Prevent automatic activation (default: false)

## Where Skills Live

Skills are loaded from these locations (in priority order):

1. **Enterprise Skills**: Managed settings (not implemented yet)
2. **Personal Skills**: `~/.claude/skills/` - Your personal skills across all projects
3. **Project Skills**: `.claude/skills/` - Shared skills for this repository
4. **Config Skills**: `config/skills/` - Default location in OpenManus
5. **Plugin Skills**: Bundled with plugins

## Configuration

Skills are configured in `config/config.toml`:

```toml
[skills]
enabled = true                                    # Enable skills system
paths = [
    ".claude/skills",
    "config/skills"
]
auto_activate = true                             # Automatically activate relevant skills
threshold = 0.3                                # Minimum relevance threshold (0.0-1.0)
```

## Creating a Skill

### Simple Example

```markdown
---
name: code-review
description: Reviews code for quality, security, and best practices
---

When reviewing code:
1. Check for security vulnerabilities
2. Identify performance issues
3. Evaluate code quality and best practices
4. Provide actionable feedback with examples
```

### Multi-File Example

For complex skills, use progressive disclosure:

```
my-skill/
├── SKILL.md              # Required - overview and navigation
├── reference.md          # Detailed API docs - loaded when needed
└── examples.md           # Usage examples - loaded when needed
```

In `SKILL.md`, reference other files:

```markdown
## Quick Start

Basic instructions here.

## Additional Resources

- For complete API details, see [reference.md](reference.md)
- For usage examples, see [examples.md](examples.md)
```

## Using Skills

### Automatic Activation

Skills activate automatically when your request matches their description:

```bash
python main.py --prompt "Review the code in src/main.py for bugs"
# Automatically activates the code-review skill
```

### List Available Skills

```bash
python main.py --list-skills
```

### Manual Activation

Coming soon: Programmatic API for manual skill activation.

## Example Skills

Three example skills are included in `config/skills/`:

1. **code-review**: Code quality and security reviews
2. **documentation**: Writing README, API docs, and comments
3. **debugging**: Systematic debugging and error fixing

## Best Practices

1. **Write Clear Descriptions**: Include keywords users would naturally say
2. **Keep Under 500 Lines**: For optimal performance, use supporting files for detailed docs
3. **Use Progressive Disclosure**: Put essential info in SKILL.md, details in supporting files
4. **Test Your Skills**: Try with various user requests to ensure they trigger correctly
5. **Follow Markdown Standards**: Use proper headers, code blocks, and formatting

## Troubleshooting

### Skill Not Activating

Check the description includes relevant keywords. For example:
- **Poor**: "Helps with documents"
- **Good**: "Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files, forms, or document extraction."

### Skill Not Loading

1. Verify file path: `config/skills/my-skill/SKILL.md`
2. Check YAML syntax: Starts with `---` on line 1
3. Verify metadata: Has `name` and `description` fields
4. Run debug mode: Check logs for loading errors

### Multiple Skills Conflict

Make descriptions more specific:
- Differentiate by specific use cases
- Include unique trigger terms
- Use narrower scopes for similar skills

## Architecture

Skills integrate with the agent system through:

1. **Skill Discovery**: `app/skill_manager.py` discovers and loads skills from configured paths
2. **Schema**: `app/schema_skill.py` defines skill data models
3. **Config**: `app/config.py` includes SkillsSettings configuration
4. **Agent Integration**: `app/agent/manus.py` activates skills and injects prompts
5. **Main Entry**: `main.py` initializes skill manager before agent creation

## Future Enhancements

- [ ] Hook support for skill lifecycle events
- [ ] Forked context execution for isolation
- [ ] Skill versioning and updates
- [ ] Skill marketplace integration
- [ ] Skill development tools and validators
- [ ] Performance metrics and analytics

## References

- [Claude Skills Documentation](https://code.claude.com/docs/en/skills)
- [OpenManus Architecture](ARCHITECTURE.md)
