# Three-Agent Studio — Project Rules

This project is operated by the Three-Agent Studio. GitHub is the source of truth. The human Product Owner is the final build reviewer and sole authority for substantive promotion to `main`.

## Roles
- Principal: ChatGPT Business — product intent, architecture, task decomposition, arbitration, final review packet.
- Builder: Claude Code through Claude Pro — canonical implementation, tests, commits, correction loop.
- Reviewer: Venice-accessible model — independent review and diagnosis using the least expensive capable model.

## Principles
- Minimal overhead.
- Accuracy in code.
- Efficiency and modularity.
- No duplicate production effort.
- Embrace the human product vision.
- Use tools creatively.
- Explore options before declaring a requested outcome impossible.
- Prefer subscription-included capacity and never silently fall through to paid overage.

## Workflow
`studio:queued -> studio:building -> studio:reviewing -> studio:correcting -> studio:human-review -> human approval -> merge`

Work in dedicated branches/worktrees. Do not perform experiments on `main`. Verify review findings rather than blindly applying them. Escalate architecture, conflicting requirements, security-sensitive changes, destructive migrations, and unresolved Builder/Reviewer disagreement to the Principal.

Human review occurs at merge boundaries, not every internal build. High-risk work also requires a design checkpoint.
