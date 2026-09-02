# Atelier3A

**Atelier3A (A3A)** is a GitHub-centered three-agent software studio that gives one human a single point of contact while routing work among:

- **Principal:** ChatGPT Business -- product intent, architecture, arbitration, final review packet.
- **Builder:** Claude Code authenticated through Claude Pro -- canonical implementation and test loop.
- **Reviewer:** Venice.ai models -- independent review with a hard local budget ceiling and no silent paid fallback.

GitHub is the source of truth and message bus. The default policy is **human approval before substantive merge to `main`**.

## Minimal deployment

### New project

1. Create a GitHub repository from Atelier3A using **Use this template**.
2. Clone the new project onto the machine that will run A3A, then:

```bash
gh auth login
claude
./a3a setup
./a3a run
```

`claude` is run once to authenticate Claude Code with the Claude Pro subscription. Do **not** configure an Anthropic API key, auth token, gateway URL, or cloud-provider fallback in the A3A runner environment.

Unattended Builder sessions run in Claude Code restricted mode with no additional directories, no browser or MCP access, and a fail-closed permission policy. Claude may edit and inspect files only in its assigned worktree. Shell execution uses whichever native shell tool Claude Code exposes on the host -- `Bash` on non-Windows, `PowerShell` on Windows, selected automatically and not configurable -- and is limited to exact, argument-free test/build/lint/typecheck entry points such as `python -m pytest`, `npm test`, `npm run build`, `cargo test`, and `dotnet test`; every other shell command is denied on either platform.

If automated Venice review is desired, set `VENICE_API_KEY`. If it is absent or the configured monthly credit ceiling is reached, the task routes to `studio:principal-needed` instead of spending more money.

The legacy `./studio` command remains supported as a compatibility alias.

### Existing project

Clone `cargo-culture/Atelier3A` locally and run:

```bash
cd /path/to/existing-project
/path/to/Atelier3A/a3a init .
git add AGENTS.md .studio .github .gitignore README-STUDIO.md
git commit -m "chore: install Atelier3A"
git push
/path/to/Atelier3A/a3a setup
/path/to/Atelier3A/a3a run
```

The installer adds the A3A policy/state files and GitHub issue template without overwriting existing files unless `--force` is used.

## Human workflow

You speak only to the ChatGPT Principal. Example:

> Implement mobile drag-and-drop equipment markers and prepare the final build for my review.

The Principal creates or updates the GitHub work packet and applies `studio:queued`. The local runner dispatches Claude, pushes the implementation branch, opens the PR, requests independent review when budget permits, loops corrections at most twice, and leaves the task at `studio:human-review`.

The Principal then gives the human a concise review packet. The human says `Approved. Merge.` or requests revision.

## Commands

```text
a3a doctor          Check git, gh, Claude and billing-safety prerequisites
a3a setup           Check prerequisites and create/update A3A labels
a3a labels          Create/update A3A workflow labels
a3a init [path]     Install A3A files into an existing Git repo
a3a process 214     Process one issue
a3a run --once      Process currently queued issues and exit
a3a run             Poll GitHub continuously (default: every 60 seconds)
```

`studio ...` remains supported for backward compatibility.

## Cost behavior

The runner is designed to fail closed:

- Claude subscription quota exhausted -> task becomes blocked; no API fallback.
- Anthropic API keys/tokens, gateway URLs, cloud-provider fallbacks, and the Venice reviewer key are removed from Builder subprocesses; `a3a doctor` flags Builder API fallback configuration.
- Builder file access remains confined to the assigned worktree, and only exact repository verification commands are approved unattended.
- Venice API key absent -> Principal review required.
- Venice local monthly ceiling reached -> Principal review required.
- The runner never merges substantive work automatically.

The local Venice budget tracker is a safety estimate, **not a server-side billing control**. Set the ceiling conservatively and use Venice account-side controls when available.

## Important files

- `AGENTS.md` -- governing operating rules.
- `.studio/studio.yaml` -- machine-readable routing and cost policy.
- `.studio/state.md` -- concise current state.
- `STUDIO-INTEGRATION.md` -- detailed single-front-door architecture and setup.
- `studio_runner/` -- local orchestrator.

## Template model

Atelier3A is intentionally usable as a GitHub template. For projects that already exist, use `a3a init` instead of recreating them.
