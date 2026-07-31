---
name: ab-implement
description: Implement a plan.md twice with two different models in separate sibling git worktrees, then compare the two diffs and recommend an approach. Usage /ab-implement <plan.md> [slug] [modelA] [modelB]
agent: Dual Implement
model: Claude Opus 4.5
argument-hint: <path-to-plan.md> [slug] [modelA] [modelB]
---

Implement the plan at `$1` twice — once per model — in two isolated sibling
git worktrees, then compare the two diffs and recommend an approach.

Arguments (positional):
- `$1` = `PLAN_ABS` (required) — absolute or repo-relative path to the plan
  markdown to implement.
- `$2` = `SLUG` (optional) — filesystem-safe slug for branches, worktree
  dirs, and artifacts. Defaults to the sanitized plan filename stem.
- `$3` = `MODEL_A` (optional, default `GLM-5.2`) — display name of the model
  for slot A, exactly as it appears in the model picker.
- `$4` = `MODEL_B` (optional, default `Kimi K2.7 Code`) — display name of the
  model for slot B, exactly as it appears in the model picker.

Full user input for reference: `$ARGUMENTS`

Follow your orchestrator procedure exactly:
1. Resolve and validate inputs; derive `SLUG` from the plan filename stem if
   not given. Never infer the plan from the open editor.
2. Preflight: record `BASE_SHA` and current branch; warn loudly via
   `#vscode/askQuestions` if the main working tree is dirty (worktrees are
   created from `BASE_SHA`, so uncommitted work is not in either
   implementation); abort if `ab/<SLUG>-a|b` or the worktree paths already
   exist (offer cleanup, never `--force`).
3. Provision: `mkdir -p .ab-implement/<SLUG>`; create both worktrees from
   `BASE_SHA` as `../<REPO_NAME>-<SLUG>-a|b` on branches `ab/<SLUG>-a|b`;
   write `run.json`, `plan.snapshot.md`, and a multi-root
   `ab-<SLUG>.code-workspace` (repo + both worktrees).
4. Launch both implementers in a **single message** (two `agent/runSubagent`
   calls → parallel): `Impl Worktree A` on `MODEL_A`, `Impl Worktree B` on
   `MODEL_B`. Each prompt fully specifies slot, model, worktree, branch,
   `BASE_SHA`, `PLAN_ABS` (read-only, not copied in), inlined repo
   conventions (inline `.kb/review-guidelines.md` verbatim if present — it is
   untracked and absent from worktrees), guardrails, cache hygiene, and the
   required reply format. State the model explicitly in each prompt as well
   as relying on the implementer's frontmatter.
5. Capture diffs deterministically: assert each worktree has commits on top
   of `BASE_SHA` and a clean `git status`; write
   `.ab-implement/<SLUG>/impl-{a,b}.{diff,stat}`; persist each subagent's
   returned summary to `impl-{a,b}-report.md` (record any residue or failure).
6. Compare (diff-only): read both diff/stat files; classify every plan step
   as `A+B` / `A only` / `B only` / `neither`; write
   `.ab-implement/<SLUG>/comparison.md` with all 10 sections from your
   procedure.
7. Reply in ≤8 lines: recommendation, one-line rationale, `comparison.md`
   path, both branch names, cleanup command. Substitute the real `<SLUG>`
   into the handoff prompts so the "Adopt Implementation A/B" buttons are
   pre-filled.

Keep the two runs strictly blind: never share one slot's diff, branch, or
summary with the other slot's subagent.
