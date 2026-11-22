# Pull request

Runs when every slice of the task is `done`. A draft PR goes up, the pr-reviewer checks it against the whole repository, accepted findings become fix slices, and the user marks the PR ready.

## 1. Draft PR (no PR in `chisel status`)

1. Run the full test suite and the project's checks. Done when all are green.
2. Write the PR description to a temporary file outside the repository (`mktemp`): what and why, how to try it, test results, and anything the project's CLAUDE.md asks a PR to carry.
3. `chisel request push`. Gate report: the commits (`git log --oneline <default branch>..HEAD`), the PR title, and the description. Then: "Run `/chisel:approve` to push and open a draft PR." Stop.
4. After approval: `chisel open-pr --title "<title>" --body-file <file>`.
5. Dispatch the `chisel:pr-reviewer` agent with the default branch, the PR URL, and the doc paths.
6. Judge its findings as in [slice](slice.md#judging-findings). Report them to the user with your decisions.
7. With accepted findings: add a fix slice for each to the task's table in IMPLEMENTATION (ids `fix-1`, `fix-2`, …) and tell the user to run `/clear` and then `/chisel:task`. Every fix slice goes through [slice](slice.md); a fix of a few lines may take `--single-gate`, its regression test then reviewed by the impl-reviewer. Without accepted findings, go to step 3 below.

## 2. Fix slices committed (PR open, all slices `done`)

Without fix slices in the task, go to step 3 below.

1. `chisel push`.
2. Dispatch the `chisel:pr-reviewer` agent again, limited to whether the fix slices resolve their findings without new problems.
3. Judge as before. Anything new and accepted becomes another fix slice; otherwise continue below.

## 3. Ready

1. In the task's IMPLEMENTATION entry, set `PR:` to the PR URL and `Status:` to `in review`.
2. `chisel request ready`. Gate report: the pr-reviewer findings and what became of them. Then: "Run `/chisel:approve` to mark the PR ready for review." Stop.
3. After approval: `chisel ready --message "Link <task title in a few words> to its PR"`. The task is finished.
