---
name: feature-implementer
description: This skill should be used when implementing new features following the Komorebi TDD workflow. It provides scaffolding, templates, and guidance for full-stack feature development.
tier: standard
model: auto
license: MIT
---

# Feature Implementer

## About This Skill

This skill accelerates feature implementation in the Komorebi project by providing:
- TDD workflow guidance (Red → Green → Refactor → Hammer)
- Code generation scaffolding for common patterns
- Backend and frontend templates
- Validation scripts to ensure conventions are followed

## When to Use

Invoke this skill when:
- Implementing a new CRUD feature
- Adding a new API endpoint with tests
- Creating a new React component with state management

**Example triggers:**
- "Implement a new feature for managing projects"
- "Create a new endpoint for chunk summarization"

## How to Use

1. **Generate Scaffold:** Use `scripts/generate_scaffold.py <feature_name>`
2. **Follow TDD Workflow:** See `references/tdd_workflow.md`
3. **Use Templates:** Copy from `assets/` as starting points
4. **Validate:** Use `scripts/validate_feature.py`

## Bundled Resources

### Scripts

- **`generate_scaffold.py`**: Creates directory structure and stubs
- **`validate_feature.py`**: Checks conventions compliance

### References

- **`tdd_workflow.md`**: Detailed TDD guidance (load when needed)
- **`api_patterns.md`**: FastAPI patterns (load when building APIs)
- **`component_patterns.md`**: React patterns (load when building UI)

### Assets

- **`api_templates/`**: CRUD endpoint templates
- **`component_templates/`**: React component templates

**Ready to implement features efficiently!**
