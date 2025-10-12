# PO Agent - Quick Reference

## Setup (First Time Only)

```bash
# Run automated setup
chmod +x setup.sh
./setup.sh

# OR manual setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials
```

## Daily Usage

### Activate Virtual Environment
```bash
source venv/bin/activate
```

### Create a New Issue
```bash
python src/issue_creator.py
```

### Prepare for Refinement
```bash
python src/refinement_prep.py
```

### Find Stale Issues
```bash
# Default settings (180 days old, 90 days inactive)
python src/backlog_cull.py

# Custom thresholds
python src/backlog_cull.py --age 90 --activity 60 --refinement 40

# Export results
python src/backlog_cull.py --export-csv
```

### When Done
```bash
deactivate
```

## Quick Tips

### Check DoR Score for an Issue
```python
# In Python shell (with venv activated)
from src.jira_client import JiraClient
from src.dor_checker import DoRChecker

client = JiraClient()
checker = DoRChecker()

issue = client.get_issue('DD-123')
result = checker.check_issue(issue)
print(f"Score: {result['percentage']}%")
```

### Search for Issues
```python
from src.jira_client import JiraClient

client = JiraClient()
results = client.search_issues('project = DD AND status = "Not Ready"')
print(f"Found {len(results['issues'])} issues")
```

## Common JQL Queries

```python
# All Not Ready items
'project = DD AND status = "Not Ready" ORDER BY rank'

# Old unresolved items
'project = DD AND resolution = Unresolved AND created < -6m'

# Items without story points
'project = DD AND "Story Points" is EMPTY'

# Items without acceptance criteria
'project = DD AND cf[12016] is EMPTY'
```

## Troubleshooting

### Import Errors
```bash
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

### Connection Errors
```bash
# Test connection
python src/jira_client.py

# Check .env file
cat .env
```

### Custom Field IDs
```python
# Find custom field IDs
from src.jira_client import JiraClient
client = JiraClient()
issue = client.get_issue('DD-1234')
# Look for customfield_* in the response
import json
print(json.dumps(issue['fields'], indent=2))
```

## GitHub Copilot Integration

Ask Copilot:
- "Create a new story for [feature]"
- "Review my backlog for refinement"
- "Find stale issues to remove"
- "What's the DoR score for DD-123?"
- "Draft acceptance criteria for [scenario]"

## Configuration Files

- `.env` - Jira credentials (never commit!)
- `config.yaml` - Project settings and DoR checklist
- `.github/copilot-instructions.md` - Copilot agent instructions

## Useful Commands

```bash
# Check Python version
python --version

# List installed packages
pip list

# Update a package
pip install --upgrade requests

# View project structure
tree -L 2 -I 'venv|__pycache__|*.pyc'
```

## Definition of Ready Score

- **90-100%**: ✅ Ready for refinement
- **70-89%**: ⚠️  Nearly ready (minor gaps)
- **50-69%**: 🔸 Partially ready (needs work)
- **0-49%**: ❌ Not ready (major gaps)

## Support

- Check README.md for detailed documentation
- Review .github/copilot-instructions.md for AI assistance
- Open GitHub issues for bugs or feature requests
