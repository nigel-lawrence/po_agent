"""
Jira Client - Handles authentication and API interactions with Jira
"""

import os
import requests
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
import yaml
import json

# Load environment variables
load_dotenv()


class JiraClient:
    """
    Client for interacting with Jira REST API
    """

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize Jira client with configuration
        
        Args:
            config_path: Path to the YAML configuration file
        """
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Get credentials from environment
        self.jira_url = os.getenv('JIRA_URL')
        self.jira_email = os.getenv('JIRA_EMAIL')
        self.jira_api_token = os.getenv('JIRA_API_TOKEN')
        
        if not all([self.jira_url, self.jira_email, self.jira_api_token]):
            raise ValueError(
                "Missing Jira credentials. Please set JIRA_URL, JIRA_EMAIL, "
                "and JIRA_API_TOKEN in your .env file"
            )
        
        # Set up session with authentication
        self.session = requests.Session()
        self.session.auth = (self.jira_email, self.jira_api_token)
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        self.cloud_id = self.config['project']['cloud_id']
        self.api_base = f"https://api.atlassian.com/ex/jira/{self.cloud_id}/rest/api/3"
        self.project_key = self.config['project']['prefix']
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Dict:
        """
        Make an authenticated request to Jira API
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (without base URL)
            params: Query parameters
            data: Request body data
            
        Returns:
            Response data as dictionary
        """
        url = f"{self.api_base}/{endpoint}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data
            )
            response.raise_for_status()
            
            # Some endpoints return empty responses
            if response.status_code == 204 or not response.content:
                return {}
            
            return response.json()
        
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            raise Exception(f"Jira API error: {error_msg}") from e
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}") from e
    
    def get_issue(self, issue_key: str, fields: Optional[List[str]] = None) -> Dict:
        """
        Get a single Jira issue
        
        Args:
            issue_key: Issue key (e.g., "DD-123")
            fields: Optional list of fields to retrieve
            
        Returns:
            Issue data
        """
        params = {}
        if fields:
            params['fields'] = ','.join(fields)
        
        return self._make_request('GET', f"issue/{issue_key}", params=params)
    
    def search_issues(
        self, 
        jql: str, 
        fields: Optional[List[str]] = None,
        max_results: int = 50,
        start_at: int = 0
    ) -> Dict:
        """
        Search for issues using JQL via the search/jql endpoint
        
        Args:
            jql: JQL query string
            fields: Optional list of fields to retrieve (defaults to key, summary, status, issuetype, priority, created, updated, description, parent)
            max_results: Maximum number of results to return
            start_at: Starting index for pagination (ignored with nextPageToken pagination)
            
        Returns:
            Search results including issues and metadata
        """
        # Build request parameters for GET request
        params = {
            'jql': jql,
            'maxResults': max_results
        }
        
        # Default fields if none specified - we need at least these for the DoR checker
        if not fields:
            fields = [
                'key', 'summary', 'status', 'issuetype', 'priority', 
                'created', 'updated', 'description', 'parent', 
                'customfield_12015',  # story_syntax
                'customfield_11874',  # acceptance_criteria (BDD/Gherkin)
                'customfield_11850',  # account_code (CDP Feature Development, etc.)
                'customfield_10201',  # sprint (for ordering and display)
                'labels', 'environment', 'storyPoints'
            ]
        
        # Add fields
        params['fields'] = ','.join(fields)
        
        # Use GET request to search/jql endpoint with query parameters
        result = self._make_request('GET', 'search/jql', params=params)
        
        # Convert to legacy format for compatibility with existing code
        # The new search/jql endpoint uses nextPageToken pagination, but we'll
        # keep the old interface for now
        if 'issues' in result:
            # Add total count estimate (not provided by new API, use length for now)
            if 'total' not in result:
                result['total'] = len(result['issues'])
        
        return result
    
    def create_issue(self, issue_data: Dict) -> Dict:
        """
        Create a new Jira issue
        
        Args:
            issue_data: Issue creation data following Jira API format
            
        Returns:
            Created issue data including key and ID
        """
        return self._make_request('POST', 'issue', data=issue_data)
    
    def update_issue(self, issue_key: str, update_data: Dict) -> Dict:
        """
        Update an existing Jira issue
        
        Args:
            issue_key: Issue key (e.g., "DD-123")
            update_data: Update data following Jira API format
            
        Returns:
            Response data (usually empty for successful updates)
        """
        return self._make_request('PUT', f"issue/{issue_key}", data=update_data)
    
    def get_field_metadata(self, project_key: str, issue_type_id: str) -> Dict:
        """
        Get field metadata for creating issues
        
        Args:
            project_key: Project key
            issue_type_id: Issue type ID
            
        Returns:
            Field metadata
        """
        return self._make_request(
            'GET',
            f"issue/createmeta/{project_key}/issuetypes/{issue_type_id}"
        )
    
    def get_transitions(self, issue_key: str) -> List[Dict]:
        """
        Get available transitions for an issue
        
        Args:
            issue_key: Issue key
            
        Returns:
            List of available transitions
        """
        result = self._make_request('GET', f"issue/{issue_key}/transitions")
        return result.get('transitions', [])
    
    def transition_issue(self, issue_key: str, transition_id: str) -> Dict:
        """
        Transition an issue to a new status
        
        Args:
            issue_key: Issue key
            transition_id: ID of the transition to execute
            
        Returns:
            Response data
        """
        data = {
            'transition': {
                'id': transition_id
            }
        }
        return self._make_request('POST', f"issue/{issue_key}/transitions", data=data)
    
    def get_project_info(self, project_key: str) -> Dict:
        """
        Get project information
        
        Args:
            project_key: Project key
            
        Returns:
            Project information
        """
        return self._make_request('GET', f"project/{project_key}")
    
    def add_comment(self, issue_key: str, comment_body: str) -> Dict:
        """
        Add a comment to an issue
        
        Args:
            issue_key: Issue key
            comment_body: Comment text
            
        Returns:
            Created comment data
        """
        data = {
            'body': {
                'type': 'doc',
                'version': 1,
                'content': [
                    {
                        'type': 'paragraph',
                        'content': [
                            {
                                'type': 'text',
                                'text': comment_body
                            }
                        ]
                    }
                ]
            }
        }
        return self._make_request('POST', f"issue/{issue_key}/comment", data=data)
    
    def get_user_by_account_id(self, account_id: str) -> Dict:
        """
        Get user details by account ID
        
        Args:
            account_id: Jira account ID
            
        Returns:
            User data including displayName, emailAddress, accountId
        """
        params = {'accountId': account_id}
        return self._make_request('GET', 'user', params=params)
    
    def get_issue_with_account(self, issue_id: str) -> Dict:
        """
        Get Jira issue details including key, summary, and account code
        
        Args:
            issue_id: Issue ID or key (e.g., "DD-123" or "10001")
            
        Returns:
            Dictionary with issue key, summary, and account code
        """
        # Fetch issue with specific fields
        fields = ['key', 'summary', self.config['custom_fields']['account_code']]
        issue_data = self.get_issue(issue_id, fields=fields)
        
        # Extract account code (customfield_11850)
        account_field_id = self.config['custom_fields']['account_code']
        account = issue_data.get('fields', {}).get(account_field_id)
        
        # Handle different account field formats
        if account and isinstance(account, dict):
            account = account.get('value', 'N/A')
        elif not account:
            account = 'N/A'
        
        return {
            'key': issue_data.get('key', 'UNKNOWN'),
            'summary': issue_data.get('fields', {}).get('summary', 'N/A'),
            'account': account
        }


def main():
    """
    Test the Jira client connection
    """
    try:
        client = JiraClient()
        print(f"✓ Connected to Jira: {client.jira_url}")
        print(f"✓ Project: {client.project_key}")
        
        # Test getting project info
        project_info = client.get_project_info(client.project_key)
        print(f"✓ Project Name: {project_info.get('name')}")
        
        print("\n✓ Jira client is configured correctly!")
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
