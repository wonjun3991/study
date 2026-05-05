---
description: Create detailed Jira ticket by analyzing codebase. Generates tickets ready for /implement-feature command execution.
---

# Create Detailed Jira Ticket

This command analyzes your codebase and creates a comprehensive Jira ticket with all the technical details needed for the `/implement-feature` command to implement the feature automatically.

## What This Command Does

1. **Analyzes your request** - Understands what feature you want
2. **Asks clarifying questions** - Priority, required/optional, single/multiple values, etc.
3. **Explores the codebase** - Finds related APIs, domain models, services, repositories
4. **Reads relevant files** - OpenAPI specs, entities, enums, interfaces
5. **Generates comprehensive ticket** - With implementation details, code examples, file paths
6. **Creates Jira ticket** - Using Jira REST API (curl) with all the details
7. **Returns ticket info** - Ticket number (TMS-XXX) and URL

## Usage

```bash
/create-ticket <feature description>
```

### Examples

```bash
# Add filter parameter to existing API
/create-ticket Add RouteStatus filter parameter to listRouteDetails

# Add new field to API
/create-ticket Add delivery memo field to Order API

# Implement new feature
/create-ticket Implement RouteCandidate status management

# Modify existing behavior
/create-ticket Update related Order status when Route is deleted
```

## User Input

Feature to implement:

{{USER_INPUT}}

## Instructions for Claude

You MUST follow this workflow to create a production-ready Jira ticket:

### Step 1: Understand the Request

Parse the user's request and identify:
- Which API/entity is affected
- What kind of change (add parameter, add field, new feature, modify behavior)
- What domain concepts are involved

### Step 2: Ask Clarifying Questions

Use `AskUserQuestion` tool to gather:

**Question 1: Parameter Type (if adding filter/parameter)**
- Single value vs Multiple values
- Example: "status=PLANNED" vs "status=PLANNED,ASSIGNED"

**Question 2: Required vs Optional**
- Is the new parameter/field required or optional?
- What happens when not provided?

**Question 3: Priority**
- Highest: Urgent, blocking work
- High: Important, near-term delivery
- Medium: Normal priority
- Low: Nice to have, can wait

**Question 4: Additional Requirements (if needed)**
- Any edge cases to handle?
- Any related features to consider?
- Any constraints or limitations?

### Step 3: Explore Codebase

Use Glob, Grep, and Read tools to find relevant files:

**3.1 Find API Definition**
Grep: pattern `operationId.*<api-name>`, path `src/main/resources/openapi`

**3.2 Find Domain Models**
Glob: pattern `**/<EntityName>.java`, path `src/main/java/com/omelet/oaasis/domain`

**3.3 Find Enums (if applicable)**
Grep: pattern `enum <EnumName>`, path `src/main/java/com/omelet/oaasis/domain`

**3.4 Find Service/UseCase**
Grep: pattern `public.*<methodName>`, path `src/main/java/com/omelet/oaasis/application`

**3.5 Find Repository**
Grep: pattern `public.*<methodName>`, path `src/main/java/com/omelet/oaasis/adapter/out/persistence`

**3.6 Find Controller Implementation**
Grep: pattern `public.*<methodName>`, path `src/main/java/com/omelet/oaasis/adapter/in/rest`

### Step 4: Read Relevant Files

Use `Read` tool to get detailed context:
- OpenAPI spec (specific endpoint section)
- Domain entities and enums
- Service interfaces
- Repository interfaces
- Controller implementations
- Related ADR documents (if architecture decision needed)

### Step 5: Generate Comprehensive Ticket Description

Create a detailed Markdown description with the following structure:

```markdown
# Overview
<1-2 sentence summary of what this feature does>

## Current State
- Current API signature or entity structure
- Current parameters/fields available
- Current behavior

## Requirements
- **<Feature Name>**: <Clear description>
- **<Constraint 1>**: <Description>
- **<Constraint 2>**: <Description>
- **Integration with existing features**: <How it works with existing features>

## Implementation Scope

### 1. OpenAPI Spec Changes
**File**: `<path-to-openapi-yaml>`

```yaml
# Add to components/parameters section (if adding parameter)
<ParameterName>:
  name: <param-name>
  in: query
  required: <true|false>
  description: <description>
  schema:
    type: <type>
    items:  # if array
      type: <item-type>
      enum:  # if enum
        - <VALUE1>
        - <VALUE2>

# Add parameter to <endpoint-path> endpoint
<endpoint-path>:
  <method>:
    parameters:
      - $ref: '#/components/parameters/<ExistingParam1>'
      - $ref: '#/components/parameters/<ExistingParam2>'
      - $ref: '#/components/parameters/<NewParam>'  # new
```

### 2. Code Generation
```bash
./gradlew cleanGeneratedApiV3 openApiGenerateV3 -x test
# OR for V2:
# ./gradlew cleanGeneratedApiV2 openApiGenerateV2 -x test
```

### 3. Implementation File Changes

#### 3.1 UseCase Interface
**File**: `<path-to-use-case-interface>`
```java
<ReturnType> <methodName>(
    <ExistingParam1> <param1>,
    <ExistingParam2> <param2>,
    <NewParamType> <newParam>);  // new
```

#### 3.2 Repository Port
**File**: `<path-to-repository-interface>`
```java
<ReturnType> <methodName>(
    <ExistingParam1> <param1>,
    <ExistingParam2> <param2>,
    <NewParamType> <newParam>);  // new
```

#### 3.3 Service Implementation
**File**: `<path-to-service-implementation>`
- Add <newParam> parameter to <methodName> method
- Pass <newParam> to repository call

#### 3.4 JPA Repository
**File**: `<path-to-jpa-repository>`
- Add <newParam> filtering logic using QueryDSL
- Skip filtering when `<newParam>` is null or empty
- Add `<entity>.<field>.in(<newParam>)` condition when value is present

#### 3.5 Controller Implementation
**File**: `<path-to-controller-implementation>`
- Update <methodName> method signature (match generated API interface)
- Convert <DtoType> to <DomainType> (using Mapper)
- Pass <newParam> to service.<methodName> call

### 4. Test Cases
**File**: `<path-to-test-file>`
- <Test case 1> test
- <Test case 2> test
- <Test case 3> test
- Combination test with other parameters

## Acceptance Criteria
- [ ] <Acceptance criterion 1>
- [ ] <Acceptance criterion 2>
- [ ] <Acceptance criterion 3>
- [ ] Unit tests and integration tests pass
- [ ] Changes visible in Swagger UI

## Reference Files
- `<file-path-1>`: <description> (line <start>-<end>)
- `<file-path-2>`: <description> (line <start>-<end>)
- `<file-path-3>`: <description> (line <start>-<end>)
```

**IMPORTANT**:
- Include specific file paths with line numbers
- Include code examples for each layer (OpenAPI, UseCase, Repository, Service, Controller)
- Include QueryDSL filter logic examples
- Include test scenarios
- Reference existing code patterns from the codebase

### Step 6: Create Jira Ticket

Use curl-based Jira API (see `.claude/skills/jira-api.md`):

1. **Write JSON to temp file** using Write tool:

```json
// /tmp/jira-create.json
{
  "fields": {
    "project": { "key": "TMS" },
    "issuetype": { "name": "Task" },
    "summary": "<Concise summary>",
    "description": "<Generated wiki markup description>",
    "priority": { "name": "<Highest|High|Medium|Low>" }
  }
}
```

2. **Create issue via curl** using Bash tool:

```bash
curl -s -X POST -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -H "Content-Type: application/json" \
  "$JIRA_BASE_URL/rest/api/2/issue" \
  -d @/tmp/jira-create.json | jq .
```

3. **Extract key and URL** from response: `jq -r '.key'` and `jq -r '.self'`

### Step 7: Output Result

After creating the ticket, output:

```
Jira ticket created successfully!

**Ticket Info:**
- **Ticket**: TMS-XXX
- **Title**: <title>
- **Priority**: <priority>
- **Link**: https://omelet.atlassian.net/browse/TMS-XXX

The ticket includes:
- Current state and requirements description
- Implementation scope (OpenAPI spec, UseCase, Repository, Service, Controller, Tests)
- Detailed code examples and list of files to modify
- Acceptance Criteria checklist
- Reference file paths

**Next Steps:**
```bash
# Implement the feature based on the ticket
/implement-feature TMS-XXX
```

## Important Notes

### What Makes a Good Ticket for /implement-feature

The ticket MUST include:

1. ✅ **Specific file paths** - Not just "update the service", but "src/main/java/.../FindRouteService.java"
2. ✅ **Code examples** - Method signatures, QueryDSL patterns, OpenAPI schemas
3. ✅ **Line numbers** - Reference existing code locations
4. ✅ **Layer-by-layer guide** - OpenAPI → UseCase → Repository → Service → Controller → Tests
5. ✅ **Clear acceptance criteria** - Testable requirements
6. ✅ **Architecture context** - How it fits into Hexagonal Architecture

### What to Avoid

- ❌ Vague descriptions like "Add a filter" without specifying how
- ❌ Missing file paths or layer information
- ❌ No code examples
- ❌ Unclear requirements
- ❌ Missing test scenarios

### Quality Checklist

Before creating the ticket, verify:
- [ ] All affected layers identified (Domain, Application, Adapter)
- [ ] File paths are absolute and correct
- [ ] Code examples match project patterns
- [ ] OpenAPI schema is valid YAML
- [ ] QueryDSL patterns follow existing code
- [ ] Test scenarios cover edge cases
- [ ] Acceptance criteria are specific and testable

## Error Handling

### If Codebase Search Fails

1. **API not found**: Search with different patterns, check both v2 and v3 APIs
2. **Entity not found**: Check package naming, search by partial name
3. **Service not found**: Look in both `application/service` and `domain` packages

### If Jira Creation Fails

1. **Authentication error (401)**: Verify `JIRA_EMAIL` and `JIRA_API_TOKEN` environment variables are set correctly
2. **Invalid field (400)**: Check required fields for the project, validate JSON with `jq . /tmp/jira-create.json`
3. **Permission denied (403)**: Verify user has create permission in TMS project
4. **Environment variables missing**: Run `echo $JIRA_BASE_URL $JIRA_EMAIL` to check

### If Requirements are Unclear

- **Ask more questions**: Use AskUserQuestion to clarify
- **Search for similar features**: Find existing patterns in codebase
- **Reference ADRs**: Check architecture decision records for guidance

## Integration with /implement-feature

The ticket you create is designed to be consumed by `/implement-feature`:

```bash
# Step 1: Create detailed ticket
/create-ticket "Add RouteStatus filter to listRouteDetails API"
# Output: TMS-408 created

# Step 2: Implement the ticket
/implement-feature TMS-408
# feature-implementer agent reads the ticket and implements everything
```

The ticket provides the agent with:
- Clear requirements
- File paths to modify
- Code patterns to follow
- Test scenarios to implement
- Validation criteria

This enables the agent to work autonomously with minimal clarification needed.

## cloudId Configuration

For this project (OaaSIS TMS):
- **cloudId**: `3a979782-5aa7-4940-ad57-16e620c0437c`
- **Project Key**: `TMS`
- **Jira URL**: https://omelet.atlassian.net

## Summary

`/create-ticket` bridges the gap between:
- 💭 **User's idea** ("I want to add a filter")
- 📋 **Detailed specification** (Complete Jira ticket)
- 🤖 **Automated implementation** (`/implement-feature` execution)

By analyzing the codebase and generating comprehensive tickets, this command enables faster feature delivery with less manual specification work.
