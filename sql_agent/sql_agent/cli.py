import os
import logging
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from dotenv import load_dotenv

from sql_agent.db import DatabaseManager
from sql_agent.llm import SQLAgent
from sql_agent.models import QueryResult

# Load environment variables
load_dotenv()

app = typer.Typer(
    name="sql-agent",
    help="AI-powered SQL agent for CSV data analysis",
    add_completion=False
)

console = Console()

# Global state
db_manager: Optional[DatabaseManager] = None
sql_agent: Optional[SQLAgent] = None


def get_db_manager(db_path: str) -> DatabaseManager:
    global db_manager
    if db_manager is None or str(db_manager.db_path) != db_path:
        db_manager = DatabaseManager(db_path)
    return db_manager


def get_sql_agent(
    db_path: str, 
    api_key: Optional[str] = None,
    model: str = "gpt-4"
) -> SQLAgent:
    global sql_agent
    db_mgr = get_db_manager(db_path)
    
    if sql_agent is None:
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise typer.BadParameter("OpenAI API key is required. Set OPENAI_API_KEY environment variable or use --api-key option.")
        
        sql_agent = SQLAgent(
            db_manager=db_mgr,
            api_key=api_key,
            model=model
        )
    return sql_agent


@app.command()
def load(
    csv_path: str = typer.Argument(..., help="Path to the CSV file to load"),
    table_name: str = typer.Option(None, "--table", "-t", help="Name for the table (default: filename without extension)"),
    db_path: str = typer.Option("app.db", "--db", help="Path to SQLite database file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging")
):
    """Load a CSV file into the SQLite database."""
    
    if verbose:
        logging.basicConfig(level=logging.INFO)
    
    if not Path(csv_path).exists():
        console.print(f"[red]Error: CSV file '{csv_path}' not found[/red]")
        raise typer.Exit(1)
    
    if table_name is None:
        table_name = Path(csv_path).stem
    
    try:
        db_mgr = get_db_manager(db_path)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(f"Loading {csv_path}...", total=None)
            result = db_mgr.load_csv(csv_path, table_name)
        
        # Create a results table
        table = Table(title=f"✅ Successfully loaded '{table_name}'")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Table Name", result["table_name"])
        table.add_row("Rows Loaded", str(result["rows_loaded"]))
        table.add_row("Columns", str(len(result["columns"])))
        table.add_row("Load Time", f"{result['load_time_seconds']}s")
        table.add_row("Database", result["db_path"])
        
        console.print(table)
        
        # Show column info
        console.print(f"\n[bold]Columns:[/bold] {', '.join(result['columns'])}")
        
        console.print(f"\n[green]✨ Ready for queries! Use:[/green]")
        console.print(f"   sql-agent ask \"Your question about {table_name}\"")
        
    except Exception as e:
        console.print(f"[red]Error loading CSV: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def ask(
    question: str = typer.Argument(..., help="Question about your data"),
    table_name: Optional[str] = typer.Option(None, "--table", "-t", help="Specific table to query"),
    db_path: str = typer.Option("app.db", "--db", help="Path to SQLite database file"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="OpenAI API key"),
    model: str = typer.Option("gpt-4", "--model", "-m", help="OpenAI model to use"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug mode")
):
    """Ask a question about your data using AI."""
    
    if verbose or debug:
        logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
    
    if not Path(db_path).exists():
        console.print(f"[red]Error: Database '{db_path}' not found. Load data first with 'sql-agent load'[/red]")
        raise typer.Exit(1)
    
    try:
        agent = get_sql_agent(db_path, api_key, model)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("🤔 Analyzing question...", total=None)
            result = agent.ask(question, table_name)
        
        # Display the answer
        console.print(Panel(
            result.answer,
            title="💡 Answer",
            border_style="green"
        ))
        
        # Show query details if data was returned
        if result.data and debug:
            console.print(f"\n[dim]SQL Query: {result.sql_query}[/dim]")
            console.print(f"[dim]Execution time: {result.execution_time_ms}ms[/dim]")
            console.print(f"[dim]Rows returned: {result.row_count}[/dim]")
        
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        if debug:
            console.print_exception()
        raise typer.Exit(1)


@app.command()
def schema(
    table_name: Optional[str] = typer.Argument(None, help="Table name to describe (optional)"),
    db_path: str = typer.Option("app.db", "--db", help="Path to SQLite database file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging")
):
    """Show database schema information."""
    
    if verbose:
        logging.basicConfig(level=logging.INFO)
    
    if not Path(db_path).exists():
        console.print(f"[red]Error: Database '{db_path}' not found[/red]")
        raise typer.Exit(1)
    
    try:
        db_mgr = get_db_manager(db_path)
        
        if table_name:
            # Show specific table schema
            if not db_mgr.table_exists(table_name):
                console.print(f"[red]Error: Table '{table_name}' not found[/red]")
                raise typer.Exit(1)
            
            schema = db_mgr.get_table_schema(table_name)
            
            # Table info
            info_table = Table(title=f"📊 Table: {schema.table_name}")
            info_table.add_column("Property", style="cyan")
            info_table.add_column("Value", style="green")
            info_table.add_row("Total Rows", str(schema.row_count))
            info_table.add_row("Columns", str(len(schema.columns)))
            console.print(info_table)
            
            # Columns
            cols_table = Table(title="Columns")
            cols_table.add_column("Name", style="bold blue")
            cols_table.add_column("Type", style="yellow")
            cols_table.add_column("Nullable", style="magenta")
            cols_table.add_column("Primary Key", style="red")
            
            for col in schema.columns:
                cols_table.add_row(
                    col["name"],
                    col["type"],
                    "Yes" if col["nullable"] else "No",
                    "Yes" if col["primary_key"] else "No"
                )
            
            console.print(cols_table)
            
            # Sample data
            if schema.sample_data:
                console.print(f"\n[bold]Sample Data (first {len(schema.sample_data)} rows):[/bold]")
                sample_table = Table()
                
                headers = list(schema.sample_data[0].keys())
                for header in headers:
                    sample_table.add_column(header, overflow="fold")
                
                for row in schema.sample_data:
                    values = [str(row.get(h, '')) for h in headers]
                    sample_table.add_row(*values)
                
                console.print(sample_table)
        else:
            # Show all tables
            db_info = db_mgr.get_database_info()
            
            if not db_info.tables:
                console.print("[yellow]No tables found in database[/yellow]")
                return
            
            tables_table = Table(title=f"📚 Database: {db_info.db_path}")
            tables_table.add_column("Table Name", style="bold blue")
            tables_table.add_column("Row Count", style="green")
            
            for table in db_info.tables:
                try:
                    schema = db_mgr.get_table_schema(table)
                    tables_table.add_row(table, str(schema.row_count))
                except:
                    tables_table.add_row(table, "Unknown")
            
            console.print(tables_table)
            console.print(f"\n[green]💡 Use 'sql-agent schema <table_name>' for detailed info[/green]")
    
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def version():
    """Show version information."""
    console.print("sql-agent v0.1.0")
    console.print("AI-powered SQL agent for CSV data analysis")


if __name__ == "__main__":
    app()