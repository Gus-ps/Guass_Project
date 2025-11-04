"""Simple script to run the pipeline locally for a ticker.

Usage: python scripts/run_demo.py AAPL
"""
import sys
from src.backend import generate_company_report


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_demo.py <TICKER>")
        sys.exit(1)
    ticker = sys.argv[1]
    report = generate_company_report(ticker)
    try:
        import json
        print(json.dumps(report, indent=2, default=str))
    except Exception:
        print(report)


if __name__ == "__main__":
    main()
