# Plan

Turns the grilled task into a SPEC entry, an IMPLEMENTATION entry with its slices, and the task branch. The doc paths are in `chisel status`.

## New task

1. Make sure you start from the up-to-date default branch with a clean working tree. If the tree has changes, ask the user what to do with them.
2. Choose the branch: the repository's convention (project CLAUDE.md, recent branches in `git branch -a`) or `<type>/<kebab-case-name>` with type `feature`, `bugfix`, `refactor`, `chore` or `docs`.
3. `chisel begin --task "<task title>" --branch <branch>`.
4. Write the SPEC entry: what the task solves and what changes for the user, in business terms, matching the style of the existing SPEC. A bug fix changes SPEC only when it changes intended behaviour.
5. Write the IMPLEMENTATION entry in the format below, with its slices.
6. `chisel request plan`, present the gate report, and stop.

## Task already in IMPLEMENTATION

1. Read its entry and the code it touches, and check that the scope and slices still fit the code as it is now. Propose changes where they don't, and write the agreed ones into the entry.
2. Fill in the type and branch lines when they are missing, then `chisel begin`, `chisel request plan`, present the gate report, and stop. The gate asks the user whether the plan is still current.

## IMPLEMENTATION entry

```markdown
## <Task title>

- Type: feature
- Branch: `feature/<name>`
- PR: —
- Status: in progress

<What this task implements, which parts of the code it touches, what is out of scope: two to five sentences.>

| id | slice | tests | status |
|---|---|---|---|
| 1 | <behaviour this slice adds> | <behaviours its tests check> | todo |
| 2 | <UI-only change> | — (UI) | todo |
```

Group tasks under an `# <Epic>` heading when they belong to one. Number slice ids within the task; when the repository already numbers them (`4.5`), follow its scheme.

## Slicing

- A slice is a vertical slice: one behaviour end to end, with its own tests, that leaves every test green once committed.
- Aim for at most ~400 changed lines including tests; generated files and lockfiles don't count.
- Order slices so each builds on committed ones.
- A slice with nothing to unit test (layout, styling, config) gets `— (UI)` or `— (config)` in the tests column: it has a single gate.

## Gate report

The task and its branch, the SPEC change in two or three sentences, the slices as a list, and the open risks. Then: "Run `/chisel:approve` to commit the plan, or tell me what to change."

## After approval

`chisel commit --message "Plan <task title in a few words>"`. It creates or switches to the branch and commits the docs, or only creates the branch when they live outside the repository. The session is now locked: tell the user to run `/clear` and then `/chisel:task`.
