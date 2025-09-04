#!/usr/bin/env python3

import pytest
from typer.testing import CliRunner
from sql_agent.cli import app
import os
import tempfile
from pathlib import Path

runner = CliRunner()

def test_version_command():
    """Test the version command"""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "sql-agent v0.1.0" in result.stdout

def test_schema_command_no_db():
    """Test schema command when database doesn't exist"""
    result = runner.invoke(app, ["schema", "--db", "nonexistent.db"])
    assert result.exit_code == 1
    assert "Database 'nonexistent.db' not found" in result.stdout

def test_load_command_nonexistent_file():
    """Test load command with nonexistent CSV file"""
    result = runner.invoke(app, ["load", "nonexistent.csv"])
    assert result.exit_code == 1
    assert "CSV file 'nonexistent.csv' not found" in result.stdout

def test_load_command_with_sample_data():
    """Test load command with the sample data"""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test.db")
        
        # Test loading the sample CSV
        result = runner.invoke(app, [
            "load", 
            "data/sales.csv", 
            "--table", "sales", 
            "--db", db_path
        ])
        
        if result.exit_code == 0:
            assert "Successfully loaded 'sales'" in result.stdout
            assert os.path.exists(db_path)
        else:
            # If file doesn't exist, just check the error message is appropriate
            assert "CSV file" in result.stdout and "not found" in result.stdout

if __name__ == "__main__":
    test_version_command()
    test_schema_command_no_db()
    test_load_command_nonexistent_file()
    test_load_command_with_sample_data()
    print("All CLI tests passed!")
