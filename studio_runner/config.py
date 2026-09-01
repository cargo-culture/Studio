from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
from .util import StudioError


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

        permission_mode = permissions.get("mode", "dontAsk")
        restricted = permissions.get("restricted_to_worktree", True)
        tools = tuple(permissions.get("tools", BUILDER_TOOLS))
        allowed = tuple(permissions.get("allow", BUILDER_ALLOWED_TOOLS))
        denied = _unique(BUILDER_DENIED_TOOLS, tuple(permissions.get("deny", ())))
        forbidden_env = _unique(
            BUILDER_FORBIDDEN_ENVIRONMENT_VARIABLES,
            tuple(authentication.get("forbidden_environment_variables", ())),
        )

        if permission_mode != "dontAsk":
            raise StudioError("Builder permissions must use dontAsk mode")
        if restricted is not True:
            raise StudioError("Builder permissions must remain restricted to the worktree")
        if tuple(tools) != BUILDER_TOOLS:
            raise StudioError("Builder tool access must use the fixed worktree-only tool set")
        unknown = set(allowed) - set(BUILDER_ALLOWED_TOOLS)
        if unknown:
            raise StudioError(f"unsafe Builder allow rule(s): {', '.join(sorted(unknown))}")
        missing_file_tools = {"Read", "Glob", "Grep", "Edit", "Write"} - set(allowed)
        if missing_file_tools:
            raise StudioError(f"Builder file tool(s) missing: {', '.join(sorted(missing_file_tools))}")

        return BuilderPolicy(
            permission_mode=permission_mode,
            restricted_to_worktree=restricted,
            tools=tools,
            allowed_tools=allowed,
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
