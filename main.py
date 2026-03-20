import os
import click
from dotenv import load_dotenv
import sys

# Ensure src modules can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.document_loader import load_document
from src.task_extractor import TaskExtractor
from src.jira_client import JiraManager

@click.command()
@click.argument('filepaths', type=click.Path(exists=True), nargs=-1, required=True)
@click.option('--model', default='gemini-3-pro-preview', help='The Gemini model version to use for extraction (e.g. gemini-3-pro-preview for 3 Pro equivalent context parsing)')
@click.option('--dry-run', is_flag=True, help='Extract and display tasks without creating them in Jira.')
def main(filepaths, model, dry_run):
    """
    Automated Jira Task Creation CLI.
    
    FILEPATHS: Path to one or more input files (PDF, DOCX, TXT, CSV, XLS/XLSX) containing meeting transcripts, docs, etc.
    """
    # Load environment variables
    load_dotenv()
    
    document_text = ""
    for filepath in filepaths:
        click.echo(f"[*] Reading and processing document: {filepath}")
        try:
            content = load_document(filepath)
            document_text += f"\n\n--- Document: {os.path.basename(filepath)} ---\n\n{content}"
            click.echo(f"[+] Document {os.path.basename(filepath)} loaded successfully. Extracted {len(content)} characters.")
        except Exception as e:
            click.secho(f"[-] Failed to load document {filepath}: {e}", fg="red")
            return

    # Initialize Jira Manager early to get active context
    click.echo("\n[*] Connecting to Jira for context...")
    try:
        jira_client = JiraManager()
        jira_context = jira_client.get_active_context()
        if jira_context:
            click.echo(f"[+] Retrieved active Jira context ({len(jira_context.splitlines())} items found).")
        else:
            click.echo("[-] No active Jira context found or failed to retrieve.")
    except Exception as e:
        click.secho(f"[-] Failed to connect to Jira or retrieve context: {e}", fg="red")
        jira_context = ""

    click.echo(f"\n[*] Extracting tasks using Gemini model: {model}...")
    try:
        extractor = TaskExtractor(model_name=model, jira_context=jira_context)
        document_actions = extractor.extract_tasks(document_text)
        
        if not document_actions or not document_actions.tasks:
            click.secho("[-] No engineering/production tasks were extracted from the document.", fg="yellow")
            return
            
        tasks = document_actions.tasks
        epic_theme = document_actions.epic_theme
        click.secho(f"[+] Successfully extracted {len(tasks)} tasks.", fg="green")
        if epic_theme:
            click.secho(f"[+] Epic Theme identified: {epic_theme}", fg="blue")
    except Exception as e:
        click.secho(f"[-] Failed to extract tasks: {e}", fg="red")
        return

    for idx, task in enumerate(tasks, start=1):
        click.echo(f"\n--- Action {idx}: {task.action} ---")
        click.echo(f"Title: {task.title}")
        click.echo(f"Type : {task.issue_type}")
        click.echo(f"Desc : {task.description}")
        if task.target_issue_key:
            click.echo(f"Target: {task.target_issue_key}")
        if task.dependencies:
            click.echo(f"Deps  : {', '.join(task.dependencies)}")

    if dry_run:
        click.secho("\n[!] Dry run mode enabled. Skipping Jira creation.", fg="yellow")
        return

    click.echo("\n[*] Applying actions in Jira...")
    success_count = 0
    
    epic_key = None
    if epic_theme:
        try:
            epic_key = jira_client.get_or_create_epic(epic_theme)
            click.echo(f"    [+] Linked to Epic: {epic_key} ({epic_theme})")
        except Exception as e:
            click.secho(f"    [-] Failed to get/create Epic '{epic_theme}': {e}", fg="red")

    created_tasks = {} # Map title to Jira Issue Key for dependency linking

    for task in tasks:
        try:
            if task.action == "CREATE":
                issue_key = jira_client.create_task(
                    title=task.title,
                    description=task.description,
                    issue_type=task.issue_type,
                    epic_key=epic_key
                )
                created_tasks[task.title] = issue_key
                click.echo(f"    [+] Created Jira Issue: {issue_key}")
            
            elif task.action == "UPDATE":
                if not task.target_issue_key:
                    click.secho(f"    [-] UPDATE action missing target_issue_key for '{task.title}'", fg="red")
                    continue
                jira_client.add_comment(
                    issue_key=task.target_issue_key,
                    comment=task.description
                )
                created_tasks[task.title] = task.target_issue_key
                click.echo(f"    [+] Added comment to Jira Issue: {task.target_issue_key}")
            
            elif task.action == "SUBTASK":
                if not task.target_issue_key:
                    click.secho(f"    [-] SUBTASK action missing target_issue_key for '{task.title}'", fg="red")
                    continue
                issue_key = jira_client.create_subtask(
                    parent_key=task.target_issue_key,
                    title=task.title,
                    description=task.description
                )
                created_tasks[task.title] = issue_key
                click.echo(f"    [+] Created Sub-task: {issue_key} under {task.target_issue_key}")
                
            success_count += 1
        except Exception as e:
            click.secho(f"    [-] Failed to process '{task.title}': {e}", fg="red")
            
    # Automated Dependency Linking
    click.echo("\n[*] Processing dependencies...")
    for task in tasks:
        task_key = created_tasks.get(task.title) or task.target_issue_key
        if not task_key:
            continue
            
        for dep in task.dependencies:
            # dep might be a title or an issue key
            dep_key = created_tasks.get(dep) or dep
            # Basic heuristic: if it looks like a JIRA key (has a hyphen), use it. 
            # Otherwise we might fail, but it's a best-effort linking.
            if dep_key and '-' in dep_key:
                try:
                    jira_client.create_dependency(source_key=task_key, target_key=dep_key)
                    click.echo(f"    [+] Linked {task_key} Blocks {dep_key}")
                except Exception as e:
                    click.secho(f"    [-] Failed to link {task_key} and {dep_key}: {e}", fg="yellow")
            
    click.secho(f"\n[+] Operation completed. Processed {success_count}/{len(tasks)} actions successfully.", fg="green")

if __name__ == "__main__":
    main()
