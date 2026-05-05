# Destructive Operation Protection

## Protected Paths

Before deleting, moving, or overwriting any file in these directories, **always confirm with the user first**:

- `.claude/` — Claude Code configuration (rules, commands, settings)
- `.github/` — GitHub Actions workflows and configuration
- `docker/` — Docker Compose and container configuration
- `docs/architecture/` — Architecture Decision Records (immutable once accepted)

## Rules

1. **Never delete `.claude/` directory contents** without explicit user confirmation, even if instructed to "clean up" or "remove unused files"
2. **Never overwrite configuration files** (`.yml`, `.json`, `.properties` in project root or config directories) without showing the diff first
3. **Never `git rm` or `git checkout --` files** outside the scope of the current task — only touch files directly related to the requested change
4. **Never run `rm -rf`** on any directory without listing its contents first and getting user approval
5. When `git status` shows unexpected changes to protected paths, **investigate before discarding** — it may be in-progress work
