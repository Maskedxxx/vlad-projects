"""Vector store implementation using FAISS and OpenAI embeddings."""

import json
import pickle
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn

from .config import LocalDocsConfig, IndexMetadata

console = Console()


class VectorStore:
    """FAISS-based vector store with OpenAI embeddings."""
    
    def __init__(self, config: LocalDocsConfig):
        self.config = config
        self.embeddings = OpenAIEmbeddings(
            model=config.embedding_model,
            api_key=config.openai_api_key
        )
        self.vectorstore: Optional[FAISS] = None
        self.metadata_path = config.index_dir / "metadata.json"
        self.index_path = config.index_dir / "faiss_index"
        
    def create_index(self, documents: List[Document]) -> None:
        """Create FAISS index from documents."""
        if not documents:
            console.print("[yellow]No documents to index[/yellow]")
            return
            
        console.print(f"[blue]🔧 Creating embeddings for {len(documents)} chunks...[/blue]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            console=console,
        ) as progress:
            # Create FAISS index with progress tracking
            task = progress.add_task("Generating embeddings...", total=len(documents))
            
            try:
                # Create vectorstore from documents
                self.vectorstore = FAISS.from_documents(
                    documents=documents,
                    embedding=self.embeddings,
                )
                
                progress.update(task, completed=len(documents))
                
                # Save the index
                self._save_index()
                
                # Save metadata
                self._save_metadata(documents)
                
                console.print(f"[green]✅ Index created successfully![/green]")
                console.print(f"[green]📊 {len(documents)} chunks indexed[/green]")
                
            except Exception as e:
                console.print(f"[red]❌ Failed to create index: {str(e)}[/red]")
                raise
    
    def load_index(self) -> bool:
        """Load existing FAISS index from disk."""
        if not self.index_path.exists():
            console.print("[yellow]No existing index found[/yellow]")
            return False
            
        try:
            self.vectorstore = FAISS.load_local(
                folder_path=str(self.index_path),
                embeddings=self.embeddings,
                allow_dangerous_deserialization=True
            )
            
            console.print("[green]✅ Index loaded successfully[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]❌ Failed to load index: {str(e)}[/red]")
            return False
    
    def search(self, query: str, k: Optional[int] = None) -> List[Tuple[Document, float]]:
        """Search for similar documents."""
        if not self.vectorstore:
            raise ValueError("No index loaded. Run 'ingest' command first.")
            
        k = k or self.config.top_k
        
        try:
            # Perform similarity search with scores
            results = self.vectorstore.similarity_search_with_score(
                query=query,
                k=k
            )
            
            console.print(f"[blue]🔍 Found {len(results)} relevant chunks[/blue]")
            return results
            
        except Exception as e:
            console.print(f"[red]❌ Search failed: {str(e)}[/red]")
            return []
    
    def add_documents(self, documents: List[Document]) -> None:
        """Add new documents to existing index."""
        if not documents:
            return
            
        if not self.vectorstore:
            console.print("[yellow]No existing index. Creating new one...[/yellow]")
            self.create_index(documents)
            return
            
        console.print(f"[blue]➕ Adding {len(documents)} new chunks to index...[/blue]")
        
        try:
            # Add documents to existing vectorstore
            self.vectorstore.add_documents(documents)
            
            # Save updated index
            self._save_index()
            
            # Update metadata
            self._update_metadata(documents)
            
            console.print(f"[green]✅ Added {len(documents)} chunks to index[/green]")
            
        except Exception as e:
            console.print(f"[red]❌ Failed to add documents: {str(e)}[/red]")
            raise
    
    def get_index_stats(self) -> Dict[str, any]:
        """Get statistics about the current index."""
        if not self.vectorstore:
            return {"status": "No index loaded"}
            
        # Load metadata if available
        metadata = self._load_metadata()
        
        stats = {
            "status": "Index loaded",
            "vector_count": self.vectorstore.index.ntotal if self.vectorstore.index else 0,
            "embedding_model": self.config.embedding_model,
        }
        
        if metadata:
            stats.update({
                "total_documents": metadata.total_documents,
                "total_chunks": metadata.total_chunks,
                "created_at": metadata.created_at,
                "updated_at": metadata.updated_at,
            })
        
        return stats
    
    def _save_index(self) -> None:
        """Save FAISS index to disk."""
        if not self.vectorstore:
            return
            
        # Ensure directory exists
        self.config.index_dir.mkdir(parents=True, exist_ok=True)
        
        # Save FAISS index
        self.vectorstore.save_local(str(self.index_path))
    
    def _save_metadata(self, documents: List[Document]) -> None:
        """Save index metadata."""
        # Count unique documents
        unique_sources = set()
        for doc in documents:
            source = doc.metadata.get("source", "unknown")
            unique_sources.add(source)
        
        metadata = IndexMetadata(
            total_documents=len(unique_sources),
            total_chunks=len(documents),
            embedding_model=self.config.embedding_model,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )
        
        # Save metadata as JSON
        with open(self.metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata.model_dump(), f, indent=2, ensure_ascii=False)
    
    def _update_metadata(self, new_documents: List[Document]) -> None:
        """Update existing metadata with new documents."""
        metadata = self._load_metadata()
        
        if metadata:
            # Count new unique documents
            existing_sources = set()
            new_sources = set()
            
            for doc in new_documents:
                source = doc.metadata.get("source", "unknown")
                new_sources.add(source)
            
            metadata.total_documents += len(new_sources - existing_sources)
            metadata.total_chunks += len(new_documents)
            metadata.updated_at = datetime.now().isoformat()
        else:
            # Create new metadata
            metadata = IndexMetadata(
                total_documents=len(set(doc.metadata.get("source", "unknown") for doc in new_documents)),
                total_chunks=len(new_documents),
                embedding_model=self.config.embedding_model,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
            )
        
        # Save updated metadata
        with open(self.metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata.model_dump(), f, indent=2, ensure_ascii=False)
    
    def _load_metadata(self) -> Optional[IndexMetadata]:
        """Load index metadata from disk."""
        if not self.metadata_path.exists():
            return None
            
        try:
            with open(self.metadata_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return IndexMetadata(**data)
        except Exception:
            return None