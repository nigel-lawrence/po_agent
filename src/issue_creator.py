#!/usr/bin/env python3
"""
Issue Creator - Interactive CLI tool for creating well-structured Jira issues

This tool helps Product Owners create issues that are as complete as possible
for refinement sessions, including story syntax, BDD acceptance criteria,
and considerations for cost and telemetry.
"""

import sys
import yaml
from typing import Dict, Optional
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.markdown import Markdown
from jira_client import JiraClient
from dor_checker import DoRChecker

console = Console()


class IssueCreator:
    """
    Interactive issue creator with guided prompts
    """

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the issue creator
        
        Args:
            config_path: Path to configuration file
        """
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.client = JiraClient(config_path)
        self.checker = DoRChecker(config_path)
        self.project_key = self.config['project']['prefix']
    
    def create_issue_interactive(self):
        """
        Run interactive issue creation workflow
        """
        console.print("\n[bold blue]🎯 Jira Issue Creator[/bold blue]")
        console.print("Let's create a well-structured issue for refinement!\n")
        
        # Get issue type
        issue_type = self._select_issue_type()
        
        # Get basic info
        summary = Prompt.ask("[bold]Issue Title/Summary[/bold]")
        
        # Get epic link (optional)
        epic_key = None
        if Confirm.ask("Would you like to link this to an epic?", default=False):
            epic_key = Prompt.ask("Epic key (e.g., DD-100)")
        
        # Get story syntax for stories
        story_syntax = None
        if issue_type.lower() == 'story':
            console.print("\n[bold cyan]📝 Story Syntax[/bold cyan]")
            console.print("Let's create the user story in 'As a... I want... So that...' format\n")
            
            user_type = Prompt.ask("As a [user type]", default="user")
            capability = Prompt.ask("I want [what capability/feature]")
            value = Prompt.ask("So that [what business value/outcome]")
            
            story_syntax = self._format_story_syntax(user_type, capability, value)
            
            console.print("\n[green]✓ Story syntax:[/green]")
            console.print(Panel(story_syntax, border_style="green"))
        
        # Get acceptance criteria
        console.print("\n[bold cyan]✅ Acceptance Criteria[/bold cyan]")
        console.print("Let's define acceptance criteria in BDD/Gherkin format\n")
        
        acceptance_criteria = self._gather_acceptance_criteria()
        
        console.print("\n[green]✓ Acceptance criteria:[/green]")
        console.print(Panel(acceptance_criteria, border_style="green"))
        
        # Get description with considerations
        console.print("\n[bold cyan]📄 Description & Considerations[/bold cyan]")
        description = self._gather_description()
        
        # Get environments
        console.print("\n[bold cyan]🌍 Environments[/bold cyan]")
        environments = self._gather_environments()
        
        # Combine description with environments
        full_description = self._build_full_description(
            description, 
            environments,
            issue_type
        )
        
        # Build issue data
        issue_data = self._build_issue_data(
            issue_type=issue_type,
            summary=summary,
            description=full_description,
            story_syntax=story_syntax,
            acceptance_criteria=acceptance_criteria,
            epic_key=epic_key
        )
        
        # Show preview
        console.print("\n[bold]📋 Issue Preview:[/bold]")
        self._display_preview(issue_data, issue_type)
        
        # Confirm creation
        if not Confirm.ask("\nCreate this issue?", default=True):
            console.print("[yellow]Issue creation cancelled[/yellow]")
            return None
        
        # Create the issue
        try:
            console.print("\n[bold]Creating issue...[/bold]")
            result = self.client.create_issue(issue_data)
            issue_key = result['key']
            
            console.print(f"\n[bold green]✓ Issue created successfully: {issue_key}[/bold green]")
            console.print(f"View at: {self.client.jira_url}/browse/{issue_key}")
            
            # Check DoR score
            if Confirm.ask("\nWould you like to check the Definition of Ready score?", default=True):
                self._check_dor_score(issue_key)
            
            return issue_key
            
        except Exception as e:
            console.print(f"[bold red]✗ Error creating issue: {str(e)}[/bold red]")
            return None
    
    def _select_issue_type(self) -> str:
        """
        Prompt user to select issue type
        
        Returns:
            Selected issue type name
        """
        issue_types = self.config['issue_types']
        
        console.print("[bold]Select Issue Type:[/bold]")
        type_list = list(issue_types.keys())
        
        for i, type_name in enumerate(type_list, 1):
            console.print(f"  {i}. {type_name.title()}")
        
        choice = Prompt.ask(
            "Enter number",
            choices=[str(i) for i in range(1, len(type_list) + 1)],
            default="1"
        )
        
        return type_list[int(choice) - 1]
    
    def _format_story_syntax(self, user_type: str, capability: str, value: str) -> str:
        """
        Format the story syntax in ADF (Atlassian Document Format)
        
        Args:
            user_type: Type of user
            capability: Capability or feature
            value: Business value or outcome
            
        Returns:
            Formatted story syntax
        """
        return (
            f"As a {user_type}\n"
            f"I want {capability}\n"
            f"So that {value}"
        )
    
    def _gather_acceptance_criteria(self) -> str:
        """
        Gather acceptance criteria in BDD/Gherkin format
        
        Returns:
            Formatted acceptance criteria
        """
        feature_name = Prompt.ask("Feature name")
        
        scenarios = []
        scenario_count = 1
        
        while True:
            console.print(f"\n[bold]Scenario {scenario_count}:[/bold]")
            scenario_name = Prompt.ask("Scenario name")
            given = Prompt.ask("Given (precondition)")
            when = Prompt.ask("When (action)")
            then = Prompt.ask("Then (expected outcome)")
            
            scenarios.append({
                'name': scenario_name,
                'given': given,
                'when': when,
                'then': then
            })
            
            if not Confirm.ask("Add another scenario?", default=False):
                break
            
            scenario_count += 1
        
        # Format as Gherkin
        ac = f"Feature: {feature_name}\n\n"
        for scenario in scenarios:
            ac += f"Scenario: {scenario['name']}\n"
            ac += f"  Given {scenario['given']}\n"
            ac += f"  When {scenario['when']}\n"
            ac += f"  Then {scenario['then']}\n\n"
        
        return ac.strip()
    
    def _gather_description(self) -> str:
        """
        Gather issue description
        
        Returns:
            Description text
        """
        console.print("Enter the issue description (press Enter twice when done):")
        lines = []
        empty_count = 0
        
        while empty_count < 2:
            line = input()
            if not line:
                empty_count += 1
            else:
                empty_count = 0
            lines.append(line)
        
        # Remove trailing empty lines
        while lines and not lines[-1]:
            lines.pop()
        
        return '\n'.join(lines)
    
    def _gather_environments(self) -> Dict[str, bool]:
        """
        Gather environment deployment information
        
        Returns:
            Dictionary of environments
        """
        console.print("Which environments will this be deployed to?")
        
        environments = {
            'staging': Confirm.ask("Staging", default=True),
            'pre-production': Confirm.ask("Pre-production", default=True),
            'production': Confirm.ask("Production", default=True)
        }
        
        return environments
    
    def _build_full_description(
        self, 
        description: str, 
        environments: Dict[str, bool],
        issue_type: str
    ) -> str:
        """
        Build full description with all considerations
        
        Args:
            description: Main description
            environments: Environment information
            issue_type: Type of issue
            
        Returns:
            Complete description
        """
        parts = [description, "\n"]
        
        # Add environments
        parts.append("\n## Environments")
        env_list = [env.title() for env, enabled in environments.items() if enabled]
        if env_list:
            parts.append(f"This will be deployed to: {', '.join(env_list)}")
        else:
            parts.append("Environments to be determined")
        
        # Add consideration sections
        parts.append("\n## Security Considerations")
        if Confirm.ask("\nAdd security considerations now?", default=False):
            security = Prompt.ask("Describe security implications/risks")
            parts.append(security)
        else:
            parts.append("_To be defined during refinement_")
        
        parts.append("\n## Cost Implications")
        if Confirm.ask("Add cost considerations now?", default=False):
            cost = Prompt.ask("Describe cost implications")
            parts.append(cost)
        else:
            parts.append("_To be defined during refinement_")
        
        parts.append("\n## Telemetry & Monitoring")
        if Confirm.ask("Add telemetry considerations now?", default=False):
            telemetry = Prompt.ask("Describe metrics, alerts, and monitoring")
            parts.append(telemetry)
        else:
            parts.append("_To be defined during refinement_")
        
        parts.append("\n## Documentation")
        if Confirm.ask("Link to relevant documentation?", default=False):
            docs = Prompt.ask("Documentation links or references")
            parts.append(docs)
        else:
            parts.append("_To be identified during refinement_")
        
        parts.append("\n## What to Demo")
        if Confirm.ask("Define demo scope now?", default=False):
            demo = Prompt.ask("What should be demonstrated")
            parts.append(demo)
        else:
            parts.append("_To be defined during refinement_")
        
        return '\n'.join(parts)
    
    def _build_issue_data(
        self,
        issue_type: str,
        summary: str,
        description: str,
        story_syntax: Optional[str] = None,
        acceptance_criteria: Optional[str] = None,
        epic_key: Optional[str] = None
    ) -> Dict:
        """
        Build Jira issue creation data structure
        
        Args:
            issue_type: Type of issue
            summary: Issue summary
            description: Issue description
            story_syntax: Story syntax (for stories)
            acceptance_criteria: Acceptance criteria
            epic_key: Parent epic key
            
        Returns:
            Issue data dictionary for Jira API
        """
        issue_type_id = self.config['issue_types'][issue_type.lower()]
        
        # Build fields
        fields = {
            'project': {'key': self.project_key},
            'issuetype': {'id': issue_type_id},
            'summary': summary,
            'description': self._text_to_adf(description)
        }
        
        # Add story syntax if applicable
        if story_syntax:
            fields[self.config['custom_fields']['story_syntax']] = self._text_to_adf(story_syntax)
        
        # Add acceptance criteria
        if acceptance_criteria:
            fields[self.config['custom_fields']['acceptance_criteria']] = self._text_to_adf(acceptance_criteria)
        
        # Add parent epic
        if epic_key:
            fields['parent'] = {'key': epic_key}
        
        return {'fields': fields}
    
    def _text_to_adf(self, text: str) -> Dict:
        """
        Convert plain text to ADF (Atlassian Document Format)
        
        Args:
            text: Plain text
            
        Returns:
            ADF document structure
        """
        # Split text into paragraphs
        paragraphs = text.split('\n')
        
        content = []
        for para in paragraphs:
            if para.strip():
                # Check if it's a heading
                if para.startswith('##'):
                    heading_text = para.lstrip('#').strip()
                    content.append({
                        'type': 'heading',
                        'attrs': {'level': 2},
                        'content': [{'type': 'text', 'text': heading_text}]
                    })
                else:
                    content.append({
                        'type': 'paragraph',
                        'content': [{'type': 'text', 'text': para}]
                    })
            else:
                # Empty paragraph for spacing
                content.append({'type': 'paragraph', 'content': []})
        
        return {
            'type': 'doc',
            'version': 1,
            'content': content
        }
    
    def _display_preview(self, issue_data: Dict, issue_type: str):
        """
        Display a preview of the issue to be created
        
        Args:
            issue_data: Issue data structure
            issue_type: Type of issue
        """
        fields = issue_data['fields']
        
        console.print(f"[bold]Type:[/bold] {issue_type.title()}")
        console.print(f"[bold]Project:[/bold] {self.project_key}")
        console.print(f"[bold]Summary:[/bold] {fields['summary']}")
        
        if 'parent' in fields:
            console.print(f"[bold]Epic:[/bold] {fields['parent']['key']}")
    
    def _check_dor_score(self, issue_key: str):
        """
        Check and display Definition of Ready score
        
        Args:
            issue_key: Issue key to check
        """
        try:
            issue_data = self.client.get_issue(issue_key)
            result = self.checker.check_issue(issue_data)
            
            console.print(f"\n[bold]Definition of Ready Score:[/bold]")
            console.print(f"Score: {result['score']}/{result['max_score']} ({result['percentage']}%)")
            console.print(f"Level: {self.checker.get_readiness_level(result['percentage'])}")
            
            if result['percentage'] < 100:
                console.print("\n[yellow]Recommendations for improvement:[/yellow]")
                for rec in result['recommendations'][:5]:
                    console.print(f"  {rec}")
        
        except Exception as e:
            console.print(f"[yellow]Could not check DoR score: {str(e)}[/yellow]")


def main():
    """
    Main entry point for the issue creator CLI
    """
    try:
        creator = IssueCreator()
        issue_key = creator.create_issue_interactive()
        
        if issue_key:
            return 0
        else:
            return 1
    
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        return 1
    except Exception as e:
        console.print(f"[bold red]Error: {str(e)}[/bold red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
