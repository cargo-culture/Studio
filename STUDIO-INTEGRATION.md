# Studio Integration — Single Front Door

## Goal
The human talks only to the **ChatGPT Business Principal**. GitHub is the shared command bus and source of truth. A local Studio runner dispatches production work to Claude Code and independent review to a budget-gated Venice model.

```text
HUMAN
  |
  v
CHATGPT BUSINESS — Principal
  |
  v
GITHUB — issues / PRs / decisions / state
  |
  v
LOCAL STUDIO RUNNER
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
The machine running the Studio needs:

- Git;
- GitHub CLI (`gh`), authenticated to the project repositories;
- Python 3.11+;
- Claude Code, authenticated through the Claude Pro subscription;
- optional `VENICE_API_KEY` for automated independent review.

Do **not** expose `ANTHROPIC_API_KEY` to the Studio Builder environment. The runner strips it from Claude subprocesses and `studio doctor` flags its presence.

After cloning a Studio-enabled project:

```bash
gh auth login
claude
./studio setup
./studio run
```

Run `claude` once to establish subscription authentication.

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
3. invokes `claude -p` with the issue and repository rules;
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
After this repository is marked as a GitHub template, choose **Use this template** and create the new project repository. Clone it, authenticate locally once, then run `./studio setup` and `./studio run`.

### Existing project
Clone `cargo-culture/Studio` locally and run from the existing project:

```bash
/path/to/Studio/studio init .
git add AGENTS.md .studio .github .gitignore README-STUDIO.md
git commit -m "chore: install Three-Agent Studio"
git push
/path/to/Studio/studio setup
/path/to/Studio/studio run
```

The installer does not overwrite existing project files unless `--force` is explicitly supplied.

## Minimalism rule
Do not add a database, vector store, cloud server, message broker, or heavyweight orchestration framework until an observed limitation requires one.

Git is the persistent state. GitHub issues are the queue. PRs are the handoff envelopes. Labels are the workflow state machine. Local compute runs the orchestration.
