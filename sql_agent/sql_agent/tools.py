from typing import Dict, Any, List
from langchain.tools import BaseTool
from pydantic import Field
import logging
from sql_agent.db import DatabaseManager
from sql_agent.models import TableSchema


logger = logging.getLogger(__name__)


class DescribeTableSchemaTool(BaseTool):
    name: str = "describe_table_schema"
    description: str = """
    Get detailed information about a database table including:
    - Column names and types
    - Sample data (first 5 rows)
    - Row count
    Use this tool to understand the structure and content of tables before writing SQL queries.
    """
    
    db_manager: DatabaseManager = Field(exclude=True)
    
    def __init__(self, db_manager: DatabaseManager, **kwargs):
        super().__init__(db_manager=db_manager, **kwargs)
    
    def _run(self, table_name: str) -> str:
        try:
            logger.info(f"Describing schema for table: {table_name}")
            
            schema = self.db_manager.get_table_schema(table_name)
            
            result = f"Table: {schema.table_name}\n"
            result += f"Total rows: {schema.row_count}\n\n"
            
            result += "Columns:\n"
            for col in schema.columns:
                pk_indicator = " (PRIMARY KEY)" if col["primary_key"] else ""
                null_indicator = " (NULLABLE)" if col["nullable"] else " (NOT NULL)"
                result += f"  - {col['name']}: {col['type']}{pk_indicator}{null_indicator}\n"
            
            if schema.sample_data:
                result += f"\nSample data (first {len(schema.sample_data)} rows):\n"
                
                if schema.sample_data:
                    headers = list(schema.sample_data[0].keys())
                    
                    header_line = " | ".join(f"{h:15}" for h in headers)
                    result += f"{header_line}\n"
                    result += "-" * len(header_line) + "\n"
                    
                    for row in schema.sample_data:
                        row_values = []
                        for header in headers:
                            value = str(row.get(header, ''))
                            if len(value) > 15:
                                value = value[:12] + "..."
                            row_values.append(f"{value:15}")
                        result += " | ".join(row_values) + "\n"
            
            return result
            
        except Exception as e:
            error_msg = f"Error describing table schema: {str(e)}"
            logger.error(error_msg)
            return error_msg


class RunSQLQueryTool(BaseTool):
    name: str = "run_sql_query" 
    description: str = """
    Execute a SELECT SQL query against the database.
    Returns the query results in a formatted table.
    
    IMPORTANT RESTRICTIONS:
    - Only SELECT statements are allowed
    - Maximum 100 rows will be returned
    - Query will be automatically validated for security
    
    Always use describe_table_schema first to understand the table structure.
    """
    
    db_manager: DatabaseManager = Field(exclude=True)
    
    def __init__(self, db_manager: DatabaseManager, **kwargs):
        super().__init__(db_manager=db_manager, **kwargs)
    
    def _run(self, sql_query: str) -> str:
        try:
            logger.info(f"Executing SQL query: {sql_query}")
            
            result = self.db_manager.execute_query(sql_query)
            
            if not result["data"]:
                return f"Query executed successfully but returned no results.\n\nSQL: {result['sql_query']}\nExecution time: {result['execution_time_ms']}ms"
            
            output = f"Query Results ({result['row_count']} rows, {result['execution_time_ms']}ms):\n\n"
            
            if result["data"]:
                headers = list(result["data"][0].keys())
                
                col_widths = {}
                for header in headers:
                    col_widths[header] = max(
                        len(str(header)),
                        max(len(str(row.get(header, ''))) for row in result["data"][:10]),
                        10
                    )
                    col_widths[header] = min(col_widths[header], 20)
                
                header_line = " | ".join(f"{h:{col_widths[h]}}" for h in headers)
                output += header_line + "\n"
                output += "-" * len(header_line) + "\n"
                
                for row in result["data"]:
                    row_values = []
                    for header in headers:
                        value = str(row.get(header, ''))
                        if len(value) > col_widths[header]:
                            value = value[:col_widths[header]-3] + "..."
                        row_values.append(f"{value:{col_widths[header]}}")
                    output += " | ".join(row_values) + "\n"
            
            output += f"\nSQL executed: {result['sql_query']}"
            return output
            
        except Exception as e:
            error_msg = f"Error executing SQL query: {str(e)}"
            logger.error(error_msg)
            return error_msg


class ListTablesTool(BaseTool):
    name: str = "list_tables"
    description: str = """
    List all available tables in the database.
    Use this to discover what data is available for querying.
    """
    
    db_manager: DatabaseManager = Field(exclude=True)
    
    def __init__(self, db_manager: DatabaseManager, **kwargs):
        super().__init__(db_manager=db_manager, **kwargs)
    
    def _run(self) -> str:
        try:
            logger.info("Listing all tables")
            
            db_info = self.db_manager.get_database_info()
            
            if not db_info.tables:
                return "No tables found in the database."
            
            result = f"Available tables ({db_info.total_tables}):\n"
            for i, table in enumerate(db_info.tables, 1):
                result += f"{i}. {table}\n"
            
            result += f"\nDatabase path: {db_info.db_path}"
            return result
            
        except Exception as e:
            error_msg = f"Error listing tables: {str(e)}"
            logger.error(error_msg)
            return error_msg


def create_sql_tools(db_manager: DatabaseManager) -> List[BaseTool]:
    return [
        ListTablesTool(db_manager=db_manager),
        DescribeTableSchemaTool(db_manager=db_manager),
        RunSQLQueryTool(db_manager=db_manager),
    ]