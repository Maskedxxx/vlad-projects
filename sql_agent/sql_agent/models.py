from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TableSchema(BaseModel):
    table_name: str
    columns: List[Dict[str, Any]]
    row_count: int
    sample_data: List[Dict[str, Any]]


class QueryRequest(BaseModel):
    question: str
    table_name: Optional[str] = None
    max_rows: int = Field(default=100, le=100)


class QueryResult(BaseModel):
    sql_query: str
    data: List[Dict[str, Any]]
    row_count: int
    execution_time_ms: float
    answer: str


class SQLValidationResult(BaseModel):
    is_valid: bool
    error_message: Optional[str] = None
    sanitized_query: Optional[str] = None


class DatabaseInfo(BaseModel):
    db_path: str
    tables: List[str]
    total_tables: int