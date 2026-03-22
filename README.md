# Jira Task Automation

An automated Python CLI tool that parses documents (PDFs, DOCX, TXT, Excel/CSV) containing meeting notes or project specifications, extracts engineering and production tasks using Google Gemini 3 Pro (via LangChain), and publishes them directly to Jira.

## Features
- **Multi-file Document Support:** Processes single or multiple PDFs, DOCX, TXT, CSV, and Excel spreadsheets simultaneously using LangChain document loaders.
- **Context-Aware LLM Extraction:** Injects active Jira project context into Google Gemini Pro (via LangChain) to intelligently categorize tasks (Creates, Updates, and Sub-tasks).
- **Dynamic Epic Management & Dependency Linking:** Automatically identifies Epic themes, links tasks to Epics, and establishes "Blocks/Blocked By" issue links based on task dependencies.
- **Automated Bi-Directional Jira Integration:** Creates new issues, appends comments to existing issues (preventing duplicates), and manages sub-tasks directly in the target Jira project.
- **Dry-Run Mode:** Validate your extracted tasks and Jira actions locally without executing them in Jira.

## Prerequisites
- Python 3.10+
- Jira Account & API Token
- Google Gemini API Key

## Setup

1. **Clone or Download the Repository:**
   Make sure you are in the project folder.

2. **Create a Virtual Environment & Install Dependencies:**
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\Activate.ps1
   # On macOS/Linux:
   source venv/bin/activate

   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**
   Rename `.env.example` to `.env` and fill in your details:
   ```env
   JIRA_SERVER_URL=https://your-domain.atlassian.net
   JIRA_USER_EMAIL=your-email@example.com
   JIRA_API_TOKEN=your-jira-api-token
   JIRA_PROJECT_KEY=PROJ

   GOOGLE_API_KEY=your-gemini-api-key
   ```

   *Note: You can generate a Jira API token from your Atlassian account security settings.*

## Usage

Run the CLI tool using its subcommands: `extract` and `plan-sprint`.

### Extract and Create Tasks in Jira
Pass one or more file paths to your documents.
```bash
python main.py extract path/to/meeting_notes.pdf path/to/schedule.xlsx
```

### Dry Run (Extract without Publishing)
Use the `--dry-run` flag to safely preview the extracted tasks on the console.
```bash
python main.py extract path/to/meeting_notes.txt --dry-run
```

### Plan a Sprint
Analyze current backlog tasks and organize them into a Sprint based on your instructions.
```bash
python main.py plan-sprint --instructions "Focus on high priority bug fixes and the new login page"
# Or provide a text file
python main.py plan-sprint --instructions path/to/instructions.txt --dry-run
```

### Customizing the Model
You can specify a different Gemini model if required (default is `gemini-3-pro-preview`).
```bash
python main.py extract path/to/document.docx --model gemini-3.1-pro-preview
```

## Supported File Formats
- `.txt` (Plain text)
- `.pdf` (Portable Document Format)
- `.docx` / `.doc` (Microsoft Word)
- `.csv` (Comma-separated values)
- `.xls` / `.xlsx` (Microsoft Excel)
