import requests
import datetime
import os
import argparse
from dotenv import load_dotenv
from collections import defaultdict
from jira_client import JiraClient

# Load environment variables from .env file
load_dotenv()

# --- CONFIG ---
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")
TEMPO_API_TOKEN = os.getenv("TEMPO_API_TOKEN")
TEMPO_TEAM_NAME = os.getenv("TEMPO_TEAM_NAME")

# Initialize Jira client
jira_client = JiraClient()

# --- PARSE ARGUMENTS ---
def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Check Tempo timesheet submissions and breakdown for a specific week.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Check last week (default)
  python tempo_chaser.py
  
  # Check the week before last (2 weeks ago)
  python tempo_chaser.py --weeks-ago 2
  
  # Check 3 weeks ago
  python tempo_chaser.py --weeks-ago 3
        '''
    )
    parser.add_argument(
        '--weeks-ago',
        type=int,
        default=1,
        help='Number of weeks ago to check (default: 1 = last week)'
    )
    return parser.parse_args()

# Parse command-line arguments
args = parse_arguments()

# --- DATE CALC ---
today = datetime.date.today()
# Calculate the start of the target week based on weeks_ago parameter
# weeks_ago=1 means last week, weeks_ago=2 means week before last, etc.
last_week_start = today - datetime.timedelta(days=today.weekday() + (7 * args.weeks_ago))
last_week_end = last_week_start + datetime.timedelta(days=6)

# --- GET TEAM ID FROM NAME ---
def get_team_id_by_name(team_name):
    """Get Tempo team ID by team name."""
    url = "https://api.tempo.io/4/teams"
    headers = {"Authorization": f"Bearer {TEMPO_API_TOKEN}"}
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Error fetching teams: {response.status_code}")
        return None
    
    teams_data = response.json()
    team = next((t for t in teams_data.get('results', []) if t['name'] == team_name), None)
    
    if team:
        return team['id']
    else:
        print(f"Team '{team_name}' not found")
        return None

# --- GET TEAM MEMBERS ---
def get_team_members(team_id):
    """Get member details (account ID, email, name) for all members in a Tempo team."""
    url = f"https://api.tempo.io/4/teams/{team_id}/members"
    headers = {"Authorization": f"Bearer {TEMPO_API_TOKEN}"}
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Error fetching team members: {response.status_code}")
        return []
    
    members_data = response.json()
    
    # Get user details from Jira using JiraClient
    team_members = []
    
    for member in members_data.get('results', []):
        account_id = member.get('member', {}).get('accountId')
        
        if account_id:
            try:
                user_data = jira_client.get_user_by_account_id(account_id)
                email = user_data.get('emailAddress', '').lower()
                name = user_data.get('displayName', 'Unknown')
                if email:
                    team_members.append({
                        'accountId': account_id,
                        'email': email,
                        'name': name
                    })
            except Exception as e:
                print(f"Warning: Could not fetch user details for account {account_id}: {e}")
    
    return team_members

# --- GET TIMESHEET STATUS ---
def get_submission_status(team_members):
    """Check which team members have submitted and which haven't."""
    headers = {"Authorization": f"Bearer {TEMPO_API_TOKEN}"}
    missing_members = []
    submitted_members = []
    
    for member in team_members:
        # Check timesheet approval status
        url = f"https://api.tempo.io/4/timesheet-approvals/user/{member['accountId']}"
        params = {
            "from": last_week_start.isoformat(),
            "to": last_week_end.isoformat()
        }
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            status = data.get('status', {}).get('key', 'UNKNOWN')
            
            # OPEN means not submitted
            # IN_REVIEW or APPROVED means submitted
            if status == 'OPEN':
                missing_members.append(member)
            elif status in ['IN_REVIEW', 'APPROVED']:
                submitted_members.append(member)
        else:
            print(f"Warning: Could not check status for {member['name']}: {response.status_code}")
    
    return missing_members, submitted_members

# --- GET WORKLOGS FOR USER ---
def get_user_worklogs(account_id):
    """Get all worklogs for a specific user in the date range."""
    headers = {"Authorization": f"Bearer {TEMPO_API_TOKEN}"}
    url = f"https://api.tempo.io/4/worklogs/user/{account_id}"
    
    params = {
        "from": last_week_start.isoformat(),
        "to": last_week_end.isoformat()
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json().get('results', [])
    else:
        return []

# --- GET JIRA ISSUE DETAILS ---
def get_jira_issue_details(issue_id):
    """Get Jira issue details including key, summary and account."""
    try:
        return jira_client.get_issue_with_account(issue_id)
    except Exception as e:
        print(f"Warning: Could not fetch issue details for {issue_id}: {e}")
        return {
            'key': 'UNKNOWN',
            'summary': 'Unable to fetch',
            'account': 'N/A'
        }

# --- PROCESS WORKLOGS ---
def process_worklogs(worklogs):
    """Process worklogs and group by Jira issue."""
    issues_data = defaultdict(lambda: {
        'timeSpentSeconds': 0,
        'issue_id': '',
        'issue_key': '',
        'summary': '',
        'account': ''
    })
    
    total_time_seconds = 0
    
    for worklog in worklogs:
        issue_id = worklog.get('issue', {}).get('id', 'UNKNOWN')
        time_spent = worklog.get('timeSpentSeconds', 0)
        
        issues_data[issue_id]['timeSpentSeconds'] += time_spent
        issues_data[issue_id]['issue_id'] = issue_id
        total_time_seconds += time_spent
    
    # Fetch Jira details for each issue
    for issue_id in issues_data.keys():
        if issue_id != 'UNKNOWN':
            details = get_jira_issue_details(issue_id)
            issues_data[issue_id]['issue_key'] = details['key']
            issues_data[issue_id]['summary'] = details['summary']
            issues_data[issue_id]['account'] = details['account']
    
    return dict(issues_data), total_time_seconds

# --- FORMAT TIME ---
def format_time(seconds):
    """Convert seconds to hours and minutes."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours}h {minutes}m"

# --- MAIN ---
if __name__ == "__main__":
    print("=" * 100)
    print("TEMPO TIMESHEET CHECKER & BREAKDOWN REPORT")
    print("=" * 100)
    
    # Show which week we're checking
    weeks_ago_text = "Last week" if args.weeks_ago == 1 else f"{args.weeks_ago} weeks ago"
    print(f"Checking: {weeks_ago_text}")
    print(f"Week: {last_week_start.strftime('%B %d, %Y')} to {last_week_end.strftime('%B %d, %Y')}")
    print("=" * 100)
    print()
    
    # Get team ID from name
    print(f"Looking up team '{TEMPO_TEAM_NAME}'...")
    team_id = get_team_id_by_name(TEMPO_TEAM_NAME)
    if not team_id:
        print(f"✗ Error: Could not find team '{TEMPO_TEAM_NAME}'")
        exit(1)
    
    print(f"✓ Found team '{TEMPO_TEAM_NAME}' (ID: {team_id})")
    
    # Get team members
    print(f"Fetching team members...")
    team_members = get_team_members(team_id)
    if not team_members:
        print("✗ Error: No team members found")
        exit(1)
    
    print(f"✓ Found {len(team_members)} team members")
    
    # Check for submission status
    print(f"Checking timesheet submission status...")
    missing_users, submitted_users = get_submission_status(team_members)
    
    print(f"✓ Status check complete")
    print()
    
    # =========================================================================
    # PART 1: MISSING SUBMISSIONS
    # =========================================================================
    print("=" * 100)
    print("PART 1: SUBMISSION STATUS")
    print("=" * 100)
    print()
    
    submitted_count = len(submitted_users)
    total_count = len(team_members)
    print(f"📊 Submission Status: {submitted_count}/{total_count} team members have submitted")
    print()
    
    if missing_users:
        print(f"⚠️  {len(missing_users)} team member(s) need to submit timesheets:\n")
        
        for user in missing_users:
            print(f"   ❌ {user['name']}")
            print(f"      Email: {user['email']}")
            print()
        
        print("=" * 100)
        print("💡 Action Required:")
        print("   1. Contact the team members listed above")
        print("   2. Remind them to submit their timesheets")
        print("=" * 100)
        print()
    else:
        print("✅ All team members have submitted their timesheets!\n")
        print("=" * 100)
        print()
    
    # =========================================================================
    # PART 2: TIME BREAKDOWN FOR SUBMITTED TIMESHEETS
    # =========================================================================
    if submitted_users:
        print()
        print("=" * 100)
        print("PART 2: TIME BREAKDOWN BY JIRA CARD (SUBMITTED TIMESHEETS)")
        print("=" * 100)
        print()
        
        # Track statistics for missing account codes
        total_cards_missing_account = 0
        members_with_missing_accounts = []
        
        # Process each submitted member
        for idx, member in enumerate(submitted_users, 1):
            print("=" * 100)
            print(f"👤 {member['name']} ({member['email']})")
            print("=" * 100)
            
            # Get worklogs
            worklogs = get_user_worklogs(member['accountId'])
            
            if not worklogs:
                print("   No worklogs found for this user.\n")
                continue
            
            # Process worklogs
            issues_data, total_time = process_worklogs(worklogs)
            
            if total_time == 0:
                print("   No time logged for this week.\n")
                continue
            
            print(f"\n📊 Total Time Logged: {format_time(total_time)}")
            print()
            
            # Sort issues by time spent (descending)
            sorted_issues = sorted(issues_data.items(), 
                                  key=lambda x: x[1]['timeSpentSeconds'], 
                                  reverse=True)
            
            # Count missing accounts for this user
            missing_accounts_for_user = []
            
            # Display each issue
            for issue_id, data in sorted_issues:
                time_seconds = data['timeSpentSeconds']
                time_formatted = format_time(time_seconds)
                percentage = (time_seconds / total_time) * 100 if total_time > 0 else 0
                issue_key = data['issue_key']
                account = data['account']
                
                # Highlight missing account codes
                if account == 'N/A' or not account:
                    account_display = "⚠️  MISSING - ACTION REQUIRED ⚠️"
                    missing_accounts_for_user.append(issue_key)
                else:
                    account_display = account
                
                print(f"   🔗 {issue_key}")
                print(f"      Link: {JIRA_BASE_URL}/browse/{issue_key}")
                print(f"      Title: {data['summary']}")
                print(f"      Account: {account_display}")
                print(f"      Time: {time_formatted} ({percentage:.1f}% of week)")
                print()
            
            # Track missing accounts
            if missing_accounts_for_user:
                total_cards_missing_account += len(missing_accounts_for_user)
                members_with_missing_accounts.append({
                    'name': member['name'],
                    'cards': missing_accounts_for_user
                })
            
            if idx < len(submitted_users):
                print()
        
        # =====================================================================
        # PART 3: MISSING ACCOUNT CODES SUMMARY
        # =====================================================================
        print()
        print("=" * 100)
        print("PART 3: ACCOUNT CODE STATUS")
        print("=" * 100)
        
        if total_cards_missing_account > 0:
            print()
            print("⚠️  ACTION REQUIRED - MISSING ACCOUNT CODES")
            print("=" * 100)
            print(f"\n{total_cards_missing_account} Jira card(s) are missing account codes:\n")
            
            for member_info in members_with_missing_accounts:
                print(f"👤 {member_info['name']}:")
                for card in member_info['cards']:
                    print(f"   • {card} - {JIRA_BASE_URL}/browse/{card}")
                print()
            
            print("=" * 100)
            print("💡 Please update the 'Account' field in Jira for the cards listed above.")
            print("=" * 100)
        else:
            print()
            print("✅ All cards have account codes assigned!")
            print("=" * 100)
    
    # =========================================================================
    # FINAL SUMMARY
    # =========================================================================
    print()
    print("=" * 100)
    print("END OF REPORT")
    print("=" * 100)

