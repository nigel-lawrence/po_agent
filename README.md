# PO Agent - Product Owner Assistant for Jira

An intelligent agent system designed to help Product Owners manage their Jira backlog more efficiently by automating repetitive tasks and ensuring quality standards.

## 🎯 Overview

PO Agent provides three powerful CLI tools to help Product Owners:

1. **Issue Creator** - Draft well-structured Jira issues with complete story syntax and acceptance criteria
2. **Refinement Preparation** - Review and score backlog items against your Definition of Ready
3. **Backlog Cull** - Identify stale issues that may be candidates for removal

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
```

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

# Export to CSV
python src/backlog_cull.py --export-csv
```

This will:
- Find issues older than threshold with no recent activity
- Calculate staleness scores
- Display candidates in a ranked table
- Offer bulk actions (label, comment, generate report)

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
│   └── backlog_cull.py          # Backlog cull tool
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
4. **Iterate on DoR scores** - Don't aim for 100% immediately, focus on continuous improvement
5. **Use GitHub Copilot** - Let AI help with repetitive content generation

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
