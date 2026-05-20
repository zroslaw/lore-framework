The `lr` plugin is distributed via a self-hosted Claude Code marketplace on GitHub.

## Marketplace setup

`.claude-plugin/marketplace.json` in the lore-framework repo root:
```json
{
  "name": "lore-framework",
  "version": "1.0.0",
  "repository": "https://github.com/zroslaw/lore-framework",
  "license": "MIT",
  "owner": { "name": "Yaroslav Roslaw" },
  "plugins": [
    {
      "name": "lr",
      "source": "./",
      "description": "Persistent knowledge system for AI agents",
      "version": "1.0.0",
      "repository": "https://github.com/zroslaw/lore-framework",
      "license": "MIT"
    }
  ]
}
```

Critical details:
- `source` must be `"./"` not `"."` — the trailing slash is required
- `version`, `repository`, `license` are required in the plugin entry (not just top-level)

## Installation (user)

```
/plugin marketplace add zroslaw/lore-framework
/plugin install lr@lore-framework
```

## Local development

```bash
claude --plugin-dir ./lore-framework
```

`/reload-plugins` picks up changes without restarting. Reports "0 skills" even when working — this is a display quirk.

## What does NOT work

`pluginDirs` in `.claude/settings.json` is not supported. There is no project-level persistent plugin configuration other than marketplace installation.
