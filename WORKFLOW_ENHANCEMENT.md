# Proposed Workflow Enhancement: Context-Aware, Bi-Directional Synchronization

## 1. Executive Summary
The current Jira Task Automation tool operates as a one-way extraction and creation pipeline. It reads documents and blindly creates tasks in Jira. This leads to duplicate tickets if a document is re-processed, lacks contextual grouping (like Epics), and ignores the current state of the Jira board. 

This enhancement proposes a **Context-Aware, Bi-Directional Synchronization Workflow** leveraging Jira Query Language (JQL), the Atlassian Python SDK, and Pre-Extraction Space Context Injection to transform the system into an intelligent project management assistant.

## 2. Core Enhancements

### 2.1 Pre-Extraction Space Context Injection
Instead of relying solely on post-extraction validation, the system will fetch the current state of the Jira project *before* calling the LLM.

*   **Fetching Space Context:** The CLI uses the Jira SDK to execute a JQL query (e.g., `project = "PROJ" AND resolution = Unresolved ORDER BY updated DESC`). It formats this list of active Epics and tasks into a lightweight context string (e.g., `PROJ-101: Setup Database (In Progress)`).
*   **Context-Aware Prompting:** The LangChain system prompt is updated to provide the LLM with this context, instructing it to evaluate whether an extracted action item is new, an update to an existing task, or a sub-task of an existing item.

### 2.2 Evolving the Pydantic Schema
To support the LLM's new decision-making capabilities, the Pydantic schema in `task_extractor.py` will be updated to handle different action types:

```python
from pydantic import BaseModel, Field
from typing import Optional, Literal

class TaskAction(BaseModel):
    action: Literal["CREATE", "UPDATE", "SUBTASK"] = Field(
        description="Whether to CREATE a new task, UPDATE an existing one, or create a SUBTASK."
    )
    title: str = Field(description="The title of the task.")
    description: str = Field(description="Detailed description or the update comment.")
    target_issue_key: Optional[str] = Field(
        description="If action is UPDATE or SUBTASK, provide the existing Jira issue key (e.g., PROJ-123). Null if CREATE."
    )
    assignee: Optional[str] = Field(description="The person responsible, if mentioned.")
    dependencies: list[str] = Field(default_factory=list, description="Titles or keys of dependent tasks.")

class DocumentActionList(BaseModel):
    tasks: list[TaskAction]
    epic_theme: Optional[str] = Field(description="The overarching theme or Epic for these tasks.")
```

### 2.3 Intelligent Execution & Deduplication (`jira_client.py`)
The execution flow will act on the LLM's categorized decisions rather than just creating standalone issues:

*   **CREATE:** The script creates a new issue.
*   **UPDATE:** If the LLM identifies that the topic belongs to an existing issue (`PROJ-101`), the script uses the SDK to append a comment to that issue (e.g., *"Update from latest document: [Details]"*) instead of creating a duplicate.
*   **SUBTASK:** The script creates a new sub-task explicitly linked to the parent issue identified by the LLM.

### 2.4 Dynamic Epic Management
If the LLM extracts an `epic_theme`, the script uses JQL to search for an existing Epic (`project = "PROJ" AND issuetype = Epic AND summary ~ "{epic_theme}"`). If found, newly created tasks are linked to it. If not, the Epic is created first, and tasks are subsequently linked.

### 2.5 Automated Dependency Linking
Using the `dependencies` field extracted by the LLM, the `jira_client` iterates through the created tasks and uses the SDK's linking capability (`jira.create_issue_link(type="Blocks", inwardIssue=dependency_key, outwardIssue=task_key)`) to map out execution order.

## 3. Key Benefits

1.  **Zero Hallucinated Duplicates:** The LLM knows exactly what exists. If a document revisits "Database schema design," the LLM maps it to the existing ticket rather than creating a new one.
2.  **Historical Threading:** Meeting notes often revisit old topics. This workflow automatically appends the latest notes as comments to existing tickets, maintaining a single source of truth.
3.  **Hierarchical Understanding:** The LLM can automatically build out Epic -> Task -> Sub-task hierarchies natively because it can "see" the existing Epics and tasks in the Space.
4.  **Relational Context:** Dependencies (Blocks/Blocked By) are automatically generated, providing a ready-to-use critical path for the engineering team.
