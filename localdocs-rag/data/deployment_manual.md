# Deployment Manual

## System Requirements

- Python 3.12 or higher
- OpenAI API key
- At least 2GB RAM for processing large documents
- 1GB disk space for indexes and embeddings

## Environment Setup

### Local Development

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install the package:
   ```bash
   pip install -e .
   ```

3. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your OpenAI API key
   ```

### Production Deployment

For production use, consider the following setup:

1. **Server Requirements**:
   - Ubuntu 20.04+ or CentOS 7+
   - Python 3.12
   - systemd for service management

2. **Installation Steps**:
   ```bash
   # Install system dependencies
   sudo apt update
   sudo apt install python3.12 python3.12-venv

   # Create application user
   sudo useradd -m -s /bin/bash localdocs

   # Deploy application
   sudo -u localdocs git clone <repository>
   sudo -u localdocs python3.12 -m venv /home/localdocs/venv
   sudo -u localdocs /home/localdocs/venv/bin/pip install -e .
   ```

3. **Configuration**:
   ```bash
   # Create production config
   sudo -u localdocs cp .env.example /home/localdocs/.env
   # Configure with production API keys and paths
   ```

## Security Considerations

- Store API keys in environment variables, never in code
- Use dedicated service accounts for production deployments
- Implement rate limiting if exposing via API
- Regularly rotate API keys
- Monitor API usage to detect anomalies

## Monitoring and Logging

The application logs important events including:
- Document processing status
- Search queries and response times
- API usage statistics
- Error conditions

Configure log rotation and monitoring alerts for production systems.

## Backup and Recovery

1. **Data Backup**:
   - Index files (`.localdocs/`)
   - Source documents (`data/`)
   - Configuration files (`.env`)

2. **Recovery Process**:
   - Restore source documents
   - Restore configuration
   - Re-run `localdocs ingest` to rebuild indexes

## Performance Tuning

### Memory Optimization
- Adjust `chunk_size` based on document types
- Monitor RAM usage during indexing
- Consider batch processing for large document sets

### Speed Optimization
- Use SSD storage for index files
- Increase `top_k` only when necessary
- Cache frequently accessed embeddings