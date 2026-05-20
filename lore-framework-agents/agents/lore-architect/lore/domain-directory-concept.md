A "domain directory" is the top-level working directory containing agent repos and any other repositories or data relevant to a work domain.

**Structure:**
```
domain-dir/
├── agent-repo-1/            # Agent repos (one or more)
├── agent-repo-2/
├── other-repos/             # Any other domain content
└── .claude/commands/        # Optional registered agent boot commands
```

**Key properties:**
- The user always runs Claude from the domain directory root
- Agents have visibility across the entire domain — all sibling repos
- `lore-framework/` no longer needs to be a sibling — it's installed as a plugin
- Multiple agent repos can coexist
- Sibling repo layout chosen over git submodules for simplicity

**Plugin vs old setup:**
Previously `lore-framework/` lived in the domain as a sibling repo and commands were copied to `.claude/commands/` during setup. Now the plugin is installed via the marketplace and no setup step is needed.
