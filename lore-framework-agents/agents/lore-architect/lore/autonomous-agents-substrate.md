# Autonomous Agents — Technical Substrate

Concrete building blocks identified during the 2026-04-26 brainstorm for running lore agents as autonomous background processes on macOS. Companion to `autonomous-agents-vision.md`.

## Process / persistence layer — tmux

- **tmux** holds shell sessions in a daemon independent of any terminal viewport. Detach (`Ctrl-b d`) without killing the process; reattach later.
- Each autonomous lore agent runs as `tmux new -d -s <agent-name> 'claude ...'` — fully headless start, no GUI required.
- Hierarchy: `session → windows → panes`.
- Inspection without attaching:
  - `tmux list-sessions`
  - `tmux list-panes -a -F '#{session_name} #{pane_pid} #{pane_current_command} #{pane_dead}'`
  - `tmux capture-pane -t <session> -p -S -100` — read last N lines from any pane
  - `tmux pipe-pane -t <session> -o 'cat >> ~/logs/<agent>.log'` — live tee for watchers
- Lifecycle hooks built in: `monitor-activity`, `monitor-silence <sec>`, `monitor-bell`, `set-hook -g pane-died ...`. The `monitor-silence` hook is the natural "agent looks stuck" signal.

## GUI / interaction layer — iTerm2 Python API

- iTerm2 runs a **local WebSocket server** on a Unix domain socket at `~/Library/Application Support/iTerm2/private/socket`, speaking a protobuf protocol. Enable via Settings → General → Magic → Enable Python API.
- The `iterm2` Python library (`pip install iterm2`) is a client wrapper. **Scripts run as ordinary external processes**, not "inside" iTerm2 — the bundled venv + Scripts menu + `AutoLaunch/` are conveniences, not requirements.
- Async event subscriptions are the headline feature absent from AppleScript: prompt detected, command finished, output matched, focus changed, layout changed.
- Capabilities: list/create/close windows/tabs/sessions, read session contents, send keystrokes (`async_send_text`), set titles/colors/profiles, register custom status bar components, register RPC triggers. Effectively full programmatic control.
- iTerm2 has native tmux integration: `tmux -CC attach -t <session>` renders tmux windows/panes as real iTerm2 tabs — best of both worlds.

## Signal layer — Claude Code hooks > regex triggers

- **Claude Code emits structured hook events** via `~/.claude/settings.json`: `Stop` (turn finished), `Notification` (needs permission/input), `PostToolUse`, `SubagentStop`, etc. Each hook runs an arbitrary shell command.
- This is **strictly superior** to regex-matching Claude's output (iTerm2 triggers, watching logs) — real signal vs. pattern-guessing on rendered text.
- For a switchboard: `Notification` hook → set tab yellow + post macOS notification; `Stop` hook → set tab green + post notification. No regex, no plist surgery.
- iTerm2 triggers remain useful for non-Claude processes inside the session (build output, etc.) where there are no hooks.

## Status surface — escape sequences

Cheap, no API needed:
- Tab color: `printf '\033]6;1;bg;red;brightness;255\a'` (and green/blue components separately). Reset: `printf '\033]6;1;bg;*;default\a'`.
- Tab title: `printf '\033]1;<title>\a'`. Window title: `printf '\033]2;<title>\a'`. Both: `\033]0;<title>\a`.
- Bell on inactive tab: red dot indicator, escape `\a`.
- These work from inside the session — Claude Code hooks can `printf` them directly.

## Notification delivery

- `osascript -e 'display notification "..." with title "..."'` — zero install, basic alerts.
- `terminal-notifier` (`brew install terminal-notifier`) — supports `-execute "osascript ..."` for **click-handler actions**. This is how "click the notification → focus that tab" works.
- Click handler runs AppleScript like `tell application "iTerm2" to select session id "<session_id>"`.

## OS-level session identity

- **tty** (`/dev/ttysNNN`) — kernel-level handle for the terminal device. `tty` command prints current. Each terminal window/tab has one. **Reusable** after a session dies — not stable long-term.
- iTerm2 **`unique id`** (or Python API `session_id`) — stable for the life of the session; the right handle for scripts.
- `osascript` one-liner to enumerate: `tell application "iTerm2" to repeat with w in windows, tabs, sessions ... return tty + name + unique id`.
- Terminal-agnostic listing: `ps -axo pid,tty,command | grep -E '\-zsh|\-bash|\-fish'`.

## Switchboard architecture sketch

A long-running daemon (Python, `iterm2` lib + FastAPI/uvicorn co-running on one asyncio loop):
- Connects to iTerm2 via the Unix socket
- Subscribes to session events, maintains agent state map
- Exposes a localhost HTTP/WebSocket API (`GET /sessions`, `POST /sessions/<id>/activate`, `POST /sessions/<id>/send`)
- Bind to `127.0.0.1` (or Tailscale IP) only; add a token check before accepting commands. Never `0.0.0.0` without auth — it's RCE-as-a-service.
- Run from `launchd` for auto-start on login, not from iTerm2's `AutoLaunch/` (cleaner restart, normal logging).

## Why not AppleScript / `osascript` for the switchboard

AppleScript is fine for fire-and-forget hook commands. For a switchboard daemon it loses on every dimension: no event subscriptions (polling only), no real ecosystem, no async, awkward syntax, cryptic errors. Use `osascript` for one-liners in hooks; use the Python API for anything stateful.

## Cross-machine / external access

- iTerm2's socket is Unix-only (file permissions = local user). To reach from another machine: `socat TCP-LISTEN:9999,bind=127.0.0.1,fork UNIX-CONNECT:<socket>` then SSH-tunnel. But this exposes the **full** iTerm2 API — RCE-equivalent, no narrowing.
- Better path: build a narrow HTTP API in front (FastAPI sketch above), expose only the operations needed, real auth, stable contract independent of iTerm2 protobuf changes. Tunnel via SSH or Tailscale.

## What's directly transferable to the framework

When this direction is picked up:
- **tmux session per agent** is a strong default for the autonomous runtime — solves "where does the agent live" cleanly.
- **Claude Code hooks** are the right signal source for state changes — the framework should standardize hook handlers (e.g., `lr-on-stop`, `lr-on-notification`) that both update the local switchboard state and trigger autonomous reflection if appropriate.
- **A switchboard daemon** could be a framework-shipped tool, not a per-user invention. Candidate: `lore-framework/scripts/switchboard.py` + a `/lr:status` skill that queries it.
- **Tab color conventions** (yellow=waiting, green=done, red=error, blue=working) — easy to standardize once.

## Current Status — Agent Teams chosen first

As of the v10 session, the user decided to experiment with Claude Code's **Agent Teams** feature as the multi-agent substrate before building this custom stack. Agent Teams provides for free what the tmux/iTerm2/switchboard path would build: spawning independent Claude Code instances, a communication channel (SendMessage mailbox), a shared task list, a UI, and built-in lifecycle management.

This substrate design remains valid as a fallback or deeper integration path if Agent Teams proves insufficient. See `spawn-teammate-feature.md` for the Agent Teams path.

## See Also

- `autonomous-agents-vision.md` — the framework-direction vision this substrate would implement
- `spawn-teammate-feature.md` — the Agent Teams path chosen experimentally over this substrate
- `framework-improvements-backlog.md` — running backlog tracking this direction
