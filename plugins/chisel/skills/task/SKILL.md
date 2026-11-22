---
name: task
description: Run a development task through the chisel workflow. Use when the user agrees to run a task as a chisel task.
argument-hint: "[task description]"
allowed-tools: Bash(python3 *)
---

# chisel task

Current state:

!`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/chisel.py" status`

Task description from the user: $ARGUMENTS

`chisel` below means `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/chisel.py"`, run from the repository root. It holds the workflow state and performs every commit, push and pull request change; hooks refuse the raw git and gh commands while a task is active.

## Hierarchy

- **Task**: one branch and one pull request. A feature, bug fix, refactor or chore.
- **Slice**: one vertical slice of the task, one commit with its tests and implementation.
- **Epic**: an optional heading in IMPLEMENTATION that groups tasks. Nothing in the workflow depends on it.

## Gates

A gate is a stop where the user decides. You reach it with `chisel request <gate>`, present the gate report, and end your turn. The user passes it by running `/chisel:approve`; its output names the next step. A chat message like "ok" or "go ahead" is feedback, so answer it by pointing to `/chisel:approve`. When the user replies with objections, rework, then present the gate again.

Gates in order: `plan` → per slice `tests` and `impl` (only `impl` for a single-gate slice) → `push` → `ready`.

## Sessions

Each commit locks the session: after `chisel commit`, tell the user to run `/clear` and then `/chisel:task`, and stop. The next session starts from the state above and the docs, so everything a later step needs belongs in IMPLEMENTATION or the state, never only in this conversation.

## Next step

Pick the first row that matches the state above, read its reference file, and follow it:

1. `Docs: not configured` → [setup](references/setup.md), then continue down this list.
2. No task is active → [grilling](references/grilling.md) for the described task, then [plan](references/plan.md). Without a description, take the next task in IMPLEMENTATION that is not done and go straight to [plan](references/plan.md).
3. `Plan committed: no` → [plan](references/plan.md).
4. A slice is in progress, or the task in IMPLEMENTATION has a slice that is not `done` → [slice](references/slice.md).
5. Otherwise → [pull request](references/pr.md).

## Language

Everything written into the repository is English. Talk to the user in their language.
