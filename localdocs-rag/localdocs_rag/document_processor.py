"""Document processing module using LangChain loaders and text splitters."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    UnstructuredMarkdownLoader,
    Docx2txtLoader,
)
from langchain_core.documents import Document
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import LocalDocsConfig, DocumentMetadata

console = Console()


class DocumentProcessor:
    """Process documents using LangChain loaders and splitters."""
    
    def __init__(self, config: LocalDocsConfig):
        self.config = config
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""],
        )
        
    def load_document(self, file_path: Path) -> List[Document]:
        """Load a single document using appropriate LangChain loader."""
        file_extension = file_path.suffix.lower()
        
        try:
            if file_extension == ".pdf":
                loader = PyPDFLoader(str(file_path))
                documents = loader.load()
                
                # Add page numbers to metadata
                for i, doc in enumerate(documents):
                    doc.metadata["page"] = i + 1
                    doc.metadata["source"] = str(file_path)
                    doc.metadata["file_type"] = "pdf"
                    
            elif file_extension == ".docx":
                loader = Docx2txtLoader(str(file_path))
                documents = loader.load()
                
                # DOCX doesn't have page numbers, so we don't add them
                for doc in documents:
                    doc.metadata["source"] = str(file_path)
                    doc.metadata["file_type"] = "docx"
                    
            elif file_extension == ".md":
                loader = UnstructuredMarkdownLoader(str(file_path))
                documents = loader.load()
                
                for doc in documents:
                    doc.metadata["source"] = str(file_path)
                    doc.metadata["file_type"] = "md"
                    
            else:
                console.print(f"[yellow]Unsupported file type: {file_extension}[/yellow]")
                return []
                
            console.print(f"[green]✓[/green] Loaded {len(documents)} pages from {file_path.name}")
            return documents
            
        except Exception as e:
            console.print(f"[red]✗[/red] Failed to load {file_path.name}: {str(e)}")
            return []
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """Split documents into chunks using RecursiveCharacterTextSplitter."""
        if not documents:
            return []
            
        chunks = self.text_splitter.split_documents(documents)
        
        # Add chunk metadata
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_id"] = i
            chunk.metadata["total_chunks"] = len(chunks)
            chunk.metadata["created_at"] = datetime.now().isoformat()
            
        return chunks
    
    def process_directory(self, directory: Optional[Path] = None) -> List[Document]:
        """Process all supported documents in a directory."""
        target_dir = directory or self.config.data_dir
        
        if not target_dir.exists():
            console.print(f"[red]Directory not found: {target_dir}[/red]")
            return []
            
        # Find all supported files
        supported_extensions = {".pdf", ".docx", ".md"}
        files = [
            f for f in target_dir.rglob("*")
            if f.suffix.lower() in supported_extensions and f.is_file()
        ]
        
        if not files:
            console.print(f"[yellow]No supported documents found in {target_dir}[/yellow]")
            return []
            
        all_chunks = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Processing documents...", total=len(files))
            
            for file_path in files:
                progress.update(task, description=f"Processing {file_path.name}...")
                
                # Load document
                documents = self.load_document(file_path)
                
                if documents:
                    # Split into chunks
                    chunks = self.split_documents(documents)
                    all_chunks.extend(chunks)
                    
                progress.advance(task)
        
        console.print(f"\n[green]📄 Processed {len(files)} documents[/green]")
        console.print(f"[green]🔗 Created {len(all_chunks)} chunks[/green]")
        
        return all_chunks
    
    def get_document_stats(self, documents: List[Document]) -> Dict[str, int]:
        """Get statistics about processed documents."""
        if not documents:
            return {}
            
        stats = {
            "total_documents": len(set(doc.metadata.get("source", "") for doc in documents)),
            "total_chunks": len(documents),
            "pdf_files": len([doc for doc in documents if doc.metadata.get("file_type") == "pdf"]),
            "docx_files": len([doc for doc in documents if doc.metadata.get("file_type") == "docx"]),
            "md_files": len([doc for doc in documents if doc.metadata.get("file_type") == "md"]),
        }
        
        # Calculate average chunk length
        if documents:
            total_length = sum(len(doc.page_content) for doc in documents)
            stats["avg_chunk_length"] = total_length // len(documents)
        
        return stats