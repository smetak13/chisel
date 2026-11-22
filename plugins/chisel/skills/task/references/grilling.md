# Grilling

Adapted from the grilling skill by Matt Pocock (MIT, see [GRILLING-LICENSE](GRILLING-LICENSE)).

Interview the user relentlessly about the task until you reach a shared understanding. Map this as a **design tree**: every decision branches into the decisions that hang off it.

Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are already settled: the questions you can ask _now_ without guessing at answers you haven't heard yet. Ask the whole frontier in one round: number each question and give your recommended answer. Then wait for the user's answers before the next round.

Format a round like so:

```
❓ **Q1** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>

---

❓ **Q2** - **<question title>**: <question body>

➡️ <your recommended answer>
```

Each round the user answers reshapes the tree: settled decisions push the frontier outward and unblock questions that depended on them. Recompute the frontier and ask the next round. A question whose answer depends on another question still open in this round belongs to a _later_ round.

Finding _facts_ is your job, never the user's. When a frontier question needs a fact from the repository or environment, dispatch a sub-agent to find it; don't ask the user for anything you could look up yourself. Don't block on it: only the questions downstream of a running exploration wait for its report. The _decisions_ are the user's: put each to them and wait.

## Scope

- **Feature or refactor**: the full tree: behaviour, edge cases, what is out of scope, how it fits the existing code, how to test it.
- **Bug fix**: a short tree: how to reproduce it, the expected behaviour, and where it lives. The first slice will be a test that reproduces the bug.

Done when the frontier is empty and the user confirms the shared understanding. Then continue with [plan](plan.md).
