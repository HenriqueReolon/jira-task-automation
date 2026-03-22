import os
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

class TaskAction(BaseModel):
    action: Literal["CREATE", "UPDATE", "SUBTASK"] = Field(
        description="Whether to CREATE a new task, UPDATE an existing one, or create a SUBTASK."
    )
    title: str = Field(description="The title of the task.")
    description: str = Field(description="Detailed description or the update comment.")
    target_issue_key: Optional[str] = Field(
        description="If action is UPDATE or SUBTASK, provide the existing Jira issue key (e.g., PROJ-123). Null if CREATE.",
        default=None
    )
    assignee: Optional[str] = Field(description="The person responsible, if mentioned.", default=None)
    dependencies: list[str] = Field(default_factory=list, description="Titles or keys of dependent tasks.")
    issue_type: str = Field(description="The type of Jira issue, usually 'Task', 'Bug', or 'Story'.", default="Task")

class DocumentActionList(BaseModel):
    tasks: List[TaskAction] = Field(description="A list of engineering/production tasks extracted from the document.")
    epic_theme: Optional[str] = Field(description="The overarching theme or Epic for these tasks.", default=None)

class TaskExtractor:
    def __init__(self, model_name: str = "gemini-3-pro-preview", jira_context: str = ""):
        """
        Initializes the Task Extractor using LangChain Google GenAI and Gemini 3 Pro (mapped to gemini-3-pro-preview or desired version).
        Make sure GOOGLE_API_KEY environment variable is set.
        """
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is missing.")
            
        # Initialize Gemini LLM
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=self.api_key,
            temperature=0.2
        )
        
        # Configure structured output parser
        self.structured_llm = self.llm.with_structured_output(DocumentActionList)
        
        # Build prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", f"You are an expert technical project manager and agile coach. Your role is to carefully analyze "
                       f"meeting transcripts, documents, PDFs, or spreadsheets, and extract actionable engineering and "
                       f"production tasks.\n\n"
                       f"You must evaluate whether an extracted action item is new, an update to an existing task, or a sub-task "
                       f"of an existing item based on the current state of the Jira project:\n\n"
                       f"=== CURRENT JIRA CONTEXT ===\n"
                       f"{jira_context}\n"
                       f"============================\n\n"
                       f"CRITICAL: The 'issue_type' field MUST be one of the valid issue types listed in the Jira context "
                       f"(if provided), otherwise use 'Task' or 'Story'. Do not invent new issue types.\n"
                       f"Ensure tasks are well-defined, containing a clear title and a detailed actionable description "
                       f"with context and criteria if present. Output ONLY the extracted tasks based on the provided text, ALWAYS in Brazilian Portuguese."),
            ("user", "Document Context:\n{document_text}\n\nExtract the engineering/production tasks from the context.")
        ])
        
        # Chain
        self.chain = self.prompt | self.structured_llm

    def extract_tasks(self, document_text: str) -> Optional[DocumentActionList]:
        """
        Executes the extraction chain over the provided document text.
        """
        try:
            response = self.chain.invoke({"document_text": document_text})
            return response
        except Exception as e:
            print(f"Error during task extraction: {e}")
            raise
