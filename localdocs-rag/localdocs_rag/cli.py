"""CLI interface for LocalDocs RAG using Typer."""

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .config import load_config
from .document_processor import DocumentProcessor
from .rag_chain import RAGChain
from .vector_store import VectorStore

# Initialize Typer app
app = typer.Typer(
    name="localdocs",
    help="🔍 LocalDocs RAG CLI - Question answering for local documents with citations",
    add_completion=False,
)

console = Console()


def _get_components():
    """Initialize and return main components."""
    try:
        config = load_config()
        config.ensure_directories()
        
        processor = DocumentProcessor(config)
        vector_store = VectorStore(config)
        
        return config, processor, vector_store
    except Exception as e:
        console.print(f"[red]❌ Configuration error: {str(e)}[/red]")
        console.print("[yellow]💡 Make sure you have set OPENAI_API_KEY in your .env file[/yellow]")
        raise typer.Exit(1)


@app.command()
def ingest(
    path: Optional[Path] = typer.Argument(
        None, 
        help="Path to documents directory (default: ./data)"
    ),
    force: bool = typer.Option(
        False, 
        "--force", 
        "-f", 
        help="Force re-indexing even if index exists"
    )
) -> None:
    """
    📥 Ingest documents and create vector index.
    
    Processes all supported documents (PDF, DOCX, MD) in the specified directory
    and creates a FAISS vector index for semantic search.
    """
    console.print(Panel(
        "🔧 LocalDocs RAG - Document Ingestion",
        style="bold blue"
    ))
    
    config, processor, vector_store = _get_components()
    
    # Use provided path or default from config
    target_path = path or config.data_dir
    
    # Check if index already exists
    if not force and vector_store.index_path.exists():
        console.print("[yellow]⚠️  Index already exists. Use --force to re-index.[/yellow]")
        
        if not typer.confirm("Do you want to continue anyway?"):
            raise typer.Exit(0)
    
    # Process documents
    console.print(f"[blue]📂 Processing documents from: {target_path}[/blue]")
    documents = processor.process_directory(target_path)
    
    if not documents:
        console.print("[red]❌ No documents found or processed[/red]")
        raise typer.Exit(1)
    
    # Create vector index
    console.print("[blue]🔧 Creating vector index...[/blue]")
    vector_store.create_index(documents)
    
    # Display statistics
    stats = processor.get_document_stats(documents)
    _display_ingest_stats(stats)
    
    console.print("[green]✅ Ingestion completed successfully![/green]")


@app.command()
def ask(
    question: str = typer.Argument(..., help="Question to ask about the documents"),
    interactive: bool = typer.Option(
        False,
        "--interactive", 
        "-i", 
        help="Enter interactive mode for multiple questions"
    )
) -> None:
    """
    ❓ Ask questions about your documents.
    
    Performs semantic search and generates answers with citations from your
    indexed documents.
    """
    config, processor, vector_store = _get_components()
    
    # Load existing index
    if not vector_store.load_index():
        console.print("[red]❌ No index found. Run 'localdocs ingest' first.[/red]")
        raise typer.Exit(1)
    
    # Initialize RAG chain
    rag_chain = RAGChain(config, vector_store)
    
    if interactive:
        _interactive_mode(rag_chain)
    else:
        # Single question mode
        console.print(Panel(
            "🤖 LocalDocs RAG - Question Answering",
            style="bold blue"
        ))
        
        response = rag_chain.ask(question)
        rag_chain.display_response(response)


@app.command()
def status() -> None:
    """
    📊 Show index status and statistics.
    """
    console.print(Panel(
        "📊 LocalDocs RAG - Index Status",
        style="bold blue"
    ))
    
    config, processor, vector_store = _get_components()
    
    # Try to load index
    index_loaded = vector_store.load_index()
    
    # Get index statistics
    stats = vector_store.get_index_stats()
    
    # Create status table
    table = Table(title="Index Information", show_header=True)
    table.add_column("Property", style="cyan", no_wrap=True)
    table.add_column("Value", style="green")
    
    table.add_row("Status", "✅ Loaded" if index_loaded else "❌ Not found")
    
    if index_loaded and isinstance(stats, dict):
        table.add_row("Vector Count", str(stats.get("vector_count", 0)))
        table.add_row("Total Documents", str(stats.get("total_documents", 0)))
        table.add_row("Total Chunks", str(stats.get("total_chunks", 0)))
        table.add_row("Embedding Model", stats.get("embedding_model", "N/A"))
        
        if stats.get("created_at"):
            table.add_row("Created", stats["created_at"][:19].replace("T", " "))
        if stats.get("updated_at"):
            table.add_row("Last Updated", stats["updated_at"][:19].replace("T", " "))
    
    # Add configuration info
    table.add_row("", "")
    table.add_row("Data Directory", str(config.data_dir))
    table.add_row("Index Directory", str(config.index_dir))
    table.add_row("Chunk Size", str(config.chunk_size))
    table.add_row("Top K Results", str(config.top_k))
    
    console.print(table)
    
    if not index_loaded:
        console.print("\n[yellow]💡 Run 'localdocs ingest' to create an index[/yellow]")


def _interactive_mode(rag_chain: RAGChain) -> None:
    """Enter interactive question-answering mode."""
    console.print(Panel(
        "🤖 Interactive Mode - Type 'exit' or 'quit' to leave",
        style="bold green"
    ))
    
    while True:
        try:
            # Get question from user
            question = typer.prompt("\n❓ Your question")
            
            if question.lower() in ["exit", "quit", "q"]:
                console.print("[blue]👋 Goodbye![/blue]")
                break
            
            if not question.strip():
                continue
            
            # Get and display answer
            response = rag_chain.ask(question)
            rag_chain.display_response(response)
            
        except KeyboardInterrupt:
            console.print("\n[blue]👋 Goodbye![/blue]")
            break
        except EOFError:
            break


def _display_ingest_stats(stats: dict) -> None:
    """Display ingestion statistics."""
    if not stats:
        return
    
    table = Table(title="Ingestion Summary", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="green", justify="right")
    
    table.add_row("Total Documents", str(stats.get("total_documents", 0)))
    table.add_row("Total Chunks", str(stats.get("total_chunks", 0)))
    
    if stats.get("pdf_files", 0) > 0:
        table.add_row("PDF Files", str(stats["pdf_files"]))
    if stats.get("docx_files", 0) > 0:
        table.add_row("DOCX Files", str(stats["docx_files"]))
    if stats.get("md_files", 0) > 0:
        table.add_row("Markdown Files", str(stats["md_files"]))
    
    if stats.get("avg_chunk_length"):
        table.add_row("Avg Chunk Length", f"{stats['avg_chunk_length']} chars")
    
    console.print(table)


@app.command()
def config() -> None:
    """
    ⚙️ Show current configuration.
    """
    console.print(Panel(
        "⚙️ LocalDocs RAG - Configuration",
        style="bold blue"
    ))
    
    try:
        cfg = load_config()
        
        table = Table(title="Current Configuration", show_header=True)
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Data Directory", str(cfg.data_dir))
        table.add_row("Index Directory", str(cfg.index_dir))
        table.add_row("Chunk Size", str(cfg.chunk_size))
        table.add_row("Chunk Overlap", str(cfg.chunk_overlap))
        table.add_row("Top K Results", str(cfg.top_k))
        table.add_row("Max Tokens", str(cfg.max_tokens))
        table.add_row("Model Name", cfg.model_name)
        table.add_row("Temperature", str(cfg.temperature))
        table.add_row("Embedding Model", cfg.embedding_model)
        table.add_row("OpenAI API Key", "✅ Set" if cfg.openai_api_key else "❌ Not set")
        
        console.print(table)
        
        if not cfg.openai_api_key:
            console.print("\n[yellow]⚠️  OpenAI API key not found![/yellow]")
            console.print("[yellow]💡 Set OPENAI_API_KEY in your .env file[/yellow]")
            
    except Exception as e:
        console.print(f"[red]❌ Configuration error: {str(e)}[/red]")


@app.callback()
def main(
    version: bool = typer.Option(
        False, 
        "--version", 
        help="Show version information"
    )
) -> None:
    """
    🔍 LocalDocs RAG CLI - Question answering for local documents with citations.
    """
    if version:
        from . import __version__
        console.print(f"LocalDocs RAG CLI v{__version__}")
        raise typer.Exit()


if __name__ == "__main__":
    app()