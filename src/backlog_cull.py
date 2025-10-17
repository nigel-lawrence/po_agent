#!/usr/bin/env python3
"""
Backlog Cull - Identify old, stale issues that are candidates for removal

This tool helps Product Owners identify backlog items that are old with
no recent activity and low refinement levels - likely candidates for removal.
"""

import sys
import yaml
from datetime import datetime, timedelta
from typing import List, Dict
from dateutil import parser as date_parser
from rich.console import Console
from rich.progress import track
from jira_client import JiraClient
from dor_checker import DoRChecker

console = Console()


class BacklogCull:
    """
    Tool for identifying stale backlog items
    """

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize backlog cull tool
        
        Args:
            config_path: Path to configuration file
        """
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.client = JiraClient(config_path)
        self.checker = DoRChecker(config_path)
        self.project_key = self.config['project']['prefix']
        
        # Get thresholds from config
        cull_config = self.config['backlog_cull']
        self.age_threshold_days = cull_config['age_threshold_days']
        self.no_activity_days = cull_config['no_activity_days']
        self.min_refinement_score = cull_config['min_refinement_score']
    
    def run_analysis(
        self,
        age_threshold: int = None,
        activity_threshold: int = None,
        refinement_threshold: int = None
    ):
        """
        Run backlog cull analysis
        
        Args:
            age_threshold: Override age threshold in days
            activity_threshold: Override activity threshold in days
            refinement_threshold: Override refinement score threshold
        """
        # Use overrides if provided
        age_threshold = age_threshold or self.age_threshold_days
        activity_threshold = activity_threshold or self.no_activity_days
        refinement_threshold = refinement_threshold or self.min_refinement_score
        
        console.print("\n[bold blue]🗑️  Backlog Cull Analysis[/bold blue]")
        console.print("Identifying stale issues for potential removal\n")
        
        console.print("[bold]Thresholds:[/bold]")
        console.print(f"  • Issue age: > {age_threshold} days")
        console.print(f"  • No activity: > {activity_threshold} days")
        console.print(f"  • Refinement score: < {refinement_threshold}%\n")
        
        # Fetch old issues
        console.print("[dim]Fetching old backlog issues...[/dim]")
        issues = self._fetch_old_issues(age_threshold)
        
        if not issues:
            console.print("[green]No stale issues found! Backlog is in good shape.[/green]")
            return
        
        console.print(f"[yellow]Found {len(issues)} old issue(s)[/yellow]\n")
        
        # Analyze issues
        console.print("[dim]Analyzing issues...[/dim]")
        candidates = []
        
        for issue in track(issues, description="Processing..."):
            try:
                analysis = self._analyze_issue(
                    issue,
                    activity_threshold,
                    refinement_threshold
                )
                
                if analysis['is_candidate']:
                    candidates.append(analysis)
            
            except Exception as e:
                console.print(f"[yellow]Warning: Could not analyze {issue['key']}: {str(e)}[/yellow]")
        
        # Sort by staleness score (most stale first)
        candidates.sort(key=lambda x: x['staleness_score'], reverse=True)
        
        # Display results
        if candidates:
            self._display_results(candidates)
        else:
            console.print("[green]No issues meet the cull criteria![/green]")
            console.print("Your backlog is well-maintained. 🎉")
        
        # Note: No interactive actions - use agent-assisted mode for updates
        console.print("\n[dim]💡 Tip: Use agent-assisted mode (with GitHub Copilot) to review and act on these issues[/dim]")
        console.print("[dim]   The agent can help you decide what to keep, update, or close[/dim]")
    
    def _fetch_old_issues(self, age_threshold_days: int) -> List[Dict]:
        """
        Fetch issues older than threshold
        
        Args:
            age_threshold_days: Age threshold in days
            
        Returns:
            List of issue data
        """
        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=age_threshold_days)
        cutoff_str = cutoff_date.strftime('%Y-%m-%d')
        
        # JQL to get old unresolved issues
        jql = (
            f'project = {self.project_key} '
            f'AND resolution IS EMPTY '
            f'AND created < "{cutoff_str}" '
            f'ORDER BY created ASC'
        )
        
        try:
            result = self.client.search_issues(
                jql=jql,
                max_results=100  # Adjust if needed
            )
            return result.get('issues', [])
        except Exception as e:
            console.print(f"[red]Error fetching issues: {str(e)}[/red]")
            return []
    
    def _analyze_issue(
        self,
        issue: Dict,
        activity_threshold: int,
        refinement_threshold: int
    ) -> Dict:
        """
        Analyze a single issue for cull candidacy
        
        Args:
            issue: Issue data
            activity_threshold: Activity threshold in days
            refinement_threshold: Refinement score threshold
            
        Returns:
            Analysis result dictionary
        """
        fields = issue['fields']
        issue_key = issue['key']
        
        # Get dates
        created = date_parser.parse(fields['created'])
        updated = date_parser.parse(fields['updated'])
        now = datetime.now(created.tzinfo)
        
        age_days = (now - created).days
        days_since_update = (now - updated).days
        
        # Get DoR score
        dor_result = self.checker.check_issue(issue)
        refinement_score = dor_result['percentage']
        
        # Calculate staleness score (0-100, higher = more stale)
        # Factors: age, inactivity, low refinement
        age_factor = min(age_days / 365, 1.0) * 40  # Max 40 points for age
        inactivity_factor = min(days_since_update / 180, 1.0) * 40  # Max 40 points for inactivity
        refinement_factor = (100 - refinement_score) / 100 * 20  # Max 20 points for poor refinement
        
        staleness_score = age_factor + inactivity_factor + refinement_factor
        
        # Determine if candidate
        is_candidate = (
            days_since_update >= activity_threshold and
            refinement_score < refinement_threshold
        )
        
        # Get additional context
        priority = fields.get('priority', {}).get('name', 'Unknown')
        issue_type = fields.get('issuetype', {}).get('name', 'Unknown')
        status = fields.get('status', {}).get('name', 'Unknown')
        assignee = fields.get('assignee')
        assignee_name = assignee['displayName'] if assignee else 'Unassigned'
        
        # Count comments and watchers as engagement indicators
        comments = fields.get('comment', {}).get('total', 0)
        watchers = fields.get('watches', {}).get('watchCount', 0)
        
        return {
            'issue_key': issue_key,
            'summary': fields.get('summary', 'N/A'),
            'age_days': age_days,
            'days_since_update': days_since_update,
            'refinement_score': refinement_score,
            'staleness_score': round(staleness_score, 1),
            'is_candidate': is_candidate,
            'priority': priority,
            'issue_type': issue_type,
            'status': status,
            'assignee': assignee_name,
            'comments': comments,
            'watchers': watchers,
            'created': created.strftime('%Y-%m-%d'),
            'updated': updated.strftime('%Y-%m-%d'),
        }
    
    def _display_results(self, candidates: List[Dict]):
        """
        Display cull candidates in an AI-friendly format
        
        Args:
            candidates: List of candidate analyses
        """
        console.print(f"\n[bold]📋 Found {len(candidates)} Stale Backlog Items[/bold]\n")
        
        # Display each issue with full details (no truncation)
        for i, candidate in enumerate(candidates, 1):
            # Color code staleness
            staleness = candidate['staleness_score']
            if staleness >= 80:
                staleness_color = "red"
                staleness_label = "VERY STALE"
            elif staleness >= 60:
                staleness_color = "yellow"
                staleness_label = "STALE"
            else:
                staleness_color = "white"
                staleness_label = "Moderately Stale"
            
            # Build Jira URL
            base_url = self.client.jira_url.rstrip('/')
            issue_url = f"{base_url}/browse/{candidate['issue_key']}"
            
            console.print(f"[bold cyan]#{i} - {candidate['issue_key']}[/bold cyan] ({candidate['issue_type']})")
            console.print(f"[dim]{issue_url}[/dim]")
            console.print(f"[bold]{candidate['summary']}[/bold]")
            console.print("")
            console.print(f"  [bold]Staleness:[/bold] [{staleness_color}]{staleness:.0f}/100 ({staleness_label})[/{staleness_color}]")
            console.print(f"  • Age: {candidate['age_days']} days (created {candidate['created']})")
            console.print(f"  • Last updated: {candidate['days_since_update']} days ago ({candidate['updated']})")
            console.print(f"  • DoR Score: {candidate['refinement_score']:.0f}%")
            console.print(f"  • Status: {candidate['status']}")
            console.print(f"  • Priority: {candidate['priority']}")
            console.print(f"  • Assignee: {candidate['assignee']}")
            console.print(f"  • Comments: {candidate['comments']}")
            console.print(f"  • Watchers: {candidate['watchers']}")
            console.print("")
        
        # Summary statistics
        avg_age = sum(c['age_days'] for c in candidates) / len(candidates)
        avg_staleness = sum(c['staleness_score'] for c in candidates) / len(candidates)
        unassigned = sum(1 for c in candidates if c['assignee'] == 'Unassigned')
        
        console.print("\n[bold]Summary:[/bold]")
        console.print(f"  • Total candidates: {len(candidates)}")
        console.print(f"  • Average age: {avg_age:.0f} days")
        console.print(f"  • Average staleness: {avg_staleness:.0f}/100")
        console.print(f"  • Unassigned: {unassigned}")


def main():
    """
    Main entry point for backlog cull CLI
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Identify stale backlog issues for potential removal"
    )
    parser.add_argument(
        '--age',
        type=int,
        help='Age threshold in days (default: 180)'
    )
    parser.add_argument(
        '--activity',
        type=int,
        help='No activity threshold in days (default: 90)'
    )
    parser.add_argument(
        '--refinement',
        type=int,
        help='Minimum refinement score percentage (default: 30)'
    )
    
    args = parser.parse_args()
    
    try:
        cull = BacklogCull()
        cull.run_analysis(
            age_threshold=args.age,
            activity_threshold=args.activity,
            refinement_threshold=args.refinement
        )
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
