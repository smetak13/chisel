# Setup

Runs once per repository clone, before its first chisel task.

1. Look for existing spec and implementation docs in the repository (`SPEC.md`, `IMPLEMENTATION.md` or close equivalents).
2. Ask the user where this repository keeps the chisel docs:
   - **In the repository**, committed and visible to the team: the existing files, or `docs/SPEC.md` and `docs/IMPLEMENTATION.md`.
   - **Local only**, never pushed: `.git/chisel-docs/SPEC.md` and `.git/chisel-docs/IMPLEMENTATION.md`.
3. Record the answer: `chisel config --docs <spec path> <implementation path>`, paths relative to the repository root.

Done when `chisel status` shows the two doc paths.
