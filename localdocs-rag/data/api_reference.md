# API Reference

## Command Line Interface

### `localdocs ingest`

Process documents and create vector index.

**Usage:**
```bash
localdocs ingest [PATH] [OPTIONS]
```

**Arguments:**
- `PATH`: Path to documents directory (optional, default: ./data)

**Options:**
- `--force`, `-f`: Force re-indexing even if index exists

**Examples:**
```bash
localdocs ingest                    # Process ./data directory
localdocs ingest /path/to/docs     # Process custom directory
localdocs ingest --force           # Force re-index
```

### `localdocs ask`

Ask questions about your documents.

**Usage:**
```bash
localdocs ask QUESTION [OPTIONS]
```

**Arguments:**
- `QUESTION`: Question to ask about the documents

**Options:**
- `--interactive`, `-i`: Enter interactive mode for multiple questions

**Examples:**
```bash
localdocs ask "How do I deploy the application?"
localdocs ask "What are the system requirements?" --interactive
```

### `localdocs status`

Show index status and statistics.

**Usage:**
```bash
localdocs status
```

**Output:**
- Index status (loaded/not found)
- Vector count
- Total documents and chunks
- Embedding model information
- Creation and update timestamps
- Configuration settings

### `localdocs config`

Show current configuration.

**Usage:**
```bash
localdocs config
```

**Output:**
- All configuration values
- API key status
- Directory paths
- Model settings

## Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LOCALDOCS_DATA_DIR` | Documents directory | ./data |
| `LOCALDOCS_INDEX_DIR` | Index storage directory | ./.localdocs |
| `LOCALDOCS_CHUNK_SIZE` | Text chunk size | 500 |
| `LOCALDOCS_CHUNK_OVERLAP` | Chunk overlap | 50 |
| `LOCALDOCS_TOP_K` | Results to retrieve | 3 |
| `LOCALDOCS_MAX_TOKENS` | Max LLM response tokens | 1000 |
| `OPENAI_API_KEY` | OpenAI API key | Required |

### Configuration File

Create a `.env` file in your project directory:

```bash
# API Configuration
OPENAI_API_KEY=sk-your-api-key-here

# Paths
LOCALDOCS_DATA_DIR=./data
LOCALDOCS_INDEX_DIR=./.localdocs

# Processing
LOCALDOCS_CHUNK_SIZE=500
LOCALDOCS_CHUNK_OVERLAP=50

# Retrieval
LOCALDOCS_TOP_K=3
LOCALDOCS_MAX_TOKENS=1000
```

## Supported File Formats

### PDF Files (.pdf)
- Text extraction with page numbers
- Metadata preservation
- Table and image content (text only)

### Microsoft Word (.docx)
- Full text extraction
- Formatting preservation
- Embedded content handling

### Markdown (.md)
- Complete markdown parsing
- Code blocks and formatting
- Link and reference extraction

## Error Codes

| Code | Description | Solution |
|------|-------------|----------|
| 1 | Configuration error | Check API key and settings |
| 1 | No documents found | Verify document directory |
| 1 | Index not found | Run `localdocs ingest` first |
| 0 | Success | Operation completed |

## Response Format

### Question Response Structure

```python
{
    "question": "Your question",
    "answer": "Generated answer with citations",
    "sources": [
        {
            "source_num": 1,
            "file_name": "document.pdf",
            "file_path": "/path/to/document.pdf",
            "file_type": "pdf",
            "page": 5,
            "chunk_id": 12,
            "content_preview": "Relevant text excerpt..."
        }
    ]
}
```

### Index Statistics

```python
{
    "status": "Index loaded",
    "vector_count": 1250,
    "total_documents": 15,
    "total_chunks": 1250,
    "embedding_model": "text-embedding-3-small",
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-15T10:30:00"
}
```