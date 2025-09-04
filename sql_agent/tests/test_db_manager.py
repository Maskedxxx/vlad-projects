#!/usr/bin/env python3

from sql_agent.db import DatabaseManager

def test_db_manager():
    db_mgr = DatabaseManager("app.db")
    
    # Test the problematic query directly
    query = "SELECT product_name, SUM(price * quantity) as total_revenue FROM sales GROUP BY product_name ORDER BY total_revenue DESC LIMIT 5"
    
    print(f"Testing query: {query}")
    
    try:
        result = db_mgr.execute_query(query)
        print(f"Success! Returned {result['row_count']} rows")
        print(f"Execution time: {result['execution_time_ms']}ms")
        
        if result['data']:
            print("\nTop 3 results:")
            for i, row in enumerate(result['data'][:3]):
                print(f"{i+1}. {row['product_name']}: ${row['total_revenue']:.2f}")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_db_manager()