import re
import sqlparse
from sqlparse.sql import Statement
from sqlparse.tokens import Keyword, DML
from typing import List, Set
from sql_agent.models import SQLValidationResult


class SQLValidator:
    ALLOWED_KEYWORDS: Set[str] = {
        'SELECT', 'FROM', 'WHERE', 'GROUP BY', 'HAVING', 'ORDER BY', 
        'LIMIT', 'OFFSET', 'AS', 'AND', 'OR', 'NOT', 'IN', 'EXISTS',
        'BETWEEN', 'LIKE', 'IS', 'NULL', 'DISTINCT', 'COUNT', 'SUM', 
        'AVG', 'MIN', 'MAX', 'JOIN', 'LEFT JOIN', 'RIGHT JOIN', 
        'INNER JOIN', 'OUTER JOIN', 'ON', 'CASE', 'WHEN', 'THEN', 
        'ELSE', 'END', 'CAST', 'COALESCE', 'LENGTH', 'UPPER', 'LOWER',
        'SUBSTR', 'TRIM', 'ROUND', 'ABS', 'DATE', 'DATETIME', 'STRFTIME'
    }
    
    FORBIDDEN_KEYWORDS: Set[str] = {
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 
        'TRUNCATE', 'REPLACE', 'PRAGMA', 'VACUUM', 'ATTACH', 'DETACH',
        'BEGIN', 'COMMIT', 'ROLLBACK', 'SAVEPOINT', 'RELEASE'
    }
    
    def __init__(self, max_rows: int = 100):
        self.max_rows = max_rows
    
    def validate(self, query: str) -> SQLValidationResult:
        try:
            query = query.strip()
            
            if not query:
                return SQLValidationResult(
                    is_valid=False,
                    error_message="Empty query"
                )
            
            parsed = sqlparse.parse(query)
            if not parsed:
                return SQLValidationResult(
                    is_valid=False,
                    error_message="Could not parse SQL query"
                )
            
            statement = parsed[0]
            
            if not self._is_select_only(statement):
                return SQLValidationResult(
                    is_valid=False,
                    error_message="Only SELECT statements are allowed"
                )
            
            forbidden_check = self._check_forbidden_keywords(query.upper())
            if not forbidden_check[0]:
                return SQLValidationResult(
                    is_valid=False,
                    error_message=f"Forbidden keyword detected: {forbidden_check[1]}"
                )
            
            if self._has_dangerous_patterns(query):
                return SQLValidationResult(
                    is_valid=False,
                    error_message="Query contains potentially dangerous patterns"
                )
            
            sanitized_query = self._sanitize_query(query)
            
            return SQLValidationResult(
                is_valid=True,
                sanitized_query=sanitized_query
            )
            
        except Exception as e:
            return SQLValidationResult(
                is_valid=False,
                error_message=f"Validation error: {str(e)}"
            )
    
    def _is_select_only(self, statement: Statement) -> bool:
        # Convert statement to string and check if it starts with SELECT
        query_str = str(statement).strip().upper()
        
        # Must start with SELECT or WITH
        if not (query_str.startswith('SELECT') or query_str.startswith('WITH')):
            return False
        
        # Check for forbidden keywords
        for token in statement.flatten():
            if token.ttype is Keyword or token.ttype is DML:
                token_val = token.value.upper()
                if token_val in self.FORBIDDEN_KEYWORDS:
                    return False
        
        return True
    
    def _check_forbidden_keywords(self, query: str) -> tuple[bool, str]:
        for keyword in self.FORBIDDEN_KEYWORDS:
            if re.search(r'\b' + keyword + r'\b', query):
                return False, keyword
        return True, ""
    
    def _has_dangerous_patterns(self, query: str) -> bool:
        dangerous_patterns = [
            r'--\s',
            r'/\*',
            r'\*/',
            r';\s*\w',
            r'UNION\s+SELECT',
            r'@@\w+',
            r'xp_\w+',
            r'sp_\w+',
        ]
        
        query_upper = query.upper()
        for pattern in dangerous_patterns:
            if re.search(pattern, query_upper):
                return True
        return False
    
    def _sanitize_query(self, query: str) -> str:
        query = query.strip()
        if query.endswith(';'):
            query = query[:-1]
        
        query_upper = query.upper()
        if 'LIMIT' not in query_upper:
            query += f' LIMIT {self.max_rows}'
        else:
            limit_match = re.search(r'LIMIT\s+(\d+)', query_upper)
            if limit_match:
                limit_value = int(limit_match.group(1))
                if limit_value > self.max_rows:
                    query = re.sub(
                        r'LIMIT\s+\d+', 
                        f'LIMIT {self.max_rows}', 
                        query, 
                        flags=re.IGNORECASE
                    )
        
        return query