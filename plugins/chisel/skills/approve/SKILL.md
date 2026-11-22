---
name: approve
description: Approve the chisel gate that is waiting for you.
disable-model-invocation: true
allowed-tools: Bash(python3 *)
---

!`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/chisel.py" approve`

The line above is the result of the user's `/chisel:approve`. `chisel` in it means `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/chisel.py"`, run from the repository root. When it names an approved gate, carry out the next step it gives, following the chisel:task workflow and its reference files. When it is an error, show it to the user and explain what is still missing.
