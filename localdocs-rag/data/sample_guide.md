# LocalDocs RAG - Quick Start Guide

## Introduction

LocalDocs RAG is a command-line tool that allows you to ask questions about your local documents and get answers with citations. It supports PDF, DOCX, and Markdown files.

## Features

- **Document Processing**: Automatically extracts text from PDF, DOCX, and Markdown files
- **Semantic Search**: Uses OpenAI embeddings to find relevant information
- **Citation Support**: Provides specific references to source documents
- **Interactive Mode**: Ask multiple questions in a conversation-like interface

## Installation

1. Clone the repository
2. Install dependencies with `pip install -e .`
3. Set up your OpenAI API key in `.env` file
4. Run `localdocs ingest` to process your documents
5. Start asking questions with `localdocs ask "your question"`

## Configuration

The system can be configured using environment variables:

- `LOCALDOCS_DATA_DIR`: Directory containing your documents (default: ./data)
- `LOCALDOCS_CHUNK_SIZE`: Size of text chunks (default: 500)
- `LOCALDOCS_TOP_K`: Number of results to retrieve (default: 3)
- `OPENAI_API_KEY`: Your OpenAI API key (required)

## Best Practices

1. **Organize your documents**: Keep related documents in the same directory
2. **Use descriptive filenames**: This helps with source identification
3. **Ask specific questions**: More specific questions tend to get better answers
4. **Review citations**: Always check the provided sources for accuracy

## Troubleshooting

### Common Issues

- **No index found**: Run `localdocs ingest` first to process your documents
- **API key errors**: Make sure your OpenAI API key is set correctly
- **No documents processed**: Check that your files are in supported formats (PDF, DOCX, MD)

### Performance Tips

- Smaller chunk sizes provide more precise citations but may miss context
- Larger top_k values give more comprehensive answers but slower responses
- Regular re-indexing ensures your index stays up to date with document changes