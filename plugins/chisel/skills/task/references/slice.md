# Slice

One slice ends in one commit holding its tests and its implementation. The general TDD and code quality rules from the user's CLAUDE.md apply; inside a slice, *red* covers all of the slice's tests at once.

Find the checks the project runs (tests, type check, lint, build) in the project's CLAUDE.md. Run only those it lists, plus the test suite. If the repository has no test setup, stop and agree the technology and test library with the user before writing tests.

## 1. Start

If no slice is in progress, take the first slice of the active task in IMPLEMENTATION that is not `done`: `chisel slice --id <id>`, adding `--single-gate` when its tests column says there is nothing to unit test. A slice already in progress resumes where its gates stand in `chisel status`.

Single-gate slices skip to step 3.

## 2. Tests

1. Write the slice's tests, using the repository's existing test library and conventions.
2. Run them. Done when every new test is *red* because the behaviour is missing, never because the test itself is broken (syntax, wrong import, a typo in a fixture).
3. Dispatch the `chisel:test-reviewer` agent. Give it: the slice row and the task entry in IMPLEMENTATION, the doc paths, the test files, the test run output, and the command `chisel diff` (spelled out in full) for the slice diff.
4. Judge its findings (below).
5. `chisel request tests --test-files <files>`. List only files that hold nothing but tests; a test that lives inside a source file stays unlisted, and the impl-reviewer checks it instead.
6. Present the gate report and stop.

## 3. Implementation

1. Write the minimum code that turns the tests green, then refactor with the tests green.
2. When a slice outgrows ~400 changed lines, propose splitting it, and write the agreed split into IMPLEMENTATION.
3. Run the tests and the project's checks. Done when all are green.
4. Set the slice's status to `done` in IMPLEMENTATION.
5. Dispatch the `chisel:impl-reviewer` agent. Give it: the slice row and the task entry, the doc paths, the check output, and the commands `chisel diff` and, for a two-gate slice, `chisel diff --since-tests`.
6. Judge its findings.
7. `chisel request impl`, present the gate report, and stop.

Approved tests stay as approved. When one turns out to be wrong, stop and explain it to the user. On their agreement, fix it and go back through `chisel request tests`, so the user approves the tests again; `chisel request impl` refuses changed approved test files.

## 4. Commit

After the user approves `impl`: `chisel commit --message "<subject>"`. The subject is the repository's convention when it has one; otherwise a single imperative line of at most ~60 characters that names the behaviour ("Classify a URL by host"), with no slice number and no body.

The session is now locked: tell the user to run `/clear` and then `/chisel:task`.

## Judging findings

A reviewer is a second opinion. Weigh each finding on its merits:

- **Fix** it when it shows a real or likely problem: a bug, a wrong or missing test for important behaviour, a broken rule from CLAUDE.md, a risk to the rest of the code.
- **Reject** it, with a one-line reason, when it is a preference, out of the slice's scope, or wrong. Stand by a correct decision even when the reviewer disagrees.

Dispatch the reviewer again only when a fix changed logic, and at most twice per gate. Every finding, and what you did with it, goes into the gate report.

## Gate report

- What the slice does, in one or two sentences.
- `chisel diff --stat` (for `impl` of a two-gate slice, also `chisel diff --since-tests --stat`).
- Test output: for `tests`, which tests fail and why that is the expected reason; for `impl`, the suite and checks are green.
- The reviewer's findings, each marked fixed or rejected with its reason.
- "Review the diff with `git diff` and new files with `git status`, then run `/chisel:approve`, or tell me what to change."
