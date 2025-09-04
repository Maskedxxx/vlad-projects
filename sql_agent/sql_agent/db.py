import sqlite3
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import time
from sql_agent.models import TableSchema, DatabaseInfo, SQLValidationResult
from sql_agent.validators import SQLValidator


logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, db_path: str = "app.db"):
        self.db_path = Path(db_path)
        self.validator = SQLValidator()
        self._init_db()
    
    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.commit()
    
    def load_csv(self, csv_path: str, table_name: str) -> Dict[str, Any]:
        csv_file = Path(csv_path)
        
        if not csv_file.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        
        logger.info(f"Loading CSV file: {csv_path} into table: {table_name}")
        
        start_time = time.time()
        
        try:
            df = pd.read_csv(csv_file)
            
            if df.empty:
                raise ValueError("CSV file is empty")
            
            df = self._clean_dataframe(df)
            
            with sqlite3.connect(self.db_path) as conn:
                df.to_sql(table_name, conn, if_exists='replace', index=False)
                
                self._create_indexes(conn, table_name, df.columns.tolist())
                
                conn.execute("VACUUM")
                conn.commit()
            
            load_time = time.time() - start_time
            
            result = {
                "table_name": table_name,
                "rows_loaded": len(df),
                "columns": list(df.columns),
                "load_time_seconds": round(load_time, 2),
                "db_path": str(self.db_path)
            }
            
            logger.info(f"Successfully loaded {len(df)} rows into {table_name}")
            return result
            
        except Exception as e:
            logger.error(f"Error loading CSV: {str(e)}")
            raise
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        df.columns = [col.strip().replace(' ', '_').lower() for col in df.columns]
        
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace('nan', None)
        
        return df
    
    def _create_indexes(self, conn: sqlite3.Connection, table_name: str, columns: List[str]) -> None:
        common_index_patterns = ['id', 'date', 'category', 'type', 'status', 'name']
        
        for col in columns:
            col_lower = col.lower()
            if any(pattern in col_lower for pattern in common_index_patterns):
                try:
                    index_name = f"idx_{table_name}_{col}"
                    conn.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({col})")
                    logger.debug(f"Created index: {index_name}")
                except sqlite3.Error as e:
                    logger.warning(f"Could not create index for {col}: {e}")
    
    def execute_query(self, query: str) -> Dict[str, Any]:
        validation_result = self.validator.validate(query)
        
        if not validation_result.is_valid:
            raise ValueError(f"Invalid SQL query: {validation_result.error_message}")
        
        sanitized_query = validation_result.sanitized_query
        logger.info(f"Executing query: {sanitized_query}")
        
        start_time = time.time()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute(sanitized_query)
                rows = cursor.fetchall()
                
                data = [dict(row) for row in rows]
                
            execution_time = (time.time() - start_time) * 1000
            
            return {
                "sql_query": sanitized_query,
                "data": data,
                "row_count": len(data),
                "execution_time_ms": round(execution_time, 2)
            }
            
        except sqlite3.Error as e:
            logger.error(f"SQL execution error: {str(e)}")
            raise ValueError(f"SQL execution failed: {str(e)}")
    
    def get_table_schema(self, table_name: str) -> TableSchema:
        if not self.table_exists(table_name):
            raise ValueError(f"Table '{table_name}' does not exist")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns_info = cursor.fetchall()
            
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
            sample_rows = cursor.fetchall()
            
            columns = []
            for col_info in columns_info:
                columns.append({
                    "name": col_info[1],
                    "type": col_info[2],
                    "nullable": not col_info[3],
                    "primary_key": bool(col_info[5])
                })
            
            column_names = [col[1] for col in columns_info]
            sample_data = []
            for row in sample_rows:
                sample_data.append({col: row[i] for i, col in enumerate(column_names)})
        
        return TableSchema(
            table_name=table_name,
            columns=columns,
            row_count=row_count,
            sample_data=sample_data
        )
    
    def table_exists(self, table_name: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,)
            )
            return cursor.fetchone() is not None
    
    def list_tables(self) -> List[str]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            return [row[0] for row in cursor.fetchall()]
    
    def get_database_info(self) -> DatabaseInfo:
        tables = self.list_tables()
        return DatabaseInfo(
            db_path=str(self.db_path),
            tables=tables,
            total_tables=len(tables)
        )