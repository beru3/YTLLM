#!/usr/bin/env python
import argparse
import json
import requests
from config.config import API_HOST, API_PORT

def test_query(query: str):
    """
    Test a query against the API.
    
    Args:
        query: Query text
    """
    url = f"http://{API_HOST}:{API_PORT}/api/query"
    
    payload = {
        "query": query,
        "top_k": 5
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        result = response.json()
        
        print("\n" + "=" * 80)
        print("QUERY:", query)
        print("=" * 80)
        print("\nRESPONSE:")
        print(result["response"])
        print("\n" + "=" * 80)
        print(f"Retrieval time: {result['retrieval_time_ms']} ms")
        print(f"Generation time: {result['generation_time_ms']} ms")
        print(f"Total time: {result['total_time_ms']} ms")
        print("=" * 80 + "\n")
        
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        if hasattr(e, "response") and e.response:
            print(f"Response: {e.response.text}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test a query against the Marketing LLM API")
    parser.add_argument("query", help="Query text")
    
    args = parser.parse_args()
    
    test_query(args.query) 