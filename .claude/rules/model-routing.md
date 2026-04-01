# Model Routing Preferences

When choosing which model to use for different tasks:

- **Commits, git operations, simple file reads**: prefer Haiku (fast, cheap)
- **Implementation after a plan is established**: prefer Sonnet (capable, moderate cost)
- **Architecture planning, design discussions, complex debugging**: prefer Opus (best quality)
- **Exploring codebase, searching for patterns**: prefer Sonnet

If the user seems to be in a different work phase than what the current model is suited for,
suggest switching models with `/model <model-name>`.
