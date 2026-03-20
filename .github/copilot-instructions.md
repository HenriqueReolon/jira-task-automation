# Jira Task Automation - Workspace Instructions

This document provides the necessary context, architectural decisions, and rules for maintaining and expanding the Jira Task Automation Python CLI project.

## Project Overview
An automated Python CLI tool that parses documents (PDFs, DOCX, TXT, Excel/CSV) containing meeting notes or project specifications, extracts engineering and production tasks using Google Gemini 3 Pro (via LangChain), and publishes them directly to a Jira Space.

## Tech Stack
- **Python 3.10+**
- **CLI Framework:** `Click`
- **LLM / Parsing:** `langchain`, `langchain-google-genai`, `langchain-community`, `pydantic`
- **Jira Integration:** `jira` (Atlassian Python SDK)
- **Document Loaders:** `pypdf`, `python-docx`, `docx2txt`, `pandas`, `openpyxl`
- **Environment Management:** `python-dotenv`

## Architecture & Module Responsibilities
- `main.py`: The Click CLI entry point. Orchestrates the flow from loading a document to extracting tasks and publishing them to Jira. Handles all user-facing console output.
- `src/document_loader.py`: Responsible for reading various file formats and converting them into plain text using LangChain community document loaders.
- `src/task_extractor.py`: Handles the interaction with the Gemini LLM. Uses LangChain's `with_structured_output` mechanism alongside Pydantic models (`Task`, `TaskList`) to guarantee the LLM returns properly structured JSON instead of arbitrary text.
- `src/jira_client.py`: Manages the Jira connection using basic auth (email + token) and handles the creation of standard Jira Issues.

## Core Maintenance Rules

### 1. LLM Model Versioning (CRITICAL)
- The correct Google Gemini model string to use for Gemini 3 Pro is **`gemini-3-pro-preview`** (or `gemini-3.1-pro-preview`). 
- **DO NOT** revert to `gemini-1.5-pro` as it is not supported by the current `v1beta` endpoint for this specific workflow.

### 2. Testing and Execution
- **Always use the `--dry-run` flag** when running local tests to validate document extraction. This prevents accidental spamming of the production Jira project.
- Example: `python main.py documents/plano_de_acao.xlsx --dry-run`

### 3. Expanding Document Formats
- When adding support for a new file extension in `src/document_loader.py`, you must also add the appropriate underlying dependency (e.g., a specific LangChain community loader parser) to `requirements.txt`.

### 4. Modifying Task Extraction Fields
If the business requirements change and new fields are needed (e.g., Assignee, Story Points, Labels, Priority):
1. **Update Pydantic Models:** Add the new field to the `Task` class in `src/task_extractor.py` with a clear `Field(description="...")` so the LLM knows how to populate it.
2. **Update Jira Mapping:** Update the `issue_dict` payload in `src/jira_client.py`'s `create_task` method to map the new Pydantic field to the correct Jira API field.
3. **Update Prompts (If necessary):** Adjust the `system` prompt in `task_extractor.py` to instruct the LLM on how to extract the new data.