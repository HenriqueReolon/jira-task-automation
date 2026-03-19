import os
from typing import List
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

class Task(BaseModel):
    title: str = Field(description="A concise and clear title for the task (Jira Summary).")
    description: str = Field(description="A detailed description of the task, including steps, context, or acceptance criteria (Jira Description).")
    issue_type: str = Field(description="The type of Jira issue, usually 'Task', 'Bug', or 'Story'.", default="Task")

class TaskList(BaseModel):
    tasks: List[Task] = Field(description="A list of engineering/production tasks extracted from the document.")

class TaskExtractor:
    def __init__(self, model_name: str = "gemini-3-pro-preview"):
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
        self.structured_llm = self.llm.with_structured_output(TaskList)
        
        # Build prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert technical project manager and agile coach. Your role is to carefully analyze "
                       "meeting transcripts, documents, PDFs, or spreadsheets, and extract actionable engineering and "
                       "production tasks. Ensure tasks are well-defined, containing a clear title and a detailed actionable description "
                       "with context and criteria if present. Output ONLY the extracted tasks based on the provided text, ALWAYS in Brazilian Portuguese."),
            ("user", "Document Context:\n{document_text}\n\nExtract the engineering/production tasks from the context.")
        ])
        
        # Chain
        self.chain = self.prompt | self.structured_llm

    def extract_tasks(self, document_text: str) -> List[Task]:
        """
        Executes the extraction chain over the provided document text.
        """
        try:
            response = self.chain.invoke({"document_text": document_text})
            if response and hasattr(response, 'tasks'):
                return response.tasks
            return []
        except Exception as e:
            print(f"Error during task extraction: {e}")
            raise
