"""
Definition of Ready Checker - Scores issues against the Definition of Ready checklist
"""

import yaml
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import re


class DoRChecker:
    """
    Checks Jira issues against the Definition of Ready checklist
    and provides a readiness score
    """

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the DoR checker with configuration
        
        Args:
            config_path: Path to the YAML configuration file
        """
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.checklist = self.config['definition_of_ready']
        self.custom_fields = self.config['custom_fields']
        
        # Calculate total possible weight
        self.total_weight = sum(item['weight'] for item in self.checklist)
    
    def check_issue(self, issue_data: Dict) -> Dict:
        """
        Check an issue against the Definition of Ready
        
        Args:
            issue_data: Jira issue data (from API)
            
        Returns:
            Dictionary with score, percentage, checklist results, recommendations,
            and content for LLM evaluation
        """
        fields = issue_data.get('fields', {})
        issue_type = fields.get('issuetype', {}).get('name', '').lower()
        
        results = []
        total_score = 0
        max_possible = 0
        
        for item in self.checklist:
            # Check if this item applies to this issue type
            applies_to = item.get('applies_to', [])
            if applies_to and issue_type not in [t.lower() for t in applies_to]:
                # Item doesn't apply to this issue type - skip entirely
                continue
            
            # Check if this is optional
            is_optional = item.get('optional', False)
            
            # Get the weight for this item
            weight = item['weight']
            max_possible += weight
            
            # Check the field
            passed, details = self._check_field(item, fields, issue_type)
            
            score = weight if passed else 0
            total_score += score
            
            results.append({
                'name': item['name'],
                'passed': passed,
                'optional': is_optional,
                'weight': weight,
                'score': score,
                'details': details
            })
        
        # Calculate percentage
        percentage = (total_score / max_possible * 100) if max_possible > 0 else 0
        
        # Generate recommendations
        recommendations = self._generate_recommendations(results, fields, issue_type)
        
        return {
            'score': total_score,
            'max_score': max_possible,
            'percentage': round(percentage, 1),
            'checklist': results,
            'recommendations': recommendations,
            'issue_key': issue_data.get('key'),
            'summary': fields.get('summary'),
            'status': fields.get('status', {}).get('name')
        }
    
    def get_content_for_llm_review(self, issue_data: Dict) -> List[Dict]:
        """
        Extract content from issue that needs LLM evaluation for quality assessment.
        This is used for semantic/qualitative checks that can't be done deterministically.
        
        Args:
            issue_data: Jira issue data (from API)
            
        Returns:
            List of dictionaries with field names, content, and evaluation prompts
        """
        fields = issue_data.get('fields', {})
        llm_reviews = []
        
        # Story Syntax - check quality
        story_syntax = fields.get(self.custom_fields.get('story_syntax'))
        if story_syntax:
            content = self._extract_adf_text(story_syntax) if isinstance(story_syntax, dict) else str(story_syntax)
            if content and len(content) > 10:
                llm_reviews.append({
                    'field_name': 'story_syntax',
                    'criterion': 'Story syntax quality (As a... I want... So that...)',
                    'content': content,
                    'prompt': 'Evaluate if this story syntax follows the format "As a [user type] I want [feature] So that [benefit]" and provides meaningful context. Is it complete and valuable, or just template text?'
                })
        
        # Acceptance Criteria - check quality
        acceptance_criteria = fields.get(self.custom_fields.get('acceptance_criteria'))
        if acceptance_criteria:
            content = self._extract_adf_text(acceptance_criteria) if isinstance(acceptance_criteria, dict) else str(acceptance_criteria)
            if content and len(content) > 10:
                llm_reviews.append({
                    'field_name': 'acceptance_criteria',
                    'criterion': 'Acceptance criteria quality (BDD/Gherkin)',
                    'content': content,
                    'prompt': 'Evaluate if these acceptance criteria use proper BDD/Gherkin format (Given/When/Then or Feature/Scenario format) and define testable, specific outcomes. Are they meaningful and complete, or just boilerplate?'
                })
        
        # Description - check for environments, security, docs, demo, cost, telemetry
        description = fields.get('description', '')
        if description:
            desc_text = self._extract_adf_text(description) if isinstance(description, dict) else str(description)
            if desc_text and len(desc_text) > 20:
                llm_reviews.append({
                    'field_name': 'environments',
                    'criterion': 'Environments defined (Staging/Pre-prod/Production)',
                    'content': desc_text,
                    'prompt': 'Does this description mention or discuss deployment to different environments like staging, pre-production, and production? Look for environment-specific concerns or deployment strategies.'
                })
                
                llm_reviews.append({
                    'field_name': 'security',
                    'criterion': 'Security posture/implications/risks defined',
                    'content': desc_text,
                    'prompt': 'Does this description address security considerations, risks, threats, authentication, authorization, data protection, or compliance requirements?'
                })
                
                llm_reviews.append({
                    'field_name': 'documentation',
                    'criterion': 'Relevant documentation identified',
                    'content': desc_text,
                    'prompt': 'Does this description reference or link to relevant documentation, wikis, Confluence pages, ADRs, or other knowledge base articles?'
                })
                
                llm_reviews.append({
                    'field_name': 'demo',
                    'criterion': 'What to demo has been defined',
                    'prompt': 'Does this description specify what will be demonstrated or shown to stakeholders upon completion?'
                })
                
                llm_reviews.append({
                    'field_name': 'cost',
                    'criterion': 'Cost implications considered',
                    'content': desc_text,
                    'prompt': 'Does this description discuss cost implications, infrastructure expenses, licensing fees, or budget considerations?'
                })
                
                llm_reviews.append({
                    'field_name': 'telemetry',
                    'criterion': 'Telemetry considered - metrics and alerts defined',
                    'content': desc_text,
                    'prompt': 'Does this description specify telemetry, metrics, monitoring, alerts, dashboards, or observability requirements?'
                })
        
        return llm_reviews
    
    def _check_field(self, item: Dict, fields: Dict, issue_type: str = '') -> Tuple[bool, str]:
        """
        Check if a specific field meets the criteria
        
        Args:
            item: Checklist item configuration
            fields: Issue fields data
            issue_type: Type of the issue (story, task, bug, etc.)
            
        Returns:
            Tuple of (passed: bool, details: str)
        """
        field_name = item.get('field')
        
        # Handle standard fields
        if field_name == 'summary':
            value = fields.get('summary', '')
            if value and len(value.strip()) > 3:
                return True, f"Title: '{value}'"
            return False, "Title is missing or too short"
        
        if field_name == 'parent':
            parent = fields.get('parent')
            if parent:
                return True, f"Linked to {parent.get('key')}"
            if item.get('optional'):
                return True, "Optional - No parent epic"
            return False, "No parent epic linked"
        
        # Handle custom fields
        if 'field_name' in item:
            custom_field_id = item['field_name']
        elif field_name in self.custom_fields:
            # field_name is a logical name like 'account_code'
            custom_field_id = self.custom_fields[field_name]
        elif field_name and field_name.startswith('customfield_'):
            # field_name is already a custom field ID
            custom_field_id = field_name
        else:
            custom_field_id = None
        
        if custom_field_id:
            value = fields.get(custom_field_id)
            
            # Special handling for story syntax on non-story types
            # If this field has 'optional_for_non_stories' flag and issue is not a story, be lenient
            if item.get('optional_for_non_stories') and issue_type and issue_type != 'story':
                # For non-story types, this field is optional
                # If it's not set or just has template text, mark as N/A (passed)
                if not value:
                    return True, "N/A (not required for this issue type)"
                
                # Extract text to check if it's just template
                content_text = self._extract_adf_text(value) if isinstance(value, dict) else str(value)
                
                # Check if it's just the default template (for story syntax specifically)
                if self._is_story_syntax_template(content_text):
                    return True, "N/A (template text, not required for this issue type)"
                
                # If they've filled it in meaningfully, that's great too
                if self._has_meaningful_content(content_text):
                    return True, f"Optional but provided ({len(content_text)} chars)"
            
            # Check if field has content
            if value:
                # Handle different field types
                if isinstance(value, dict):
                    # Could be ADF (Atlassian Document Format) or object
                    if 'content' in value:
                        # ADF format - check if it has actual content beyond default
                        content_text = self._extract_adf_text(value)
                        if self._has_meaningful_content(content_text):
                            return True, f"Field is populated ({len(content_text)} chars)"
                        return False, "Field contains only template/default text"
                    elif 'value' in value:
                        # Select field
                        return True, f"Set to: {value['value']}"
                elif isinstance(value, (str, int, float)):
                    if str(value).strip():
                        return True, f"Value: {value}"
                elif isinstance(value, list) and len(value) > 0:
                    return True, f"Contains {len(value)} item(s)"
            
            return False, f"Field '{item['name']}' is not populated"
        
        # Handle fields that need to be checked in description
        if item.get('check_in_description'):
            description = fields.get('description', '')
            if isinstance(description, str):
                desc_text = description.lower()
            else:
                desc_text = self._extract_adf_text(description).lower()
            
            # Look for keywords related to the field
            keywords = self._get_keywords_for_field(field_name)
            found_keywords = [kw for kw in keywords if kw in desc_text]
            
            if found_keywords and len(desc_text) > 50:
                return True, f"Mentioned in description: {', '.join(found_keywords)}"
            return False, f"Not mentioned in description (expected: {', '.join(keywords[:3])})"
        
        return False, "Could not evaluate field"
    
    def _extract_adf_text(self, adf: Dict) -> str:
        """
        Extract plain text from Atlassian Document Format
        
        Args:
            adf: ADF document structure
            
        Returns:
            Plain text content
        """
        if not isinstance(adf, dict):
            return str(adf)
        
        text_parts = []
        
        def extract_recursive(node):
            if isinstance(node, dict):
                if node.get('type') == 'text':
                    text_parts.append(node.get('text', ''))
                
                # Recurse into content
                if 'content' in node:
                    for child in node['content']:
                        extract_recursive(child)
            elif isinstance(node, list):
                for item in node:
                    extract_recursive(item)
        
        extract_recursive(adf)
        return ' '.join(text_parts)
    
    def _has_meaningful_content(self, text: str) -> bool:
        """
        Check if text has meaningful content beyond templates
        
        Args:
            text: Text to check
            
        Returns:
            True if content appears meaningful
        """
        if not text or len(text.strip()) < 20:
            return False
        
        # Check for common template phrases
        template_phrases = [
            'as a i would like so that',
            'steps to reproduce 1. login 2. navigate to page 3. click stuff',
            'please describe what the expected behavior is',
            'what actually happens',
        ]
        
        normalized = ' '.join(text.lower().split())
        
        for phrase in template_phrases:
            if phrase in normalized:
                return False
        
        return True
    
    def _is_story_syntax_template(self, text: str) -> bool:
        """
        Check if text is just the story syntax template without real content
        
        Args:
            text: Text to check
            
        Returns:
            True if this appears to be just the unfilled template
        """
        if not text:
            return True
        
        normalized = ' '.join(text.lower().split())
        
        # Common story syntax template patterns
        template_patterns = [
            'as a i want so that',
            'as a i would like so that',
            'as a [user type] i want [feature] so that [benefit]',
            'as a [user type] i would like [feature] so that [benefit]',
        ]
        
        for pattern in template_patterns:
            if pattern in normalized:
                return True
        
        # Check if it's very short and contains the key words but nothing else
        if len(normalized) < 30 and 'as a' in normalized and ('i want' in normalized or 'i would like' in normalized):
            return True
        
        return False
    
    def _get_keywords_for_field(self, field_name: str) -> List[str]:
        """
        Get search keywords for a field name
        
        Args:
            field_name: Name of the field
            
        Returns:
            List of keywords to search for
        """
        keyword_map = {
            'environments': ['staging', 'pre-prod', 'pre-production', 'production', 'environment', 'deploy'],
            'security': ['security', 'threat', 'risk', 'authentication', 'authorization', 'vulnerability'],
            'documentation': ['documentation', 'docs', 'wiki', 'readme', 'confluence'],
            'demo': ['demo', 'demonstrate', 'show', 'presentation'],
            'cost': ['cost', 'price', 'budget', 'expense', 'billing', '$'],
            'telemetry': ['telemetry', 'metrics', 'monitoring', 'alert', 'observability', 'logging', 'datadog', 'grafana']
        }
        
        return keyword_map.get(field_name, [field_name])
    
    def _generate_recommendations(
        self, 
        results: List[Dict], 
        fields: Dict,
        issue_type: str
    ) -> List[str]:
        """
        Generate recommendations for improving the issue
        
        Args:
            results: Checklist results
            fields: Issue fields
            issue_type: Type of issue
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        failed_items = [r for r in results if not r['passed'] and not r['optional']]
        
        if not failed_items:
            recommendations.append("✓ Issue meets all required Definition of Ready criteria!")
            return recommendations
        
        recommendations.append(f"Missing {len(failed_items)} required item(s):")
        
        for item in failed_items:
            recommendations.append(f"  • {item['name']}: {item['details']}")
        
        # Add specific suggestions
        if any('story syntax' in r['name'].lower() for r in failed_items):
            recommendations.append("\n💡 Tip: Use the story syntax template:")
            recommendations.append("   As a [USER TYPE]")
            recommendations.append("   I want [FEATURE]")
            recommendations.append("   So that [BENEFIT]")
        
        if any('acceptance criteria' in r['name'].lower() for r in failed_items):
            recommendations.append("\n💡 Tip: Use BDD/Gherkin format:")
            recommendations.append("   Given [precondition]")
            recommendations.append("   When [action]")
            recommendations.append("   Then [expected outcome]")
        
        return recommendations
    
    def get_readiness_level(self, percentage: float) -> str:
        """
        Get a human-readable readiness level
        
        Args:
            percentage: Readiness percentage
            
        Returns:
            Readiness level description
        """
        if percentage >= 90:
            return "✅ Ready"
        elif percentage >= 70:
            return "⚠️  Nearly Ready"
        elif percentage >= 50:
            return "🔸 Partially Ready"
        else:
            return "❌ Not Ready"


def main():
    """
    Test the DoR checker with sample data
    """
    checker = DoRChecker()
    
    # Sample issue data
    sample_issue = {
        'key': 'DD-TEST',
        'fields': {
            'summary': 'Test issue for DoR checking',
            'description': 'This will be deployed to staging and production environments. Security has been reviewed.',
            'issuetype': {'name': 'Story'},
            'status': {'name': 'Not Ready'},
            'customfield_12015': {
                'type': 'doc',
                'version': 1,
                'content': [
                    {
                        'type': 'paragraph',
                        'content': [
                            {'type': 'text', 'text': 'As a user I want to test So that it works'}
                        ]
                    }
                ]
            }
        }
    }
    
    result = checker.check_issue(sample_issue)
    
    print(f"\n{'='*60}")
    print(f"Definition of Ready Check: {result['issue_key']}")
    print(f"{'='*60}")
    print(f"\nScore: {result['score']}/{result['max_score']} ({result['percentage']}%)")
    print(f"Level: {checker.get_readiness_level(result['percentage'])}")
    
    print(f"\nChecklist Results:")
    for item in result['checklist']:
        status = "✓" if item['passed'] else "✗"
        optional = " (optional)" if item['optional'] else ""
        print(f"  {status} {item['name']}{optional}")
        if not item['passed']:
            print(f"     → {item['details']}")
    
    print(f"\nRecommendations:")
    for rec in result['recommendations']:
        print(rec)


if __name__ == "__main__":
    main()
