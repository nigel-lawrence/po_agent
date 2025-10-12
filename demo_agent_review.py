#!/usr/bin/env python3
"""
Demo: Agent-Assisted DoR Review

This demonstrates how an AI agent (like GitHub Copilot) can use the hybrid
DoR checker to provide quality assessments of free-text fields.
"""

from src.jira_client import JiraClient
from src.dor_checker import DoRChecker
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()


def demo_agent_review(issue_key: str):
    """
    Demonstrate agent-assisted review for a specific issue
    
    Args:
        issue_key: Jira issue key (e.g., "DD-1130")
    """
    console.print(f"\n[bold cyan]🤖 Agent-Assisted DoR Review Demo[/bold cyan]")
    console.print(f"[dim]Issue: {issue_key}[/dim]\n")
    
    # Initialize clients
    client = JiraClient()
    checker = DoRChecker()
    
    # Get the issue
    console.print("[dim]Fetching issue...[/dim]")
    result = client.search_issues(f'key = {issue_key}', max_results=1)
    if not result.get('issues'):
        console.print(f"[red]Issue {issue_key} not found[/red]")
        return
    
    issue = result['issues'][0]
    
    # Step 1: Deterministic scoring
    console.print("\n[bold]Step 1: Deterministic Checks[/bold]")
    dor_result = checker.check_issue(issue)
    
    console.print(f"Score: {dor_result['score']}/{dor_result['max_score']} ({dor_result['percentage']}%)")
    console.print(f"\nPassed checks:")
    for item in dor_result['checklist']:
        if item['passed']:
            console.print(f"  ✅ {item['name']}")
    
    console.print(f"\nFailed checks (need attention):")
    for item in dor_result['checklist']:
        if not item['passed'] and not item.get('optional'):
            console.print(f"  ❌ {item['name']}: {item['details']}")
    
    # Step 2: Get content for LLM review
    console.print("\n[bold]Step 2: Content for Agent Quality Review[/bold]")
    llm_reviews = checker.get_content_for_llm_review(issue)
    
    console.print(f"Found {len(llm_reviews)} fields that need quality assessment\n")
    
    # Step 3: Simulate agent evaluation
    console.print("[bold]Step 3: Agent Evaluation (Simulated)[/bold]")
    console.print("[dim]In production, an LLM would evaluate each field for quality.[/dim]\n")
    
    # Example: Show first 2 reviews
    for idx, review in enumerate(llm_reviews[:2], 1):
        console.print(Panel(
            f"[bold]Criterion:[/bold] {review['criterion']}\n\n"
            f"[bold]Content:[/bold]\n{review['content'][:200]}...\n\n"
            f"[bold]Evaluation Prompt:[/bold]\n{review['prompt']}\n\n"
            f"[bold yellow]→ Agent would evaluate this and return: PASS/FAIL + reasoning[/bold yellow]",
            title=f"[cyan]Review {idx}[/cyan]",
            border_style="yellow"
        ))
    
    # Step 4: Show potential enhanced score
    console.print("\n[bold]Step 4: Enhanced Score (with Agent Evaluation)[/bold]")
    console.print("[dim]After agent review, the score could be adjusted based on quality:[/dim]\n")
    
    console.print(f"• Deterministic score: {dor_result['percentage']:.0f}%")
    console.print(f"• With agent evaluation: [yellow]Would increase if quality is good[/yellow]")
    console.print(f"• Example: If agent finds story syntax and acceptance criteria are high quality,")
    console.print(f"  score could increase by up to {2+2}/{dor_result['max_score']} points (4 more points)")
    
    # Summary
    console.print("\n[bold green]Summary: Hybrid Approach Benefits[/bold green]")
    benefits = """
    ✅ **Fast deterministic checks** - Instant feedback on structured fields
    ✅ **Quality assessment** - Agent evaluates meaning, not just presence
    ✅ **Reduces false positives** - Won't pass template/boilerplate text
    ✅ **Actionable feedback** - Agent can explain what's missing or poor quality
    ✅ **Scalable** - Deterministic checks work offline, agent used when needed
    """
    console.print(Markdown(benefits))
    
    # Usage pattern
    console.print("\n[bold]How to use in production:[/bold]")
    console.print("""
    1. Run refinement_prep.py - shows deterministic scores
    2. Select an issue to review
    3. Choose option 1: "View content for agent/LLM review"
    4. Agent (GitHub Copilot) evaluates each field
    5. Agent provides pass/fail + recommendations
    6. PO updates issue based on feedback
    """)


if __name__ == "__main__":
    import sys
    
    # Demo with DD-1130
    issue_key = sys.argv[1] if len(sys.argv) > 1 else "DD-1130"
    
    try:
        demo_agent_review(issue_key)
    except Exception as e:
        console.print(f"[bold red]Error: {str(e)}[/bold red]")
        import traceback
        traceback.print_exc()
