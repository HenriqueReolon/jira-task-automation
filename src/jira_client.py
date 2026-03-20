import os
from jira import JIRA
from typing import Dict, Any, Optional

class JiraManager:
    def __init__(self):
        self.server = os.getenv("JIRA_SERVER_URL")
        self.email = os.getenv("JIRA_USER_EMAIL")
        self.token = os.getenv("JIRA_API_TOKEN")
        self.project_key = os.getenv("JIRA_PROJECT_KEY")

        if not all([self.server, self.email, self.token, self.project_key]):
            raise ValueError("Missing Jira environment variables. Please check your .env file.")

        self.jira = JIRA(
            server=self.server,
            basic_auth=(self.email, self.token)
        )

    def get_active_context(self) -> str:
        """
        Fetches the current state of the Jira project to provide context to the LLM.
        """
        try:
            jql = f'project = "{self.project_key}" AND resolution = Unresolved ORDER BY updated DESC'
            issues = self.jira.search_issues(jql, maxResults=50)
            context_lines = []
            for issue in issues:
                issue_type = issue.fields.issuetype.name
                summary = issue.fields.summary
                status = issue.fields.status.name
                context_lines.append(f"{issue.key} ({issue_type}): {summary} [{status}]")
            
            return "\n".join(context_lines)
        except Exception as e:
            print(f"Failed to fetch active context from Jira: {e}")
            return ""

    def get_or_create_epic(self, epic_theme: str) -> str:
        """
        Searches for an existing Epic by summary. If found, returns its key.
        Otherwise, creates a new Epic and returns its key.
        """
        try:
            # Note: "Epic Name" custom field might be required depending on Jira config.
            # Usually, standard search by summary works.
            jql = f'project = "{self.project_key}" AND issuetype = Epic AND summary ~ "\\"{epic_theme}\\""'
            issues = self.jira.search_issues(jql, maxResults=1)
            
            if issues:
                return str(issues[0].key)

            # Need to create Epic
            # Epic Name field is often customfield_10011 but can vary. 
            # We'll try to set the summary and if customfield is needed it might fail, 
            # but let's assume standard issuetype=Epic for now.
            issue_dict = {
                'project': {'key': self.project_key},
                'summary': epic_theme,
                'description': f"Epic generated from document: {epic_theme}",
                'issuetype': {'name': 'Epic'},
            }
            # Attempt to discover Epic Name custom field
            epic_name_field = self._get_epic_name_field()
            if epic_name_field:
                issue_dict[epic_name_field] = epic_theme

            new_epic = self.jira.create_issue(fields=issue_dict)
            return str(new_epic.key)
        except Exception as e:
            print(f"Failed to get or create Epic '{epic_theme}': {e}")
            raise

    def _get_epic_name_field(self) -> Optional[str]:
        try:
            fields = self.jira.fields()
            for field in fields:
                if field['name'] == 'Epic Name':
                    return field['id']
            return None
        except:
            return None

    def create_task(self, title: str, description: str, issue_type: str = "Task", epic_key: Optional[str] = None) -> str:
        """
        Creates a task in the specified Jira project, optionally linking to an Epic.
        """
        issue_dict: Dict[str, Any] = {
            'project': {'key': self.project_key},
            'summary': title,
            'description': description,
            'issuetype': {'name': issue_type},
        }
        
        # Link to epic if provided. The Epic Link custom field name can vary.
        # Often it's customfield_10014
        if epic_key:
            epic_link_field = self._get_epic_link_field()
            if epic_link_field:
                issue_dict[epic_link_field] = epic_key
        
        try:
            new_issue = self.jira.create_issue(fields=issue_dict)
            return str(new_issue.key)
        except Exception as e:
            print(f"Failed to create Jira task: {e}")
            raise

    def _get_epic_link_field(self) -> Optional[str]:
        try:
            fields = self.jira.fields()
            for field in fields:
                if field['name'] == 'Epic Link':
                    return field['id']
            return None
        except:
            return None

    def create_subtask(self, parent_key: str, title: str, description: str) -> str:
        """
        Creates a sub-task linked to the specified parent issue.
        """
        issue_dict: Dict[str, Any] = {
            'project': {'key': self.project_key},
            'summary': title,
            'description': description,
            'issuetype': {'name': 'Sub-task'},
            'parent': {'key': parent_key}
        }
        
        try:
            new_issue = self.jira.create_issue(fields=issue_dict)
            return str(new_issue.key)
        except Exception as e:
            print(f"Failed to create sub-task: {e}")
            raise

    def add_comment(self, issue_key: str, comment: str):
        """
        Appends a comment to an existing Jira issue.
        """
        try:
            self.jira.add_comment(issue_key, f"Update from latest document: {comment}")
        except Exception as e:
            print(f"Failed to add comment to {issue_key}: {e}")
            raise

    def create_dependency(self, source_key: str, target_key: str):
        """
        Creates a Blocks link from source_key to target_key.
        """
        try:
            # According to enhancement plan: inwardIssue=dependency_key (target_key), outwardIssue=task_key (source_key)
            self.jira.create_issue_link(type="Blocks", inwardIssue=target_key, outwardIssue=source_key)
        except Exception as e:
            print(f"Failed to create issue link between {source_key} and {target_key}: {e}")

