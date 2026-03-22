import os
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

class IssueSelection(BaseModel):
    issue_key: str = Field(description="The key of the Jira issue to include in the sprint (e.g., PROJ-123).")
    rationale: str = Field(description="Reason for including this issue in the sprint based on the user instructions.")

class SprintPlan(BaseModel):
    sprint_name: str = Field(description="A concise and descriptive name for the sprint. MUST BE UNDER 30 CHARACTERS.")
    sprint_goal: str = Field(description="The overarching goal or objective for this sprint.")
    selected_issues: List[IssueSelection] = Field(description="The list of issues selected to be part of the sprint.")

class SprintPlanner:
    def __init__(self, model_name: str = "gemini-3-pro-preview"):
        """
        Initializes the Sprint Planner using LangChain Google GenAI and Gemini 3 Pro.
        """
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is missing.")
            
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=self.api_key,
            temperature=0.2
        )
        
        self.structured_llm = self.llm.with_structured_output(SprintPlan)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", f"You are an expert Scrum Master and Agile Coach. Your role is to analyze a list of current backlog "
                       f"tasks and organize them into a cohesive Sprint, following the specific instructions provided by the user.\n\n"
                       f"You will receive:\n"
                       f"1. A list of available tasks in the Jira backlog (with their keys, summaries, and types).\n"
                       f"2. The user's instructions for the sprint (e.g., priority focus, target features, constraints).\n\n"
                       f"Your task is to:\n"
                       f"- Select the most appropriate issues from the backlog that align with the user's instructions.\n"
                       f"- Formulate a clear 'sprint_name' and a 'sprint_goal'.\n"
                       f"- Provide a rationale for why each issue was selected.\n\n"
                       f"CRITICAL RULES:\n"
                       f"1. The 'sprint_name' MUST NOT exceed 30 characters in length. This is a strict Jira limitation.\n"
                       f"2. Only select issues that are explicitly listed in the provided backlog context. Do NOT invent new issue keys.\n"
                       f"Output your response in the requested structured format, and use Brazilian Portuguese for descriptions and goals."),
            ("user", "Backlog Tasks:\n{backlog_tasks}\n\nSprint Instructions:\n{instructions}")
        ])
        
        self.chain = self.prompt | self.structured_llm

    def plan_sprint(self, backlog_tasks: str, instructions: str) -> Optional[SprintPlan]:
        """
        Analyzes the backlog tasks and user instructions to generate a structured SprintPlan.
        """
        try:
            response = self.chain.invoke({
                "backlog_tasks": backlog_tasks,
                "instructions": instructions
            })
            return response
        except Exception as e:
            print(f"Error during sprint planning: {e}")
            raise
