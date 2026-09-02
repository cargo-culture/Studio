from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
import os
from .util import StudioError


# Claude Code exposes different native shell tools per host OS: Bash on
# POSIX, PowerShell on Windows. The Builder policy is fixed per platform and
# is never selectable through config, so an approved verification command is
# always available for the host actually running the agent.
SHELL_TOOL_POSIX = "Bash"
SHELL_TOOL_WINDOWS = "PowerShell"


def is_windows() -> bool:
    return os.name == "nt"


def native_shell_tool() -> str:
    return SHELL_TOOL_WINDOWS if is_windows() else SHELL_TOOL_POSIX


def _for_shell(rules: tuple[str, ...], shell_tool: str) -> tuple[str, ...]:
    translated = []
    for rule in rules:
        if rule == SHELL_TOOL_POSIX:
            translated.append(shell_tool)
        elif rule.startswith(SHELL_TOOL_POSIX + "("):
            translated.append(shell_tool + rule[len(SHELL_TOOL_POSIX):])
        else:
            translated.append(rule)
    return tuple(translated)


# BUILDER_TOOLS, BUILDER_ALLOWED_TOOLS, and BUILDER_DENIED_TOOLS are POSIX
# source-form rules: every shell rule is authored with the "Bash" tool
# prefix and none of these three constants is runtime-ready or safe to pass
# directly to Claude Code. `builder_policy` always routes them through
# `_for_shell(rules, native_shell_tool())`, which rewrites "Bash" to the
# host's native shell tool ("Bash" on POSIX, "PowerShell" on Windows),
# before they become part of a `BuilderPolicy`.
BUILDER_TOOLS = ("Read", "Glob", "Grep", "Edit", "Write", "Bash")

# Keep shell approvals exact. Wildcards make it possible to append redirections,
# alternate config paths, or other arguments that escape the intended command.
BUILDER_ALLOWED_TOOLS = (
    "Read",
    "Glob",
    "Grep",
    "Edit",
    "Write",
    "Bash(python -m unittest)",
    "Bash(python -m unittest discover)",
    "Bash(python -m pytest)",
    "Bash(py -m unittest)",
    "Bash(py -m unittest discover)",
    "Bash(py -m pytest)",
    "Bash(pytest)",
    "Bash(tox)",
    "Bash(nox)",
    "Bash(ruff check .)",
    "Bash(mypy .)",
    "Bash(pyright)",
    "Bash(python -m build)",
    "Bash(npm test)",
    "Bash(npm run test)",
    "Bash(npm run build)",
    "Bash(npm run lint)",
    "Bash(npm run typecheck)",
    "Bash(npm run type-check)",
    "Bash(pnpm test)",
    "Bash(pnpm run test)",
    "Bash(pnpm run build)",
    "Bash(pnpm run lint)",
    "Bash(pnpm run typecheck)",
    "Bash(pnpm run type-check)",
    "Bash(yarn test)",
    "Bash(yarn build)",
    "Bash(yarn lint)",
    "Bash(yarn typecheck)",
    "Bash(yarn type-check)",
    "Bash(bun test)",
    "Bash(bun run test)",
    "Bash(bun run build)",
    "Bash(bun run lint)",
    "Bash(bun run typecheck)",
    "Bash(bun run type-check)",
    "Bash(deno test)",
    "Bash(deno lint)",
    "Bash(deno check)",
    "Bash(go test ./...)",
    "Bash(go vet ./...)",
    "Bash(go build ./...)",
    "Bash(cargo test)",
    "Bash(cargo check)",
    "Bash(cargo build)",
    "Bash(cargo clippy)",
    "Bash(cargo fmt --check)",
    "Bash(dotnet test)",
    "Bash(dotnet build)",
    "Bash(mvn test)",
    "Bash(mvn verify)",
    "Bash(./mvnw test)",
    "Bash(./mvnw verify)",
    "Bash(gradle test)",
    "Bash(gradle check)",
    "Bash(gradle build)",
    "Bash(./gradlew test)",
    "Bash(./gradlew check)",
    "Bash(./gradlew build)",
    "Bash(make test)",
    "Bash(make check)",
    "Bash(make build)",
    "Bash(make lint)",
    "Bash(make typecheck)",
    "Bash(make type-check)",
)

# Claude Code treats several shell commands as read-only in every permission
# mode. Deny them at the shell layer so repository inspection must use the
# restricted file tools, which are confined to the current worktree.
BUILDER_DENIED_TOOLS = (
    "Bash(cat *)",
    "Bash(head *)",
    "Bash(tail *)",
    "Bash(grep *)",
    "Bash(rg *)",
    "Bash(find *)",
    "Bash(ls *)",
    "Bash(tree *)",
    "Bash(wc *)",
    "Bash(diff *)",
    "Bash(stat *)",
    "Bash(du *)",
    "Bash(file *)",
    "Bash(sed *)",
    "Bash(awk *)",
    "Bash(sort *)",
    "Bash(less *)",
    "Bash(more *)",
    "Bash(cd *)",
    "Bash(git *)",
    "Bash(env)",
    "Bash(env *)",
    "Bash(printenv)",
    "Bash(printenv *)",
    "Bash(set)",
    "Bash(curl *)",
    "Bash(wget *)",
    "Bash(powershell *)",
    "Bash(pwsh *)",
    "Bash(cmd *)",
)

# The POSIX alias translation above only renames the shell tool prefix
# (Bash -> PowerShell); it does not rename the commands themselves, so it
# cannot deny the native PowerShell cmdlets Claude Code may treat as
# read-only, including file/path inspection (Get-ItemProperty, Get-Acl) and
# host/process/network reconnaissance (Get-Process, Get-Service,
# Get-NetTCPConnection). Add those explicitly, Windows-only, to preserve the
# same repository-inspection boundary that the POSIX denials enforce on Bash.
#
# PowerShell also ships built-in aliases for several of these cmdlets, and
# separate alternate shell/process entry points (bash/sh/wsl) that reach the
# same prohibited file, path, environment, network, expression, or
# secondary-shell operations under a different name. Deny those aliases and
# entry points too so the boundary cannot be bypassed just by spelling the
# same operation differently. No allow rule is added for any of them.
BUILDER_DENIED_TOOLS_WINDOWS_ONLY = (
    "PowerShell(Get-Content *)",
    "PowerShell(gc *)",
    "PowerShell(type *)",
    "PowerShell(Get-ChildItem *)",
    "PowerShell(gci *)",
    "PowerShell(dir *)",
    "PowerShell(Get-Item *)",
    "PowerShell(gi *)",
    "PowerShell(Resolve-Path *)",
    "PowerShell(rvpa *)",
    "PowerShell(Test-Path *)",
    "PowerShell(Get-Location)",
    "PowerShell(gl)",
    "PowerShell(pwd)",
    "PowerShell(Get-Variable)",
    "PowerShell(Get-Variable *)",
    "PowerShell(gv)",
    "PowerShell(gv *)",
    "PowerShell(Select-String *)",
    "PowerShell(sls *)",
    "PowerShell(Invoke-WebRequest *)",
    "PowerShell(iwr *)",
    "PowerShell(Invoke-RestMethod *)",
    "PowerShell(irm *)",
    "PowerShell(Invoke-Expression *)",
    "PowerShell(iex *)",
    "PowerShell(Start-Process *)",
    "PowerShell(saps *)",
    "PowerShell(Get-ItemProperty *)",
    "PowerShell(gp *)",
    "PowerShell(Get-Acl *)",
    "PowerShell(Get-Process)",
    "PowerShell(Get-Process *)",
    "PowerShell(ps)",
    "PowerShell(ps *)",
    "PowerShell(Get-Service)",
    "PowerShell(Get-Service *)",
    "PowerShell(gsv)",
    "PowerShell(gsv *)",
    "PowerShell(Get-NetTCPConnection)",
    "PowerShell(Get-NetTCPConnection *)",
    "PowerShell(bash)",
    "PowerShell(bash *)",
    "PowerShell(sh)",
    "PowerShell(sh *)",
    "PowerShell(wsl)",
    "PowerShell(wsl *)",
    # `Bash(powershell *)`, `Bash(pwsh *)`, and `Bash(cmd *)` above translate
    # to the wildcard forms of these on Windows, but a bare invocation with
    # no arguments still opens an interactive/secondary shell and isn't
    # matched by the `*` (one-or-more-argument) rule, so deny it explicitly.
    "PowerShell(powershell)",
    "PowerShell(pwsh)",
    "PowerShell(cmd)",
)

BUILDER_API_FALLBACK_ENVIRONMENT_VARIABLES = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_BEDROCK_BASE_URL",
    "ANTHROPIC_VERTEX_BASE_URL",
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX",
    "CLAUDE_CODE_USE_FOUNDRY",
)

BUILDER_FORBIDDEN_ENVIRONMENT_VARIABLES = (
    *BUILDER_API_FALLBACK_ENVIRONMENT_VARIABLES,
    "VENICE_API_KEY",
)


@dataclass(frozen=True)
class BuilderPolicy:
    permission_mode: str
    restricted_to_worktree: bool
    tools: tuple[str, ...]
    allowed_tools: tuple[str, ...]
    denied_tools: tuple[str, ...]
    forbidden_environment_variables: tuple[str, ...]


def _unique(*groups: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(item for group in groups for item in group))


# Fail-closed: only these keys are accepted under builder.permissions. Any
# other key (typo, future/unsupported option, etc.) raises StudioError from
# builder_policy instead of being silently ignored, so an unenforced
# permission can never slip through unnoticed.
#
# "tools" and "allow" are deliberately absent: the exposed tool set and the
# exact verification allowlist are fixed per platform and are never
# configurable, even to a value that happens to match the native default, so
# config can't be used to widen or narrow either one. "deny" is the only
# configurable key, and it is additive-only (see `_unique(native_denied, ...)`
# below): it can add further denials but can never remove or replace a
# built-in one. Configured "deny" rules are authored in canonical Bash(...)
# source form on every host, the same as BUILDER_DENIED_TOOLS, and are routed
# through `_for_shell(..., shell_tool)` before merging so they land as
# PowerShell(...) on Windows.
BUILDER_PERMISSION_KEYS = frozenset({"mode", "restricted_to_worktree", "deny"})

@dataclass
class Config:
    data: dict
    path: Path

    @property
    def canonical_branch(self):
        return self.data.get("studio", {}).get("canonical_branch", "main")

    @property
    def branch_pattern(self):
        return self.data.get("github", {}).get("branch_pattern", "studio/{issue_number}-{slug}")

    @property
    def reviewer_enabled(self):
        return bool(self.data.get("agents", {}).get("reviewer", {}).get("enabled", True))

    @property
    def reviewer_model(self):
        return self.data.get("agents", {}).get("reviewer", {}).get("model_policy", {}).get("default", "zai-org-glm-5-2")

    @property
    def venice_credit_ceiling(self):
        return float(self.data.get("agents", {}).get("reviewer", {}).get("cost_control", {}).get("monthly_venice_credit_ceiling", 100))

    @property
    def max_review_rounds(self):
        return int(self.data.get("review", {}).get("max_builder_reviewer_rounds", 2))

    @property
    def builder_policy(self) -> BuilderPolicy:
        builder = self.data.get("agents", {}).get("builder", {})
        permissions = builder.get("permissions", {})
        authentication = builder.get("authentication", {})

        unrecognized = set(permissions) - BUILDER_PERMISSION_KEYS
        if unrecognized:
            raise StudioError(f"unrecognized Builder permission key(s): {', '.join(sorted(unrecognized))}")

        shell_tool = native_shell_tool()
        native_tools = _for_shell(BUILDER_TOOLS, shell_tool)
        native_allowed = _for_shell(BUILDER_ALLOWED_TOOLS, shell_tool)
        native_denied = _for_shell(BUILDER_DENIED_TOOLS, shell_tool)
        if shell_tool == SHELL_TOOL_WINDOWS:
            native_denied = _unique(native_denied, BUILDER_DENIED_TOOLS_WINDOWS_ONLY)

        permission_mode = permissions.get("mode", "dontAsk")
        restricted = permissions.get("restricted_to_worktree", True)
        configured_deny = _for_shell(tuple(permissions.get("deny", ())), shell_tool)
        denied = _unique(native_denied, configured_deny)
        forbidden_env = _unique(
            BUILDER_FORBIDDEN_ENVIRONMENT_VARIABLES,
            tuple(authentication.get("forbidden_environment_variables", ())),
        )

        if permission_mode != "dontAsk":
            raise StudioError("Builder permissions must use dontAsk mode")
        if restricted is not True:
            raise StudioError("Builder permissions must remain restricted to the worktree")

        return BuilderPolicy(
            permission_mode=permission_mode,
            restricted_to_worktree=restricted,
            tools=native_tools,
            allowed_tools=native_allowed,
            denied_tools=denied,
            forbidden_environment_variables=forbidden_env,
        )

def load_config(root: Path) -> Config:
    path = root / ".studio" / "studio.yaml"
    if not path.exists():
        raise StudioError(f"missing config: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise StudioError(f"{path} must use JSON-compatible YAML syntax: {e}") from e
    return Config(data or {}, path)
