"""
Example script demonstrating how to use the Multi-Agent Retail System.

This script shows how to:
1. Populate the database with sample data
2. Make requests to the sales agent endpoint
"""

import requests
import json

BASE_URL = "http://localhost:8000"


def add_sample_data():
    """Add sample data to the database."""
    print("Adding sample data...")
    
    # Add a user
    user_data = {
        "user_id": "user_001",
        "name": "Alice Johnson",
        "loyalty_tier": "gold"
    }
    response = requests.post(f"{BASE_URL}/admin/users", json=user_data)
    print(f"User added: {response.json()}")
    
    # Add products
    products = [
        {
            "product_id": "PROD-001",
            "name": "Wireless Headphones",
            "category": "electronics",
            "base_price": 99.99
        },
        {
            "product_id": "PROD-002",
            "name": "Smart Watch",
            "category": "electronics",
            "base_price": 199.99
        },
        {
            "product_id": "PROD-003",
            "name": "Running Shoes",
            "category": "footwear",
            "base_price": 79.99
        }
    ]
    
    for product in products:
        response = requests.post(f"{BASE_URL}/admin/products", json=product)
        print(f"Product added: {response.json()}")
    
    # Add inventory
    inventory_items = [
        {
            "sku": "SKU-001",
            "product_id": "PROD-001",
            "size": "M",
            "quantity": 50,
            "location": "warehouse"
        },
        {
            "sku": "SKU-002",
            "product_id": "PROD-002",
            "size": "L",
            "quantity": 25,
            "location": "warehouse"
        }
    ]
    
    for item in inventory_items:
        response = requests.post(f"{BASE_URL}/admin/inventory", json=item)
        print(f"Inventory added: {response.json()}")
    
    print("\nSample data added successfully!\n")


def test_sales_agent():
    """Test the sales agent with various queries."""
    print("Testing Sales Agent...\n")
    
    # Test 1: Check inventory
    print("Test 1: Checking inventory...")
    request = {
        "session_id": "session_001",
        "user_id": "user_001",
        "message": "Check if SKU-001 in size M is available"
    }
    response = requests.post(f"{BASE_URL}/sales-agent", json=request)
    result = response.json()
    print(f"Response: {result['response']}")
    print(f"Validation passed: {result['execution_trace']['validation_passed']}\n")
    
    # Test 2: Get recommendations
    print("Test 2: Getting product recommendations...")
    request = {
        "session_id": "session_001",
        "user_id": "user_001",
        "message": "Recommend some electronics products under $150"
    }
    response = requests.post(f"{BASE_URL}/sales-agent", json=request)
    result = response.json()
    print(f"Response: {result['response']}\n")
    
    # Test 3: Get user profile
    print("Test 3: Getting user profile...")
    request = {
        "session_id": "session_001",
        "user_id": "user_001",
        "message": "What's my loyalty tier?"
    }
    response = requests.post(f"{BASE_URL}/sales-agent", json=request)
    result = response.json()
    print(f"Response: {result['response']}\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Multi-Agent Retail System - Example Usage")
    print("=" * 60)
    print("\nMake sure the server is running: uvicorn app.main:app --reload\n")
    
    try:
        # Check if server is running
        response = requests.get(f"{BASE_URL}/")
        print(f"Server is running: {response.json()}\n")
        
        # Add sample data
        add_sample_data()
        
        # Test sales agent
        test_sales_agent()
        
        print("=" * 60)
        print("Example completed successfully!")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to server.")
        print("Please start the server first:")
        print("  uvicorn app.main:app --reload")
    except Exception as e:
        print(f"ERROR: {e}")

