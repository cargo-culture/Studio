# Atelier3A Integration -- Single Front Door

## Goal
The human talks only to the **ChatGPT Business Principal**. GitHub is the shared command bus and source of truth. The local Atelier3A (A3A) runner dispatches production work to Claude Code and independent review to a budget-gated Venice model.

```text
HUMAN
  |
  v
CHATGPT BUSINESS -- Principal
  |
  v
GITHUB -- issues / PRs / decisions / state
  |
  v
LOCAL A3A RUNNER
  |                    |
  v                    v
CLAUDE CODE / PRO      VENICE MODEL
Builder                Reviewer
  |                    |
  +-------- GitHub ----+
           |
           v
CHATGPT PRINCIPAL
           |
           v
HUMAN FINAL REVIEW
```

## Why GitHub is the bridge
The Principal does not need a direct machine-to-machine connection to Claude or Venice. It creates and reads GitHub issues, PRs, review comments, labels, and architecture decisions. The local runner watches those artifacts and performs the appropriate work.

This keeps project state provider-neutral and prevents important knowledge from disappearing with an agent conversation.

## One-time local setup
The machine running A3A needs:

- Git;
- GitHub CLI (`gh`), authenticated to the project repositories;
- Python 3.11+;
- Claude Code, authenticated through the Claude Pro subscription;
- optional `VENICE_API_KEY` for automated independent review.

Do **not** expose an Anthropic API key, auth token, gateway URL, or cloud-provider fallback to the A3A Builder environment. The runner strips those values from Claude subprocesses and `a3a doctor` flags them. The Venice reviewer key is also withheld from Builder subprocesses.

After cloning an Atelier3A-enabled project:

```bash
gh auth login
claude
./a3a setup
./a3a run
```

Run `claude` once to establish subscription authentication. The legacy `./studio` command remains available for compatibility.

## Human command model
The human communicates in outcomes:

- `Implement #214.`
- `Add mobile drag-and-drop equipment markers.`
- `Resolve the open collision bugs and bring me the build.`
- `Status.`
- `Approved. Merge.`

The Principal owns routing and should not ask the human to choose which agent performs routine work.

## Principal responsibilities
For a new instruction the Principal:

1. inspects GitHub for existing issues/PRs to avoid duplicated effort;
2. creates or updates the work packet;
3. defines acceptance criteria and risk;
4. records material design decisions;
5. applies `studio:queued`;
6. monitors GitHub state when the human checks in;
7. resolves `studio:principal-needed` escalations where possible;
8. prepares the final human review packet;
9. merges only after explicit human authorization.

## Runner state machine
The runner polls for `studio:queued` issues.

For each task it:

1. claims the issue with `studio:building`;
2. creates a dedicated `studio/<issue>-<slug>` worktree;
3. invokes `claude -p` in restricted, non-interactive mode with the issue and repository rules;
4. commits and pushes canonical implementation work;
5. opens or updates a PR;
6. applies `studio:reviewing`;
7. sends a focused diff/review packet to Venice if budget permits;
8. posts independent findings back to GitHub;
9. invokes Claude for verified corrections;
10. repeats review at most the configured number of rounds;
11. escalates unresolved disagreement to `studio:principal-needed`;
12. moves verified work to `studio:human-review`.

The runner never merges substantive work to `main`.

### Builder execution boundary

The Builder uses Claude Code `dontAsk` mode together with `--restricted`; it does not use `bypassPermissions` or grant additional directories. The exposed tool set is limited to worktree-confined read/edit/search tools plus the shell tool Claude Code exposes natively on the host: `Bash` on non-Windows hosts, `PowerShell` on Windows. The runner selects that tool automatically from the host platform -- it is not configurable -- and translates the same exact, argument-free test/build/lint/typecheck approvals and the same explicit denials (file inspection, Git, network, secondary-shell) onto whichever tool is active, so approved verification commands remain available on every supported host. Unlisted tool calls fail closed during unattended runs.

`builder.permissions.deny` in `.studio/studio.yaml` is the only configurable permission, and it is additive-only: it can add further denials on top of the built-in ones but can never remove or replace one. Configured deny rules are authored in canonical `Bash(...)` source form regardless of host -- for example `Bash(rm -rf *)` -- and the runner translates them onto the host's native shell tool the same way it translates the built-in denials, so that rule becomes `PowerShell(rm -rf *)` on a Windows Builder host.

The orchestrator--not Claude--owns commits, pushes, PR creation, review routing, and the final transition to human review. Merge remains a separate human-authorized action.

## Principal escalation contract
When an agent needs the Principal, GitHub should contain a compact decision packet:

```text
PRINCIPAL_NEEDED

ISSUE
#214

DECISION
What question must be resolved?

BUILDER POSITION
...

REVIEWER POSITION
...

EVIDENCE
...

OPTIONS
A. ...
B. ...

RECOMMENDATION
...
```

At the next human interaction the Principal reads this from GitHub and resolves it without involving the human unless product intent genuinely requires human judgment.

## Human review cadence
- Low-risk mechanical work: batch where practical.
- Normal feature/bug: one human review after implementation, independent review, correction, and verification.
- High-risk work: design checkpoint plus final build review.
- Release candidate: always human reviewed.

The review packet should contain CHANGE, REQUESTED, RESULT, SCOPE, TESTS, INDEPENDENT REVIEW, BEHAVIORAL CHANGES, RISKS, MANUAL CHECK, and RECOMMENDATION.

## Cost behavior
The desired failure mode is **slower production, not surprise billing**.

### Claude capacity exhausted
Stop Builder work and mark the issue blocked. Do not switch to Anthropic API billing.

### Venice budget exhausted or key absent
Stop automated third-agent review and mark `studio:principal-needed`. The ChatGPT Principal can perform the missing review on the next check-in.

### GitHub Actions quota constrained
Run tests on the local runner and post summarized results.

No agent may silently cross from subscription-included capacity to purchased metered capacity.

## Project deployment
### New project
Choose **Use this template** from `cargo-culture/Atelier3A`, create the project repository, clone it, authenticate locally once, then run `./a3a setup` and `./a3a run`.

### Existing project
Clone `cargo-culture/Atelier3A` locally and run from the existing project:

```bash
/path/to/Atelier3A/a3a init .
git add AGENTS.md .studio .github .gitignore README-STUDIO.md
git commit -m "chore: install Atelier3A"
git push
/path/to/Atelier3A/a3a setup
/path/to/Atelier3A/a3a run
```

The installer does not overwrite existing project files unless `--force` is explicitly supplied.

## Minimalism rule
Do not add a database, vector store, cloud server, message broker, or heavyweight orchestration framework until an observed limitation requires one.

Git is the persistent state. GitHub issues are the queue. PRs are the handoff envelopes. Labels are the workflow state machine. Local compute runs the orchestration.
