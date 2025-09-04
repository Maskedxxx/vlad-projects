"""RAG chain implementation for question answering with citations."""

import re
from typing import Dict, List, Tuple, Optional

from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from .config import LocalDocsConfig
from .vector_store import VectorStore

console = Console()


class RAGChain:
    """RAG chain for question answering with citations."""
    
    # Custom prompt template for citation-aware responses
    CITATION_PROMPT_TEMPLATE = """You are a helpful assistant that answers questions based on the provided context. 
You must follow these rules strictly:

1. ONLY use information from the provided context to answer the question
2. If the context doesn't contain enough information to answer the question, say so clearly
3. Always provide specific citations for your statements
4. Format citations as [Source X] where X is the source number
5. Be concise and accurate

Context:
{context}

Question: {question}

Instructions:
- Base your answer ONLY on the provided context
- Include relevant citations [Source 1], [Source 2], etc.
- If you cannot find relevant information in the context, state that clearly
- Keep your answer focused and well-structured

Answer:"""

    def __init__(self, config: LocalDocsConfig, vector_store: VectorStore):
        self.config = config
        self.vector_store = vector_store
        
        # Initialize OpenAI LLM
        self.llm = ChatOpenAI(
            model_name=config.model_name,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            api_key=config.openai_api_key,
        )
        
        # Create custom prompt
        self.prompt = PromptTemplate(
            template=self.CITATION_PROMPT_TEMPLATE,
            input_variables=["context", "question"]
        )
        
        # Initialize retrieval chain
        self._setup_chain()
    
    def _setup_chain(self) -> None:
        """Setup the retrieval QA chain."""
        if not self.vector_store.vectorstore:
            raise ValueError("Vector store not initialized. Run 'ingest' command first.")
        
        # Create retriever
        retriever = self.vector_store.vectorstore.as_retriever(
            search_kwargs={"k": self.config.top_k}
        )
        
        # Create RetrievalQA chain
        self.chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=True,
            chain_type_kwargs={"prompt": self.prompt}
        )
    
    def ask(self, question: str) -> Dict[str, any]:
        """Ask a question and get an answer with citations."""
        if not self.chain:
            raise ValueError("RAG chain not initialized")
        
        console.print(f"[blue]❓ Question:[/blue] {question}")
        console.print("[blue]🔍 Searching for relevant information...[/blue]")
        
        try:
            # Get answer from chain
            result = self.chain.invoke({"query": question})
            
            # Extract answer and source documents
            answer = result["result"]
            source_docs = result["source_documents"]
            
            # Process and format response
            formatted_response = self._format_response(answer, source_docs, question)
            
            return {
                "question": question,
                "answer": answer,
                "sources": self._extract_sources(source_docs),
                "formatted_response": formatted_response,
                "raw_sources": source_docs,
            }
            
        except Exception as e:
            console.print(f"[red]❌ Error processing question: {str(e)}[/red]")
            return {
                "question": question,
                "answer": f"Error: {str(e)}",
                "sources": [],
                "formatted_response": f"❌ Error: {str(e)}",
                "raw_sources": [],
            }
    
    def _format_response(self, answer: str, source_docs: List[Document], question: str) -> str:
        """Format the response with proper citations and sources."""
        # Create formatted response
        response_parts = []
        
        # Add the answer
        response_parts.append("## 📝 Answer")
        response_parts.append(answer)
        response_parts.append("")
        
        # Add sources section
        if source_docs:
            response_parts.append("## 📚 Sources")
            response_parts.append("")
            
            for i, doc in enumerate(source_docs, 1):
                source_info = self._format_source_info(doc, i)
                response_parts.append(source_info)
                response_parts.append("")
        
        return "\n".join(response_parts)
    
    def _format_source_info(self, doc: Document, source_num: int) -> str:
        """Format source information for display."""
        metadata = doc.metadata
        source_path = metadata.get("source", "Unknown")
        file_type = metadata.get("file_type", "unknown")
        
        # Get file name from path
        file_name = source_path.split("/")[-1] if "/" in source_path else source_path
        
        # Create file type emoji
        emoji_map = {
            "pdf": "📄",
            "docx": "📝",
            "md": "📋",
        }
        emoji = emoji_map.get(file_type, "📄")
        
        # Build source string
        source_parts = [f"**[Source {source_num}]** {emoji} {file_name}"]
        
        # Add page if available
        if metadata.get("page"):
            source_parts.append(f"(page {metadata['page']})")
        
        # Add chunk info if available
        if metadata.get("chunk_id") is not None:
            chunk_id = metadata.get("chunk_id", 0)
            total_chunks = metadata.get("total_chunks", 0)
            source_parts.append(f"(chunk {chunk_id + 1}/{total_chunks})")
        
        source_line = " ".join(source_parts)
        
        # Add content preview (first 200 chars)
        content_preview = doc.page_content.strip()
        if len(content_preview) > 200:
            content_preview = content_preview[:200] + "..."
        
        return f"{source_line}\n> {content_preview}"
    
    def _extract_sources(self, source_docs: List[Document]) -> List[Dict[str, any]]:
        """Extract source information as structured data."""
        sources = []
        
        for i, doc in enumerate(source_docs):
            metadata = doc.metadata
            
            source_info = {
                "source_num": i + 1,
                "file_name": metadata.get("source", "Unknown").split("/")[-1],
                "file_path": metadata.get("source", "Unknown"),
                "file_type": metadata.get("file_type", "unknown"),
                "page": metadata.get("page"),
                "chunk_id": metadata.get("chunk_id"),
                "total_chunks": metadata.get("total_chunks"),
                "content_preview": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                "full_content": doc.page_content,
            }
            
            sources.append(source_info)
        
        return sources
    
    def display_response(self, response: Dict[str, any]) -> None:
        """Display formatted response using Rich."""
        # Display question
        console.print(Panel(
            response["question"],
            title="❓ Question",
            border_style="blue"
        ))
        
        # Display answer
        console.print(Panel(
            Markdown(response["answer"]),
            title="📝 Answer",
            border_style="green"
        ))
        
        # Display sources
        if response["sources"]:
            sources_text = []
            for source in response["sources"]:
                emoji_map = {"pdf": "📄", "docx": "📝", "md": "📋"}
                emoji = emoji_map.get(source["file_type"], "📄")
                
                source_line = f"**[Source {source['source_num']}]** {emoji} {source['file_name']}"
                
                if source["page"]:
                    source_line += f" (page {source['page']})"
                
                if source["chunk_id"] is not None:
                    chunk_id = source["chunk_id"]
                    total_chunks = source["total_chunks"]
                    source_line += f" (chunk {chunk_id + 1}/{total_chunks})"
                
                source_line += f"\n> {source['content_preview']}"
                sources_text.append(source_line)
            
            console.print(Panel(
                Markdown("\n\n".join(sources_text)),
                title="📚 Sources",
                border_style="yellow"
            ))
    
    def batch_ask(self, questions: List[str]) -> List[Dict[str, any]]:
        """Ask multiple questions and return results."""
        results = []
        
        console.print(f"[blue]🔄 Processing {len(questions)} questions...[/blue]")
        
        for i, question in enumerate(questions, 1):
            console.print(f"\n[blue]Question {i}/{len(questions)}:[/blue]")
            result = self.ask(question)
            results.append(result)
        
        return results