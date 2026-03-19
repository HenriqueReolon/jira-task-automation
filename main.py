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
@click.argument('filepath', type=click.Path(exists=True))
@click.option('--model', default='gemini-3-pro-preview', help='The Gemini model version to use for extraction (e.g. gemini-3-pro-preview for 3 Pro equivalent context parsing)')
@click.option('--dry-run', is_flag=True, help='Extract and display tasks without creating them in Jira.')
def main(filepath, model, dry_run):
    """
    Automated Jira Task Creation CLI.
    
    FILEPATH: Path to the input file (PDF, DOCX, TXT, CSV, XLS/XLSX) containing meeting transcripts, docs, etc.
    """
    # Load environment variables
    load_dotenv()
    
    click.echo(f"[*] Reading and processing document: {filepath}")
    try:
        document_text = load_document(filepath)
        click.echo(f"[+] Document loaded successfully. Extracted {len(document_text)} characters.")
    except Exception as e:
        click.secho(f"[-] Failed to load document: {e}", fg="red")
        return

    click.echo(f"[*] Extracting tasks using Gemini model: {model}...")
    try:
        extractor = TaskExtractor(model_name=model)
        tasks = extractor.extract_tasks(document_text)
        
        if not tasks:
            click.secho("[-] No engineering/production tasks were extracted from the document.", fg="yellow")
            return
            
        click.secho(f"[+] Successfully extracted {len(tasks)} tasks.", fg="green")
    except Exception as e:
        click.secho(f"[-] Failed to extract tasks: {e}", fg="red")
        return

    for idx, task in enumerate(tasks, start=1):
        click.echo(f"\n--- Task {idx} ---")
        click.echo(f"Title: {task.title}")
        click.echo(f"Type : {task.issue_type}")
        click.echo(f"Desc : {task.description}")

    if dry_run:
        click.secho("\n[!] Dry run mode enabled. Skipping Jira creation.", fg="yellow")
        return

    click.echo("\n[*] Connecting to Jira...")
    try:
        jira_client = JiraManager()
    except Exception as e:
        click.secho(f"[-] Failed to connect to Jira: {e}", fg="red")
        return

    click.echo("[*] Creating tasks in Jira...")
    success_count = 0
    for task in tasks:
        try:
            issue_key = jira_client.create_task(
                title=task.title,
                description=task.description,
                issue_type=task.issue_type
            )
            click.echo(f"    [+] Created Jira Issue: {issue_key}")
            success_count += 1
        except Exception as e:
            click.secho(f"    [-] Failed to create task '{task.title}': {e}", fg="red")
            
    click.secho(f"\n[+] Operation completed. Created {success_count}/{len(tasks)} tasks successfully.", fg="green")

if __name__ == "__main__":
    main()
