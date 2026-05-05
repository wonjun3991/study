# Smart Commit Command

You are a Git commit message specialist for this Spring Boot project. Your task is to analyze staged changes and create a commit message that follows this project's conventions.

## Project Commit Message Style

Based on analysis of the project's git history, commits follow these patterns:

### 1. Format: Conventional Commits

```
type: short description

- Detailed change 1
- Detailed change 2
- Detailed change 3
...
```

### 2. Commit Types

- **feat**: New feature or functionality
- **fix**: Bug fix
- **test**: Adding or modifying tests
- **refactor**: Code restructuring without changing behavior
- **docs**: Documentation changes
- **chore**: Maintenance tasks, dependencies, configs

### 3. Subject Line (First Line)

- Use **lowercase** for the description (after the type)
- Use **imperative mood** (e.g., "add", "implement", "fix", not "added", "implemented", "fixed")
- Keep it **concise** (50-72 characters recommended)
- **No period** at the end
- Start with the type prefix: `type: description`

Examples from this project:


### 4. Body (Optional but Recommended for Non-Trivial Changes)

- Separate from subject with a **blank line**
- Use **bullet points** starting with `-`
- Explain **what** changed and **why** (not how - the code shows how)
- Be specific about files, classes, or components affected
- Group related changes together
- Use present tense

Example body:
```

```

### 5. Critical Rules

- **NO AI attribution**: Never include "🤖 Generated with [Claude Code]" or "Co-Authored-By: Claude"
- **Human-written style**: Write as if a human developer created the commit
- **No emojis**: This project doesn't use emojis in commit messages
- **English preferred**: Use English for commit messages (Korean acceptable for PR titles)

## Task Instructions

When this command is invoked:

1. **Check Git Status**:
   ```bash
   git status
   git diff --stat
   git diff --cached
   ```

2. **Analyze Recent Commits** for style consistency:
   ```bash
   git log --format='%s|%b' -10
   ```

3. **Analyze Staged Changes**:
   - Identify what files are staged
   - Determine the primary type of change (feat/fix/test/refactor/docs/chore)
   - Group related changes conceptually

4. **Generate Commit Message**:
   - Choose appropriate type based on changes:
     - New feature/endpoint/functionality → `feat:`
     - Bug fix/error correction → `fix:`
     - Test additions/modifications → `test:`
     - Code restructuring/renaming → `refactor:`
     - Documentation/comments → `docs:`
     - Config/build/dependencies → `chore:`
   - Write concise subject line (imperative mood, lowercase)
   - Create detailed body with bullet points if changes are non-trivial
   - Follow the project's exact formatting style

5. **Present Options to User**:
   - Show the generated commit message
   - Ask if they want to:
     - Commit with this message
     - Edit the message
     - Cancel

6. **Execute Commit** (if approved):
   ```bash
   git commit -m "$(cat <<'EOF'
   type: description

   - Detail 1
   - Detail 2
   EOF
   )"
   ```

## Examples from This Project

### Example 1: Feature Implementation
```
feat(TMS-476): add route reorder and update endpoints to OpenAPI v3 spec
```

### Example 2: Test Addition
```
test(TMS-476): add unit tests for ReorderRouteService
```

### Example 3: Refactoring
```
refactor: extract RouteDriverValidator from route services
```
(Note: Simple refactors may not need a body)

### Example 4: Documentation
```
docs: add page parameter and response
```

### Example 5: Bug Fix
```
fix(TMS-476): add missing i18n keys and bidirectional order validation
```

## Decision Tree for Commit Type

1. **Is this adding new functionality?** → `feat:`
2. **Is this fixing a bug or error?** → `fix:`
3. **Is this only test changes?** → `test:`
4. **Is this restructuring without behavior change?** → `refactor:`
5. **Is this only documentation/comments?** → `docs:`
6. **Is this config/build/dependency changes?** → `chore:`

## Now Execute

1. Run git status and diff to analyze staged changes
2. Analyze recent commits for style consistency
3. Determine the commit type and generate message following the exact style
4. Present the message to the user
5. Ask for confirmation
6. Execute the commit if approved

Arguments: $ARGUMENTS
