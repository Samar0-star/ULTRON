#!/usr/bin/env python3
"""
Perplexity Search Skill
=======================
This script acts as an interface to the Perplexity API.
It provides real-time, grounded answers with source citations.

Requirements:
    - Perplexity API key set in PERPLEXITY_API_KEY environment variable
    - Python 3.9+
    - requests
"""

import os
import sys
import json
import argparse
import requests
from typing import Dict, Any, List, Optional

def check_env() -> bool:
    """Check if Perplexity API key is configured."""
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        print("Error: PERPLEXITY_API_KEY environment variable is not set.", file=sys.stderr)
        print("\nTo fix this:", file=sys.stderr)
        print("1. Get an API key from https://www.perplexity.ai/settings/api", file=sys.stderr)
        print("2. Set it in your environment:", file=sys.stderr)
        print("   export PERPLEXITY_API_KEY='your-api-key-here'", file=sys.stderr)
        print("3. Or add it to your .env file:", file=sys.stderr)
        print("   PERPLEXITY_API_KEY=your-api-key-here", file=sys.stderr)
        return False
    return True

def do_search(
    query: str,
    model: str = "sonar-pro",
    temperature: float = 0.2,
    max_tokens: Optional[int] = None
) -> Dict[str, Any]:
    """
    Perform a search using Perplexity models via direct API.
    """
    if not check_env():
        return {
            "success": False,
            "error": "Perplexity API key not configured"
        }

    api_key = os.environ.get("PERPLEXITY_API_KEY")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are an expert research assistant. Provide detailed, accurate, and up-to-date answers."},
            {"role": "user", "content": query}
        ],
        "temperature": temperature
    }
    
    if max_tokens:
        payload["max_tokens"] = max_tokens

    try:
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers=headers,
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        data = response.json()
        
        answer = data["choices"][0]["message"]["content"]
        citations = data.get("citations", [])
        
        return {
            "success": True,
            "answer": answer,
            "citations": citations,
            "model_used": model
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "details": f"API call failed: {type(e).__name__}"
        }

def main():
    parser = argparse.ArgumentParser(
        description="Perform AI-powered web searches using Perplexity API",
        formatter_class=argparse.ArgumentRawDescriptionHelpFormatter,
        epilog="""
Examples:
  python perplexity_search.py "What are the latest breakthroughs in solid-state batteries?"
  python perplexity_search.py "Explain quantum spin liquids" --model "sonar-reasoning" --temperature 0.1
        """
    )
    
    parser.add_argument("query", type=str, help="The search query or question")
    parser.add_argument("--model", type=str, default="sonar-pro", 
                        help="Perplexity model to use (default: sonar-pro)")
    parser.add_argument("--temperature", type=float, default=0.2, 
                        help="Sampling temperature (default: 0.2)")
    parser.add_argument("--max-tokens", type=int, default=None, 
                        help="Maximum tokens to generate")
    parser.add_argument("--format", type=str, choices=["text", "json"], default="text",
                        help="Output format (default: text)")

    args = parser.parse_args()

    # Load environment variables if dotenv is available
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    result = do_search(
        query=args.query,
        model=args.model,
        temperature=args.temperature,
        max_tokens=args.max_tokens
    )

    if args.format == "json":
        print(json.dumps(result, indent=2))
        if not result["success"]:
            sys.exit(1)
    else:
        if result["success"]:
            print(f"\n--- Result (Model: {result['model_used']}) ---\n")
            print(result["answer"])
            
            if result.get("citations"):
                print("\n\n--- Citations ---\n")
                for i, citation in enumerate(result["citations"], 1):
                    print(f"[{i}] {citation}")
        else:
            print(f"Error: {result['error']}")
            if "details" in result:
                print(f"Details: {result['details']}")
            sys.exit(1)

if __name__ == "__main__":
    main()
