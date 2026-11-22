# chisel

A Claude Code plugin for a gated, slice-by-slice development workflow:

1. **Grill** the task until the requirements are shared.
2. **Plan** it: a business entry in SPEC, an IMPLEMENTATION entry with the task's scope, branch and slices. Approved plan → task branch + plan commit.
3. **Slice** by slice, one commit each: failing tests → `test-reviewer` → your approval → implementation → `impl-reviewer` → your approval → commit.
4. **Pull request**: your approval → push + draft PR → `pr-reviewer` checks it against the whole repository → fix slices if needed → your approval → PR ready.

Nothing is committed, pushed or published without `/chisel:approve`. Hooks enforce it while a task is active, and lock the session after every commit so each slice starts in a fresh context.

## Install

```sh
claude plugin marketplace add smetak13/chisel        # or a local clone: claude plugin marketplace add ~/Work/projects/chisel
claude plugin install chisel@chisel --scope local    # run inside each repository that should use it
```

`--scope local` writes `.claude/settings.local.json`, which stays out of git, so teammates without the plugin are unaffected. Run `/reload-plugins` in an open session.

## Commands

| command | does |
|---|---|
| `/chisel:task [description]` | starts a task, or continues the active one |
| `/chisel:approve` | passes the gate that is waiting |
| `/chisel:status` | shows where the task stands |

After each commit: `/clear`, then `/chisel:task`.

## State

The workflow state lives in `.git/chisel/state.json`, per clone and never committed. Delete it to abandon a task. Docs live where you chose on first use: in the repository, or locally in `.git/chisel-docs/`.

## Development

```sh
python3 -m unittest discover -s tests
claude plugin validate .
claude --plugin-dir plugins/chisel    # try changes without installing
```

The grilling reference is adapted from Matt Pocock's grilling skill (MIT, `plugins/chisel/skills/task/references/GRILLING-LICENSE`).
