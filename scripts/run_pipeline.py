import argparse
import httpx
import sys

def main():
    parser = argparse.ArgumentParser(description="Trigger full WhatIsUp pipeline")
    parser.add_argument("--secret", required=True, help="Admin secret")
    args = parser.parse_args()
    
    url = "http://localhost:8000/admin/run-pipeline"
    headers = {"X-Admin-Secret": args.secret}
    
    print("Triggering pipeline... this may take a while depending on network size.")
    
    # Use a long timeout since pipeline does multiple API calls and LLM calls
    with httpx.Client() as client:
        try:
            resp = client.post(url, headers=headers, timeout=300.0)
            resp.raise_for_status()
            print("Success:", resp.json())
        except Exception as e:
            print("Error:", e)
            if hasattr(e, "response") and e.response:
                print(e.response.text)
            sys.exit(1)

if __name__ == "__main__":
    main()
