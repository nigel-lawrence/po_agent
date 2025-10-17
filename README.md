# PO Agent - Product Owner Assistant for Jira

An intelligent agent system designed to help Product Owners manage their Jira backlog more efficiently by automating repetitive tasks and ensuring quality standards.

## 🎯 Overview

PO Agent provides four powerful CLI tools to help Product Owners:

1. **Issue Creator** - Draft well-structured Jira issues with complete story syntax and acceptance criteria
2. **Refinement Preparation** - Review and score backlog items against your Definition of Ready
3. **Backlog Cull** - Identify stale issues that may be candidates for removal
4. **Tempo Timesheet Checker** - Monitor team timesheet submissions and identify missing account codes

## ✨ Features

- **Definition of Ready Scoring** - Automatically scores issues against your team's DoR checklist
- **Agent-Assisted Refinement** - 🌟 Step through backlog items with AI-powered suggestions and direct Jira updates
- **Interactive Workflows** - Guided prompts help create complete, refinement-ready issues
- **BDD/Gherkin Support** - Built-in templates for acceptance criteria
- **Bulk Operations** - Efficiently manage multiple backlog items
- **GitHub Copilot Integration** - Custom instructions for AI-assisted backlog management
- **Atlassian MCP Integration** - Works seamlessly with Jira via MCP tools

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Jira account with API access
- Jira API token ([How to create](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/))
- Tempo API token (optional, for timesheet checking) ([How to create](https://help.tempo.io/cloud/en/tempo-timesheets/getting-started/how-to-create-an-api-token-in-tempo.html))

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd po_agent
   ```

2. **Create and activate a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Configure credentials**
   ```bash
   cp .env.example .env
   # Edit .env with your Jira credentials
   ```

5. **Update configuration**
   Edit `config.yaml` to match your Jira project settings (see Configuration section below)

6. **Test the connection**
   ```bash
   python src/jira_client.py
   ```

**Quick Setup (Automated):**
```bash
chmod +x setup.sh
./setup.sh
```

**Note:** Always activate the virtual environment before running the tools:
```bash
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

To deactivate when done:
```bash
deactivate
```

## 📝 Configuration

### Environment Variables (.env)

```env
JIRA_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-api-token-here
TEMPO_API_TOKEN=your-tempo-api-token-here  # Optional: for timesheet checking
TEMPO_TEAM_NAME=Your Team Name              # Optional: your Tempo team name
```

**Getting API Tokens:**
- **Jira API Token**: Go to [Atlassian Account Settings](https://id.atlassian.com/manage-profile/security/api-tokens) → Create API token
- **Tempo API Token**: In Tempo → Settings → API Integration → New Token (requires Tempo admin permissions)
- **Tempo Team Name**: Found in Tempo → Teams → Your team's display name (must match exactly)

### Project Configuration (config.yaml)

Key settings to update:

```yaml
project:
  prefix: "DD"  # Your project key
  cloud_id: "your-cloud-id"  # Your Atlassian Cloud ID
  name: "Your Project Name"

custom_fields:
  story_syntax: "customfield_12015"  # Your story syntax field ID
  acceptance_criteria: "customfield_12016"  # Your AC field ID
  # ... other custom fields
```

**Finding Your Custom Field IDs:**
- Use the Jira REST API browser: `https://your-domain.atlassian.net/rest/api/3/issue/YOUR-ISSUE-KEY`
- Look for fields starting with `customfield_`
- Or use the MCP tools to query an issue and inspect the response

## 🛠️ Usage

### 1. Issue Creator

Create a new, well-structured Jira issue:

```bash
# Make sure virtual environment is activated
source venv/bin/activate

python src/issue_creator.py
```

The tool will guide you through:
- Selecting issue type (Story, Task, Bug, etc.)
- Writing story syntax ("As a... I want... So that...")
- Defining BDD/Gherkin acceptance criteria
- Specifying environments, security, cost, and telemetry considerations
- Checking the Definition of Ready score

### 2. Refinement Preparation

Prepare for a refinement session by analyzing backlog items:

#### CLI Mode (Deterministic Scoring)
```bash
python src/refinement_prep.py
```

This will:
- Fetch top N items from backlog in "Not Ready" status
- Score each against your Definition of Ready (deterministic fields only)
- Display results in a sortable table showing missing fields
- Provide quick overview of backlog health

#### 🌟 Agent-Assisted Mode (Recommended)

For the best results, use **Agent-Assisted Refinement Mode** with GitHub Copilot:

1. **First, run the CLI tool** to get deterministic scores:
   ```bash
   python src/refinement_prep.py
   ```

2. **Then, ask GitHub Copilot**: "Help me prep for refinement"

3. **The agent will**:
   - Step through each issue in backlog order
   - Fetch full issue context via MCP
   - Analyze story syntax and acceptance criteria quality
   - Suggest specific improvements (story points, demo scope, etc.)
   - Ask permission before making updates
   - Update Jira directly via MCP tools

**Example Agent Session:**
```
You: "Help me prep for refinement"

Agent: "I found 20 items in 'Not Ready' status. Let me review them..."

Issue DD-1141 (60% ready):
✅ Has: Title, Account, Acceptance Criteria
❌ Missing: Story Points
💡 Suggestions:
  1. Add 5 story points (based on scope)
  2. Add demo scope comment

Should I make these updates? 

You: "Yes"

Agent: ✅ Updated DD-1141. New score: 68%
```

See [Agent-Assisted Refinement Guide](docs/agent_assisted_refinement.md) for full details.

### 3. Backlog Cull

Identify stale issues that may need removal:

```bash
python src/backlog_cull.py
```

With options:
```bash
# Custom thresholds
python src/backlog_cull.py --age 180 --activity 90 --refinement 30
```

This will:
- Find issues older than threshold with no recent activity
- Calculate staleness scores (0-100, higher = more stale)
- Display each candidate with full details in AI-friendly format:
  - Full issue key (no truncation)
  - Complete summary
  - Direct Jira URL
  - Age, last update, DoR score
  - Status, priority, assignee
  - Engagement metrics (comments, watchers)
- Perfect for AI agents to review and process

**Output Example:**
```
📋 Found 15 Stale Backlog Items

#1 - DD-405 (Task)
https://cirium.atlassian.net/browse/DD-405
Add git hook to automatically check branch protection rules

  Staleness: 94/100 (VERY STALE)
  • Age: 456 days (created 2024-01-15)
  • Last updated: 456 days ago (2024-01-15)
  • DoR Score: 30%
  • Status: Not Ready
  • Priority: Low
  • Assignee: Unassigned
  • Comments: 0
  • Watchers: 1
```

**💡 Best Practice:** Use agent-assisted mode (with GitHub Copilot) to review and act on these issues. The agent can help you decide what to keep, update, or close.

### 4. Tempo Timesheet Checker

Monitor team timesheet submissions and identify issues needing attention:

```bash
# Check last week (default)
python src/tempo_chaser.py

# Check a specific week
python src/tempo_chaser.py --weeks-ago 2  # Check 2 weeks ago
python src/tempo_chaser.py --weeks-ago 3  # Check 3 weeks ago
```

This will:
- **Part 1: Submission Status** - Show which team members have/haven't submitted timesheets
- **Part 2: Time Breakdown** - Display detailed breakdown of time logged by Jira card for submitted timesheets
- **Part 3: Account Code Status** - Identify and highlight any Jira cards missing account codes

The report provides:
- List of team members who need to submit (with email addresses for follow-up)
- Per-person time breakdown showing hours logged on each Jira card
- Percentage of time spent on each card
- Direct links to Jira issues
- Account code validation with clear warnings for missing codes
- Actionable summary of what needs attention

**Perfect for:**
- Weekly timesheet reminders
- Ensuring proper cost tracking via account codes
- Understanding team capacity and utilization
- Following up on overdue submissions

## 📊 Definition of Ready Checklist

Issues are scored against these criteria:

1. ✅ Title completed
2. ✅ Linked to an epic (if relevant)
3. ✅ Account code set
4. ✅ Story syntax (for stories)
5. ✅ Acceptance Criteria in BDD/Gherkin format
6. ✅ Environments defined
7. ✅ Security considerations documented
8. ✅ Relevant documentation identified
9. ✅ Points estimated
10. ✅ Demo scope defined
11. ✅ Cost implications considered
12. ✅ Telemetry/metrics defined

Each item is weighted and scored to produce an overall readiness percentage.

## 🤖 GitHub Copilot Integration

This project includes custom instructions for GitHub Copilot to act as a specialized PO Agent.

### Setup

1. The instructions are in `.github/copilot-instructions.md`
2. GitHub Copilot will automatically use these when working in this repository
3. You can ask Copilot to:
   - "Help me create a new story for user authentication"
   - "Prepare my backlog for refinement tomorrow"
   - "Identify stale issues we should remove"

### Example Interactions

**Creating a Story:**
```
You: "I need a story for adding Redis caching"
Copilot: "Let me help you create a complete story. I'll draft the story syntax 
and acceptance criteria..."
```

**Refinement Prep:**
```
You: "Review my backlog for tomorrow's refinement"
Copilot: "I'll run the refinement prep tool and analyze your top backlog items..."
```

## 🏗️ Architecture

```
po_agent/
├── .github/
│   └── copilot-instructions.md  # Custom Copilot instructions
├── src/
│   ├── __init__.py
│   ├── jira_client.py           # Jira API client
│   ├── dor_checker.py           # Definition of Ready scorer
│   ├── issue_creator.py         # Interactive issue creator
│   ├── refinement_prep.py       # Refinement preparation tool
│   ├── backlog_cull.py          # Backlog cull tool
│   └── tempo_chaser.py          # Tempo timesheet checker
├── config.yaml                   # Project configuration
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment template
└── README.md
```

## 🔧 Customization

### Adjusting DoR Checklist

Edit `config.yaml` under `definition_of_ready`:

```yaml
definition_of_ready:
  - field: "summary"
    name: "Title completed"
    weight: 1  # Adjust weight (importance)
  # Add, remove, or modify items
```

### Changing Thresholds

Edit `config.yaml` under specific tool sections:

```yaml
backlog_cull:
  age_threshold_days: 180      # Adjust age threshold
  min_refinement_score: 30     # Adjust minimum score
  no_activity_days: 90         # Adjust activity threshold

refinement_prep:
  backlog_top_items: 20        # Number of items to review
  min_readiness_score: 70      # Minimum score for "ready"
```

### Templates

Customize templates in `config.yaml`:

```yaml
templates:
  story_syntax: |
    As a [USER TYPE]
    I want [FEATURE]
    So that [VALUE]
```

## 🤝 Working with MCP Tools

The CLI tools complement the Atlassian MCP tools:

- **Use CLI tools for**: Batch operations, guided workflows, scoring
- **Use MCP tools for**: Quick lookups, single operations, ad-hoc queries

Example using both:
```python
# Use MCP to fetch an issue
issue = mcp_atlassian_getJiraIssue(cloudId, issueKey)

# Use CLI to score it
python3 src/dor_checker.py
```

## 📈 Best Practices

1. **Run refinement prep before every refinement session** - Ensures you're working on the right items
2. **Create issues with the issue creator** - Maintains consistency and quality
3. **Regular backlog culling** - Keep your backlog manageable (monthly or quarterly)
4. **Weekly timesheet checks** - Run tempo_chaser.py every Monday to follow up on submissions
5. **Ensure account codes are set** - Use tempo reports to identify and fix missing account codes
6. **Iterate on DoR scores** - Don't aim for 100% immediately, focus on continuous improvement
7. **Use GitHub Copilot** - Let AI help with repetitive content generation

## 🐛 Troubleshooting

### Connection Issues

```bash
# Activate virtual environment first
source venv/bin/activate

# Test Jira connection
python src/jira_client.py
```

Check:
- `.env` file has correct credentials
- API token is valid
- Cloud ID is correct

### Custom Field Issues

If custom fields aren't working:
1. Use MCP tools to fetch an issue
2. Inspect the response for `customfield_*` IDs
3. Update `config.yaml` with correct IDs

### Import Errors

```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

## 🗺️ Roadmap

Future enhancements:
- [ ] Web UI for non-technical users
- [ ] Integration with MS Copilot
- [ ] Advanced analytics and reporting
- [ ] Team velocity tracking
- [ ] Epic-level DoR checking
- [ ] Automated backlog health monitoring

## 📄 License

[Your License Here]

## 🙏 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## 📞 Support

For issues or questions:
- Open a GitHub issue
- Contact the maintainers
- Check the troubleshooting section

---

**Made with ❤️ for Product Owners who want to focus on strategy, not toil.**
