# Jira Integration

When working with Jira tickets (TMS-XXX), **always use Atlassian MCP tools first**.

## Available MCP Tools
- `mcp__atlassian__search`: Search for Jira issues and Confluence pages
- `mcp__atlassian__getJiraIssue`: Get detailed issue information
- `mcp__atlassian__createJiraIssue`: Create new Jira issues
- `mcp__atlassian__editJiraIssue`: Update existing issues
- `mcp__atlassian__addCommentToJiraIssue`: Add comments to issues
- `mcp__atlassian__transitionJiraIssue`: Transition issue status
- `mcp__atlassian__searchJiraIssuesUsingJql`: Advanced JQL search

## Workflow
1. **Always try MCP tools first** to fetch ticket details
2. Use `addCommentToJiraIssue` for documentation, frontend guides, technical details
3. **Markdown supported** in Jira comments
4. **Fallback only**: If MCP tools fail, provide content as formatted message for manual addition

**cloudId**: `3a979782-5aa7-4940-ad57-16e620c0437c`
