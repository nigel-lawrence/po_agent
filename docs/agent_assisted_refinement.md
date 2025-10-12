# Agent-Assisted Refinement Mode

> ⚠️ **NOTICE**: This document has been merged into `.github/copilot-instructions.md` as of October 12, 2025.  
> Please refer to that file for the current, consolidated instructions.  
> This file is kept for historical reference only.

**Last Updated**: October 12, 2025

## Overview

Agent-Assisted Refinement Mode is the **recommended workflow** for preparing backlog items for refinement sessions. It combines the deterministic scoring from CLI tools with LLM-powered analysis and direct Jira updates via MCP tools.

## Why This Approach?

### Problems with Pure CLI Mode
- ❌ CLI can only check deterministic fields (title, account, story points)
- ❌ Can't evaluate quality of story syntax or acceptance criteria
- ❌ Can't suggest contextual improvements
- ❌ Limited interactivity for updates

### Benefits of Agent-Assisted Mode
- ✅ **Deterministic scoring** from CLI (fast, accurate)
- ✅ **LLM analysis** for quality evaluation (story syntax, acceptance criteria)
- ✅ **Contextual suggestions** based on issue content
- ✅ **Direct Jira updates** via MCP with PO approval
- ✅ **Progressive refinement** - work through backlog in priority order

## The Workflow

### Step 1: Get Deterministic Scores
```bash
python src/refinement_prep.py
```

This generates:
- DoR scores for top N backlog items
- Missing deterministic fields (Title, Account, Story Points, etc.)
- Backlog order (Sprint ASC, RANK)

**Output Example:**
```
┏━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━-━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Rank ┃ Key        ┃ Score    ┃ Summary                 ┃ Missing (Deterministic)           ┃
┡━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━-━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 1    │ DD-1141    │ 60%      │ GitHub EMU prep - IAC   │ Story Points                      │
│ 2    │ DD-1147    │ 60%      │ GitHub EMU prep - RBA   │ Story Points                      │
│ 3    │ DD-1069    │ 44%      │ Provide secure platform │ Story Syntax, Points              │
```

### Step 2: Agent Steps Through Each Issue

For each issue in backlog order:

#### 2a. Fetch Full Context
```
Use: mcp_atlassian_getJiraIssue(cloudId, issueIdOrKey)
```
Get complete issue data including:
- Description
- Story syntax (customfield_12015)
- Acceptance criteria (customfield_11874)
- All metadata

#### 2b. LLM Analysis
Analyze non-deterministic criteria:

**Story Syntax Quality** (for Stories)
- Is it template text or meaningful?
- Does it follow "As a... I want... So that..." format?
- Is it specific and valuable?

**Acceptance Criteria Quality**
- Are they in BDD/Gherkin format?
- Are they testable and specific?
- Do they define outcomes clearly?

**Description Analysis**
- **Environments**: Mentions staging/pre-prod/production?
- **Security**: Addresses risks, threats, auth concerns?
- **Documentation**: Links to wikis, Confluence, ADRs?
- **Demo scope**: Defines what will be shown?
- **Cost**: Discusses budget, infrastructure costs?
- **Telemetry**: Specifies metrics, alerts, monitoring?

#### 2c. Present Analysis to PO
```
Issue: DD-1141 - GitHub EMU prep - IAC
Type: Task
Score: 60%

✅ Good:
- Title is clear
- Account code set
- Acceptance criteria present
- Story syntax N/A (not a story)

❌ Missing:
- Story Points (deterministic)
- Demo scope (not mentioned)
- Cost implications (not mentioned)

⚠️ Could Improve:
- Acceptance criteria is brief, could be more specific with BDD scenarios
- Description has good documentation links ✓
- Security mentioned (SSH keys) ✓

Suggestions:
1. Add 5 story points (based on checklist complexity)
2. Add comment for demo scope: "Demo: Show successful repo access and CODEOWNERS validation"
3. Optionally: Expand acceptance criteria with specific scenarios

Should I make these updates?
```

#### 2d. Get PO Approval
Wait for PO to approve specific changes:
- "Yes, add the points and demo comment"
- "Just the points, skip the demo"
- "Skip this one, move to next"

#### 2e. Update Jira via MCP
Based on approval, use:

**Update Fields:**
```
mcp_atlassian_editJiraIssue(
  cloudId, 
  issueIdOrKey, 
  fields: {
    "customfield_10100": 5,  // Story points
    "customfield_12015": { ... },  // Story syntax (if needed)
    "customfield_11874": { ... }   // Acceptance criteria (if needed)
  }
)
```

**Add Comments:**
```
mcp_atlassian_addCommentToJiraIssue(
  cloudId,
  issueIdOrKey,
  commentBody: "Demo scope: Show successful repo access and CODEOWNERS validation"
)
```

**Transition Status** (if DoR met):
```
mcp_atlassian_transitionJiraIssue(
  cloudId,
  issueIdOrKey,
  transition: { id: "..." }  // Move to "Ready"
)
```

#### 2f. Show Result & Move Next
```
✅ Updated DD-1141:
- Added 5 story points
- Added demo scope comment
- New score: 68% (was 60%)

Moving to next issue: DD-1147...
```

### Step 3: Repeat Until Complete
Continue through backlog until:
- PO says "that's enough"
- All top N items reviewed
- Sufficient items are "Ready" for refinement session

## Special Handling

### Story Syntax for Non-Stories
- **Tasks/Bugs**: Story syntax is optional
- If empty or template text → Mark as "N/A" ✅
- If filled meaningfully → Bonus points ✅
- Don't require it for non-story types

### Acceptance Criteria Quality
Even if field is populated, evaluate:
- Is it just boilerplate?
- Could it be more specific?
- Suggest BDD improvements

### Epic Link (Optional)
- Don't penalize if missing
- But suggest linking if epic is obvious

## Example Session

```
User: "Help me prep for refinement"

Agent:
1. Runs: python src/refinement_prep.py
2. Shows: "Found 20 items, average score 48.8%"
3. "Let me step through the top items with you..."

--- Issue 1: DD-1141 ---
[Fetch via MCP, analyze, suggest improvements]
"Shall I add 5 points and demo comment?"
User: "Yes"
[Update via MCP]
"✅ Done. New score: 68%"

--- Issue 2: DD-1147 ---
[Repeat process]

--- Issue 3: DD-1069 ---
"This is a Story but has no story syntax. Let me draft one:
  As a data engineer
  I want a secure platform to process DB1B data
  So that we can deliver business insights while meeting compliance requirements

Shall I update?"
User: "Yes, looks good"
[Update via MCP]
"✅ Done. New score: 60% (was 44%)"

[Continue until PO is satisfied...]

Summary:
✅ Updated 8 issues
✅ Average score improved: 48.8% → 58.2%
✅ 3 issues now Ready (≥70%)
```

## Key Principles

1. **CLI first, Agent second** - Get deterministic data fast, then add intelligence
2. **One issue at a time** - Don't overwhelm, stay focused
3. **Always ask permission** - Never update without PO approval
4. **Be specific** - Show exact changes you'll make
5. **Show progress** - Report scores before/after updates
6. **Know when to stop** - Respect PO's time, not everything needs 100%

## Integration with Existing Tools

### `refinement_prep.py` Role
- Provides initial scoring
- Returns deterministic field status
- **Does NOT** do LLM analysis
- **Does NOT** update Jira directly

### Agent (You) Role
- Fetches full issue context
- Performs LLM quality analysis
- Suggests contextual improvements
- Updates Jira via MCP after approval

### `issue_creator.py` Role
- Still used for creating NEW issues
- Guided workflow for complete issues
- Agent-assisted mode is for EXISTING backlog

## Success Metrics

After agent-assisted refinement session:
- ✅ Improved average DoR score
- ✅ More issues "Ready" for refinement (≥70%)
- ✅ Better quality story syntax and acceptance criteria
- ✅ Fewer missing fields
- ✅ PO confident about refinement session

## Future Enhancements

Potential improvements:
- Batch update mode (with bulk approval)
- AI-powered story point estimation
- Template detection for acceptance criteria
- Auto-linking to epics based on content
- Integration with refinement session notes
