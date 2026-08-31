import argparse
import httpx
import sys

def main():
    parser = argparse.ArgumentParser(description="Add an owner to WhatIsUp")
    parser.add_argument("label", help="Owner label (e.g. 'builder')")
    parser.add_argument("github_username", help="GitHub username")
    parser.add_argument("--secret", required=True, help="Admin secret")
    args = parser.parse_args()
    
    url = "http://localhost:8000/admin/owners"
    headers = {"X-Admin-Secret": args.secret}
    payload = {
        "label": args.label,
        "github_username": args.github_username
    }
    
    print(f"Adding owner {args.label} ({args.github_username})...")
    
    with httpx.Client() as client:
        try:
            resp = client.post(url, headers=headers, json=payload, timeout=30.0)
            resp.raise_for_status()
            print("Success:", resp.json())
        except Exception as e:
            print("Error:", e)
            if hasattr(e, "response") and e.response:
                print(e.response.text)
            sys.exit(1)

if __name__ == "__main__":
    main()
