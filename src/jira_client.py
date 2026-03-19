import os
from jira import JIRA
from typing import Dict, Any

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

    def create_task(self, title: str, description: str, issue_type: str = "Task") -> str:
        """
        Creates a task in the specified Jira project.
        """
        issue_dict: Dict[str, Any] = {
            'project': {'key': self.project_key},
            'summary': title,
            'description': description,
            'issuetype': {'name': issue_type},
        }
        
        try:
            new_issue = self.jira.create_issue(fields=issue_dict)
            return str(new_issue.key)
        except Exception as e:
            print(f"Failed to create Jira task: {e}")
            raise
