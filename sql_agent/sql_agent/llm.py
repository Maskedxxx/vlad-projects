import os
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from langchain.memory import ConversationBufferMemory
from langchain.schema import HumanMessage, SystemMessage
import logging
from sql_agent.db import DatabaseManager
from sql_agent.tools import create_sql_tools
from sql_agent.models import QueryResult


logger = logging.getLogger(__name__)


class SQLAgent:
    def __init__(
        self, 
        db_manager: DatabaseManager,
        api_key: Optional[str] = None,
        model: str = "gpt-4",
        temperature: float = 0.1
    ):
        self.db_manager = db_manager
        
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
        
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable or pass api_key parameter.")
        
        self.llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            streaming=False
        )
        
        self.tools = create_sql_tools(db_manager)
        
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        self.agent = initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.OPENAI_FUNCTIONS,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True
        )
    
    def ask(self, question: str, table_name: Optional[str] = None) -> QueryResult:
        logger.info(f"Processing question: {question}")
        
        try:
            system_prompt = self._create_system_prompt(table_name)
            
            full_prompt = f"{system_prompt}\n\nUser question: {question}"
            
            response = self.agent.run(full_prompt)
            
            last_query_result = self._extract_last_query_result()
            
            return QueryResult(
                sql_query=last_query_result.get("sql_query", ""),
                data=last_query_result.get("data", []),
                row_count=last_query_result.get("row_count", 0),
                execution_time_ms=last_query_result.get("execution_time_ms", 0),
                answer=response
            )
            
        except Exception as e:
            logger.error(f"Error processing question: {str(e)}")
            raise ValueError(f"Failed to process question: {str(e)}")
    
    def _create_system_prompt(self, table_name: Optional[str] = None) -> str:
        prompt = """You are a SQL data analyst assistant. Your job is to help users analyze data by writing and executing SQL queries.

IMPORTANT WORKFLOW:
1. First, use 'list_tables' to see what tables are available (unless a specific table is mentioned)
2. Use 'describe_table_schema' to understand the table structure and see sample data
3. Write and execute a precise SQL query using 'run_sql_query' 
4. Analyze the results and provide a clear, comprehensive answer

CONSTRAINTS:
- Only SELECT statements are allowed - no INSERT, UPDATE, DELETE, DROP, etc.
- Maximum 100 rows will be returned per query
- Always examine the table schema before writing queries
- Use proper SQL syntax for SQLite
- Be precise with column names and table references

RESPONSE FORMAT:
- Provide a clear answer to the user's question
- Show relevant data in a readable format
- Explain any insights or patterns you notice
- If the query returns no results, explain why that might be

EXAMPLES OF GOOD QUERIES:
- SELECT category, SUM(amount) as total_sales FROM sales GROUP BY category ORDER BY total_sales DESC LIMIT 10
- SELECT * FROM sales WHERE date >= '2023-01-01' AND date < '2024-01-01'
- SELECT AVG(price) as average_price, COUNT(*) as product_count FROM products WHERE category = 'Electronics'"""

        if table_name:
            prompt += f"\n\nThe user is asking about the '{table_name}' table specifically."
        
        return prompt
    
    def _extract_last_query_result(self) -> Dict[str, Any]:
        """Extract the results from the last SQL query execution."""
        if hasattr(self.agent.memory, 'chat_memory') and self.agent.memory.chat_memory.messages:
            for message in reversed(self.agent.memory.chat_memory.messages):
                content = str(message.content)
                if "Query Results" in content and "SQL executed:" in content:
                    lines = content.split('\n')
                    for line in lines:
                        if line.startswith('SQL executed:'):
                            sql = line.replace('SQL executed:', '').strip()
                            return {
                                "sql_query": sql,
                                "data": [],
                                "row_count": 0,
                                "execution_time_ms": 0
                            }
        
        return {
            "sql_query": "",
            "data": [],
            "row_count": 0,
            "execution_time_ms": 0
        }
    
    def reset_conversation(self):
        """Reset the conversation memory."""
        self.memory.clear()
        logger.info("Conversation memory cleared")


class SimpleQueryExecutor:
    """Fallback executor for direct SQL queries without LLM involvement."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def execute(self, sql_query: str) -> QueryResult:
        logger.info(f"Executing direct SQL query: {sql_query}")
        
        try:
            result = self.db_manager.execute_query(sql_query)
            
            return QueryResult(
                sql_query=result["sql_query"],
                data=result["data"], 
                row_count=result["row_count"],
                execution_time_ms=result["execution_time_ms"],
                answer=f"Query executed successfully. Returned {result['row_count']} rows."
            )
            
        except Exception as e:
            logger.error(f"Error executing direct query: {str(e)}")
            raise ValueError(f"Query execution failed: {str(e)}")