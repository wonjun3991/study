---
description: Create Jira ticket without any code modifications. Simple ticket creation only.
---

# Jira Ticket Creator

This command creates a Jira ticket in the TMS project **WITHOUT any code modifications or codebase exploration**.

## What This Command Does

1. **Collects ticket information** from user input
2. **Asks clarifying questions** (optional)
3. **Creates Jira ticket** using Atlassian MCP
4. **Returns ticket information**

## What This Command DOES NOT Do

- ❌ **NO code modifications** - Does not edit any files
- ❌ **NO codebase exploration** - Does not read or search code
- ❌ **NO .claude directory changes** - Does not touch configuration
- ❌ **NO implementation planning** - Just creates the ticket

## Usage

```bash
/jira-ticket <ticket title>
```

### Examples

```bash
# Simple task
/jira-ticket users/me API에 role 정보 포함

# Feature request
/jira-ticket 배송 메모 필드 추가

# Bug report
/jira-ticket Order 삭제 시 연관 데이터 정리 안됨

# Enhancement
/jira-ticket API 응답 속도 개선
```

## User Input

Ticket title and description:

{{USER_INPUT}}

## Instructions for Claude

### Critical Rules

**YOU MUST NOT:**
- ❌ Read any code files
- ❌ Search the codebase
- ❌ Modify any files (including .claude directory)
- ❌ Use Glob, Grep, or Read tools
- ❌ Use Task or Explore agents
- ❌ Make any code changes

**YOU MUST ONLY:**
- ✅ Parse user input for ticket information
- ✅ Ask clarifying questions if needed
- ✅ Create Jira ticket using Atlassian MCP
- ✅ Return ticket information to user

### Step 1: Parse User Input

Extract from user input:
- **Title**: Main ticket title
- **Description**: Any additional details provided by user

If user provides only a title, that's sufficient to create a basic ticket.

### Step 2: Ask Clarifying Questions (Optional)

Use `AskUserQuestion` tool ONLY if essential information is missing:

**Question 1: Issue Type**
- Task: New feature or improvement
- Bug: Something is broken
- Story: User story format

**Question 2: Priority**
- Highest: Urgent, blocking work
- High: Important, near-term delivery
- Medium: Normal priority (default)
- Low: Nice to have

**Question 3: Additional Details (Optional)**
- Any specific requirements?
- Any acceptance criteria?
- Any related tickets?

### Step 3: Create Jira Ticket

Use Atlassian MCP to create the ticket:

```
mcp__atlassian__createJiraIssue:
  cloudId: "3a979782-5aa7-4940-ad57-16e620c0437c"
  projectKey: "TMS"
  issueTypeName: "<Task|Bug|Story>"
  summary: "<Ticket title>"
  description: "<Ticket description>"
  additional_fields:
    priority:
      name: "<Highest|High|Medium|Low>"
```

**Description Format:**
```markdown
# 개요
<User's description or summary>

## 상세 내용
<Any additional details from user input>

## Acceptance Criteria
<If provided by user>
```

### Step 4: Output Result

After creating the ticket, output:

```
✅ Jira 티켓이 성공적으로 생성되었습니다!

**티켓 정보:**
- **티켓 번호**: TMS-XXX
- **제목**: <title>
- **타입**: <Task|Bug|Story>
- **우선순위**: <priority>
- **링크**: https://omelet.atlassian.net/browse/TMS-XXX
```

## Default Values

If user doesn't specify:
- **Issue Type**: Task
- **Priority**: Medium
- **Description**: Use the title as the summary

## Configuration

- **cloudId**: `3a979782-5aa7-4940-ad57-16e620c0437c`
- **Project Key**: `TMS`
- **Jira URL**: https://omelet.atlassian.net

## Examples

### Example 1: Simple Title Only

Input:
```
/jira-ticket API 응답에 사용자 권한 정보 추가
```

Output:
```
✅ Jira 티켓이 성공적으로 생성되었습니다!

**티켓 정보:**
- **티켓 번호**: TMS-439
- **제목**: API 응답에 사용자 권한 정보 추가
- **타입**: Task
- **우선순위**: Medium
- **링크**: https://omelet.atlassian.net/browse/TMS-439
```

### Example 2: With Description

Input:
```
/jira-ticket Order 삭제 시 연관된 Route도 함께 정리

현재는 Order를 삭제해도 Route가 남아있어서 데이터 정합성 문제가 발생합니다.
Order 삭제 시 연관된 Route의 상태를 CANCELLED로 변경하거나 함께 삭제해야 합니다.
```

Output:
```
✅ Jira 티켓이 성공적으로 생성되었습니다!

**티켓 정보:**
- **티켓 번호**: TMS-440
- **제목**: Order 삭제 시 연관된 Route도 함께 정리
- **타입**: Task
- **우선순위**: Medium
- **링크**: https://omelet.atlassian.net/browse/TMS-440
```

## Error Handling

### If Jira Creation Fails

1. **Authentication error**:
   - Verify cloudId is correct
   - Check user has Jira access

2. **Invalid field**:
   - Check required fields for TMS project
   - Verify issue type name is correct

3. **Permission denied**:
   - Verify user has create permission in TMS project

If any error occurs, simply report the error to the user without making any code changes.

## Summary

`/jira-ticket` is a simple, focused command that:
- ✅ Creates Jira tickets quickly
- ✅ Minimal user interaction
- ✅ No code modifications
- ✅ No codebase exploration
- ✅ Safe to use anytime

Perfect for creating tickets when you already know what needs to be done and just need to track it in Jira.
