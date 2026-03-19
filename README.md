# Jira Task Automation

An automated Python CLI tool that parses documents (PDFs, DOCX, TXT, Excel/CSV) containing meeting notes or project specifications, extracts engineering and production tasks using Google Gemini 3 Pro (via LangChain), and publishes them directly to Jira.

## Features
- **Multi-format Document Support:** Reads PDF, DOCX, TXT, CSV, and Excel spreadsheets using LangChain document loaders.
- **LLM-Powered Extraction:** Uses LangChain with Google Gemini Pro to identify actionable engineering and production tasks.
- **Automated Jira Integration:** Publishes parsed tasks to a target Jira project.
- **Dry-Run Mode:** Validate your extracted tasks locally without creating them in Jira.

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

Run the CLI tool by passing the file path to your document.

### Extract and Create Tasks in Jira
```bash
python main.py path/to/meeting_notes.pdf
```

### Dry Run (Extract without Publishing)
Use the `--dry-run` flag to safely preview the extracted tasks on the console.
```bash
python main.py path/to/meeting_notes.txt --dry-run
```

### Customizing the Model
You can specify a different Gemini model if required (default is `gemini-3-pro-preview`, which corresponds to Gemini 1.5/3 Pro depending on API mapping).
```bash
python main.py path/to/document.docx --model gemini-3.1-pro-preview
```

## Supported File Formats
- `.txt` (Plain text)
- `.pdf` (Portable Document Format)
- `.docx` / `.doc` (Microsoft Word)
- `.csv` (Comma-separated values)
- `.xls` / `.xlsx` (Microsoft Excel)
