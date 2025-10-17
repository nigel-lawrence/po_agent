#!/usr/bin/env python3
"""
Refinement Preparation - Review and improve backlog items for refinement sessions

This tool helps Product Owners review items at the top of the backlog that are
in "Not Ready" state, score their readiness, and interactively improve them.
"""

import sys
import yaml
from typing import List, Dict, Any
from rich.console import Console
from rich.progress import track
from jira_client import JiraClient
from dor_checker import DoRChecker

console = Console()


class RefinementPrep:
    """
    Tool for preparing backlog items for refinement
    """

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize refinement prep tool
        
        Args:
            config_path: Path to configuration file
        """
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.client = JiraClient(config_path)
        self.checker = DoRChecker(config_path)
        self.project_key = self.config['project']['prefix']
        
        # Get configuration
        self.top_items = self.config['refinement_prep']['backlog_top_items']
        self.min_readiness = self.config['refinement_prep']['min_readiness_score']
        self.not_ready_status_id = self.config['statuses']['not_ready']
    
    def run_analysis(self):
        """
        Run refinement preparation analysis
        """
        console.print("\n[bold blue]🔍 Refinement Preparation Analysis[/bold blue]")
        console.print(f"Analyzing top {self.top_items} backlog items in 'Not Ready' status\n")
        
        # Fetch issues
        console.print("[dim]Fetching issues from Jira...[/dim]")
        issues = self._fetch_not_ready_issues(self.top_items)
        
        if not issues:
            console.print("[yellow]No 'Not Ready' issues found in the backlog[/yellow]")
            return
        
        console.print(f"[green]Found {len(issues)} issue(s)[/green]\n")
        
        # Score issues
        console.print("[dim]Scoring issues against Definition of Ready...[/dim]")
        scored_issues = []
        
        for issue in track(issues, description="Analyzing..."):
            try:
                dor_result = self.checker.check_issue(issue)
                scored_issues.append({
                    'issue': issue,
                    'dor_result': dor_result
                })
            except Exception as e:
                console.print(f"[yellow]Warning: Could not score {issue['key']}: {str(e)}[/yellow]")
        
        # Keep Jira's Sprint/RANK order - don't re-sort by DoR score
        # This preserves the priority order from your board
        
        # Display results
        self._display_results(scored_issues)
        
        # Note: No interactive refinement - use agent-assisted mode instead
        console.print("\n[dim]💡 Tip: Use agent-assisted mode (with GitHub Copilot) to update issues[/dim]")
        console.print("[dim]   The agent can analyze quality and make updates via MCP tools[/dim]")
    
    def _fetch_not_ready_issues(self, max_results: int) -> List[Dict[str, Any]]:
        """
        Fetch top backlog issues in Not Ready status, ordered by Sprint then Rank
        
        Items are ordered by:
        1. **Sprint** - Items in active/upcoming sprints first
        2. **RANK** - Backlog priority order (board rank)
        
        This matches the order you see in your Jira board, excluding sub-tasks.
        
        Args:
            max_results: Maximum number of issues to fetch
            
        Returns:
            List of issue dictionaries
        """
        # ORDER BY Sprint ASC, RANK puts items IN sprints first (ASC puts non-null before null)
        # Then orders by RANK within each group
        # Also exclude Sub-tasks to match board view
        jql = (
            f'project = "{self.config["project"]["name"]}" '
            f'AND status = "{self.config["statuses"]["not_ready"]}" '
            f'AND type != Sub-task '
            f'ORDER BY Sprint ASC, RANK'
        )
        
        try:
            result = self.client.search_issues(
                jql=jql,
                max_results=self.top_items
            )
            return result.get('issues', [])
        except Exception as e:
            console.print(f"[red]Error fetching issues: {str(e)}[/red]")
            return []
    
    def _display_results(self, scored_issues: List[Dict]):
        """
        Display analysis results in a structured, agent-friendly format
        
        Args:
            scored_issues: List of scored issues
        """
        console.print("\n[bold blue]📋 Backlog Readiness Analysis[/bold blue]\n")
        
        # Define deterministic fields we care about
        # These map the checklist item names to display names
        deterministic_fields = {
            'Title completed': 'Title',
            'Story syntax completed (As a... I Want... So that...)': 'Story Syntax',
            'Acceptance Criteria in BDD/Gherkin syntax': 'Acceptance Criteria',
            'Account code set': 'Account',
            'Points estimated/assigned': 'Story Points'
        }
        
        for rank, item in enumerate(scored_issues, 1):
            dor = item['dor_result']
            issue = item['issue']
            
            # Get issue details
            summary = issue['fields'].get('summary', 'N/A')
            issue_type = issue['fields'].get('issuetype', {}).get('name', 'Unknown')
            
            # Get sprint info (customfield_10201)
            sprint_data = issue['fields'].get('customfield_10201')
            if sprint_data and len(sprint_data) > 0:
                sprint_name = sprint_data[0].get('name', 'Unknown')
            else:
                sprint_name = "Backlog"
            
            # Find missing deterministic fields
            missing = []
            for check in dor['checklist']:
                if not check['passed'] and not check.get('optional', False):
                    check_name = check.get('name', '')
                    if check_name in deterministic_fields:
                        missing.append(deterministic_fields[check_name])
            
            # Display issue
            score_color = "green" if dor['percentage'] >= 70 else "yellow" if dor['percentage'] >= 50 else "red"
            console.print(f"[bold cyan]#{rank} - {issue['key']}[/bold cyan] | [{score_color}]{dor['percentage']:.0f}% DoR[/{score_color}]")
            console.print(f"   Type: {issue_type} | Sprint: {sprint_name}")
            console.print(f"   Summary: {summary}")
            
            if missing:
                console.print(f"   [red]Missing (Deterministic): {', '.join(missing)}[/red]")
            else:
                console.print("   [green]✓ All deterministic fields complete[/green]")
            
            console.print("")  # Blank line between issues
        
        # Summary statistics
        avg_score = sum(item['dor_result']['percentage'] for item in scored_issues) / len(scored_issues)
        ready_count = sum(1 for item in scored_issues if item['dor_result']['percentage'] >= self.min_readiness)
        
        # Count items missing deterministic fields
        missing_deterministic = sum(
            1 for item in scored_issues 
            if any(
                not check['passed'] and not check.get('optional', False) 
                and check.get('name', '') in deterministic_fields
                for check in item['dor_result']['checklist']
            )
        )
        
        console.print("\n[bold]Summary:[/bold]")
        console.print(f"  • Average DoR score: {avg_score:.1f}%")
        console.print(f"  • Missing deterministic fields: {missing_deterministic}/{len(scored_issues)}")
        console.print(f"  • Ready for refinement (≥70%): {ready_count}/{len(scored_issues)}")
        
        console.print("\n[dim]Note: 'Missing' fields shown above are deterministic only:[/dim]")
        console.print("[dim]  Title, Story Syntax, Acceptance Criteria, Account, Story Points[/dim]")
        console.print("[dim]Other DoR criteria (security, telemetry, etc.) require agent review.[/dim]")


def main():
    """
    Main entry point for refinement prep CLI
    """
    try:
        prep = RefinementPrep()
        prep.run_analysis()
        return 0
    
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        return 1
    except Exception as e:
        console.print(f"[bold red]Error: {str(e)}[/bold red]")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
