---
name: status
description: Show where the current chisel task stands.
disable-model-invocation: true
allowed-tools: Bash(python3 *)
---

!`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/chisel.py" status`

Show the user this state in their language, together with the active task's slices and their statuses from IMPLEMENTATION, and name the next step. Change nothing.
