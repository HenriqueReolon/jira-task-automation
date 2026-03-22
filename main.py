import os
import click
from dotenv import load_dotenv
import sys

# Ensure src modules can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.document_loader import load_document
from src.task_extractor import TaskExtractor
from src.jira_client import JiraManager
from src.sprint_planner import SprintPlanner

@click.group()
def cli():
    """Automated Jira Task Creation and Sprint Planning CLI."""
    pass

@cli.command()
@click.argument('filepaths', type=click.Path(exists=True), nargs=-1, required=True)
@click.option('--model', default='gemini-3-pro-preview', help='The Gemini model version to use for extraction (e.g. gemini-3-pro-preview for 3 Pro equivalent context parsing)')
@click.option('--dry-run', is_flag=True, help='Extract and display tasks without creating them in Jira.')
def extract(filepaths, model, dry_run):
    """
    Extract tasks from documents and push them to Jira.
    
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

@cli.command(name="plan-sprint")
@click.option('--instructions', required=True, help='Instruction prompt for the sprint or path to a text file.')
@click.option('--board-id', type=int, help='Jira Board ID (will auto-detect if not provided).')
@click.option('--model', default='gemini-3-pro-preview', help='The Gemini model version to use for planning.')
@click.option('--dry-run', is_flag=True, help='Plan the sprint but do not create it in Jira.')
def plan_sprint(instructions, board_id, model, dry_run):
    """
    Analyze current backlog tasks and organize them into a Sprint.
    """
    load_dotenv()
    
    # Read instructions if it's a file
    if os.path.exists(instructions):
        with open(instructions, "r", encoding="utf-8") as f:
            sprint_instructions = f.read()
    else:
        sprint_instructions = instructions
        
    click.echo("\n[*] Connecting to Jira to fetch backlog...")
    try:
        jira_client = JiraManager()
        backlog_tasks = jira_client.get_backlog_tasks(max_results=100)
        
        if not backlog_tasks or backlog_tasks == "No backlog tasks found.":
            click.secho("[-] No available tasks in the backlog to plan.", fg="yellow")
            return
            
        click.echo(f"[+] Retrieved backlog tasks:\n{backlog_tasks}")
    except Exception as e:
        click.secho(f"[-] Failed to fetch backlog: {e}", fg="red")
        return

    click.echo(f"\n[*] Planning Sprint using Gemini model: {model}...")
    try:
        planner = SprintPlanner(model_name=model)
        sprint_plan = planner.plan_sprint(backlog_tasks=backlog_tasks, instructions=sprint_instructions)
        
        if not sprint_plan or not sprint_plan.selected_issues:
            click.secho("[-] No issues were selected for the sprint based on the instructions.", fg="yellow")
            return
            
        click.secho(f"\n[+] Sprint Name: {sprint_plan.sprint_name}", fg="green")
        click.secho(f"[+] Sprint Goal: {sprint_plan.sprint_goal}", fg="blue")
        click.echo("\n[*] Selected Issues:")
        
        issue_keys_to_add = []
        for issue in sprint_plan.selected_issues:
            click.echo(f"    - {issue.issue_key}: {issue.rationale}")
            issue_keys_to_add.append(issue.issue_key)
            
    except Exception as e:
        click.secho(f"[-] Failed to plan sprint: {e}", fg="red")
        return

    if dry_run:
        click.secho("\n[!] Dry run mode enabled. Skipping Jira sprint creation.", fg="yellow")
        return

    click.echo("\n[*] Applying Sprint in Jira...")
    try:
        target_board_id = board_id
        if not target_board_id:
            click.echo("    [*] Auto-detecting Board ID...")
            target_board_id = jira_client.get_board_id()
            click.echo(f"    [+] Detected Board ID: {target_board_id}")
            
        click.echo(f"    [*] Creating Sprint '{sprint_plan.sprint_name}'...")
        sprint_id = jira_client.create_sprint(
            name=sprint_plan.sprint_name,
            goal=sprint_plan.sprint_goal,
            board_id=target_board_id
        )
        click.secho(f"    [+] Created Sprint (ID: {sprint_id})", fg="green")
        
        click.echo(f"    [*] Adding {len(issue_keys_to_add)} issues to Sprint...")
        jira_client.add_issues_to_sprint(sprint_id=sprint_id, issue_keys=issue_keys_to_add)
        click.secho(f"    [+] Successfully added issues to Sprint {sprint_id}.", fg="green")
        
    except Exception as e:
        click.secho(f"    [-] Failed to apply sprint to Jira: {e}", fg="red")

if __name__ == "__main__":
    cli()
