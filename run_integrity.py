"""XTOBE Ai File Integrity — baseline + verify CLI.
Usage:
  python run_integrity.py baseline   (create manifest)
  python run_integrity.py verify     (check files)
"""
import os
import sys
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from engine.integrity import baseline, verify, get_key

def main():
    if len(sys.argv) < 2:
        print("Usage: python run_integrity.py baseline|verify")
        sys.exit(1)
    
    action = sys.argv[1]
    key = get_key()
    
    if action == "baseline":
        baseline(REPO_ROOT, key)
    elif action == "verify":
        verify(REPO_ROOT, key)
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)

if __name__ == "__main__":
    main()
