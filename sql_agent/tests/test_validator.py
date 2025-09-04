#!/usr/bin/env python3

from sql_agent.validators import SQLValidator

def test_validator():
    validator = SQLValidator()
    
    # Test the problematic query
    query = "SELECT product_name, SUM(price * quantity) as total_revenue FROM sales GROUP BY product_name ORDER BY total_revenue DESC LIMIT 5"
    
    print(f"Testing query: {query}")
    result = validator.validate(query)
    
    print(f"Is valid: {result.is_valid}")
    if not result.is_valid:
        print(f"Error: {result.error_message}")
    else:
        print(f"Sanitized: {result.sanitized_query}")

def test_forbidden_queries():
    validator = SQLValidator()
    
    # Test forbidden queries
    forbidden_queries = [
        "DROP TABLE users",
        "INSERT INTO users (name) VALUES ('test')",
        "UPDATE users SET name = 'hacker'",
        "DELETE FROM users WHERE id = 1"
    ]
    
    print("\nTesting forbidden queries:")
    for query in forbidden_queries:
        result = validator.validate(query)
        print(f"Query: {query}")
        print(f"Valid: {result.is_valid} - {result.error_message if not result.is_valid else 'OK'}")

if __name__ == "__main__":
    test_validator()
    test_forbidden_queries()
