# engine/integrity.py — SHA-256 + HMAC-signed manifest for XTOBE Ai original layer
"""
File integrity verifier.
- Computes SHA-256 of every file in the protected tree
- Signs the manifest with HMAC-SHA256 so it can't be silently altered
- Reports OK / Modified / Missing / Extra files
- Exit code 0 = CLEAN, 1 = TAMPERED
"""
import hashlib
import hmac
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Protected directories relative to xtobe-ai root
PROTECTED_DIRS = ["engine", "www", "skills", "bin", "xtobe_agent", "static"]
PROTECTED_FILES = ["main.py", "run.py", "requirements.txt", "agent_bridge.py", "voice_agent_server.py", "xtobe_self_learning_agent.py"]

def get_key():
    key = os.environ.get("XTOBE_INTEGRITY_KEY", "")
    if not key:
        print("[INTEGRITY] ERROR: XTOBE_INTEGRITY_KEY not set.")
        sys.exit(1)
    return key.encode("utf-8")


def file_hash(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(root_dir):
    manifest = {
        "files": {},
        "created": datetime.now().isoformat(),
        "root": str(root_dir)
    }
    root_path = Path(root_dir)
    
    for d in PROTECTED_DIRS:
        dpath = root_path / d
        if not dpath.exists():
            continue
        for fpath in dpath.rglob("*"):
            if fpath.is_file():
                rel = str(fpath.relative_to(root_path))
                manifest["files"][rel] = file_hash(fpath)
    
    for fname in PROTECTED_FILES:
        fpath = root_path / fname
        if fpath.exists():
            manifest["files"][fname] = file_hash(fpath)
    
    return manifest


def sign_manifest(manifest, key):
    payload = json.dumps(manifest["files"], sort_keys=True).encode("utf-8")
    return hmac.new(key, payload, hashlib.sha256).hexdigest()


def verify_signature(manifest, key):
    expected = sign_manifest(manifest, key)
    return hmac.compare_digest(expected, manifest.get("signature", ""))


def baseline(root_dir, key):
    manifest = build_manifest(root_dir)
    manifest["signature"] = sign_manifest(manifest, key)
    
    manifest_path = Path(root_dir) / "integrity_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    print(f"[INTEGRITY] Baseline created: {len(manifest['files'])} files")
    print(f"[INTEGRITY] Manifest: {manifest_path}")
    print(f"[INTEGRITY] Signature: {manifest['signature'][:16]}...")
    return manifest


def verify(root_dir, key):
    manifest_path = Path(root_dir) / "integrity_manifest.json"
    if not manifest_path.exists():
        print("[INTEGRITY] ERROR: No baseline found. Run baseline first.")
        sys.exit(1)
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        trusted = json.load(f)
    
    if not verify_signature(trusted, key):
        print("[INTEGRITY] CRITICAL: Manifest signature mismatch!")
        sys.exit(1)
    
    current = build_manifest(root_dir)
    trusted_files = trusted["files"]
    current_files = current["files"]
    
    ok = []
    modified = []
    missing = []
    extra = []
    
    for path, old_hash in trusted_files.items():
        if path not in current_files:
            missing.append(path)
        elif current_files[path] != old_hash:
            modified.append(path)
        else:
            ok.append(path)
    
    for path in current_files:
        if path not in trusted_files:
            extra.append(path)
    
    print(f"[INTEGRITY] Verified: {len(ok)} ok, {len(modified)} modified, {len(missing)} missing, {len(extra)} extra")
    
    if modified:
        for m in modified:
            print(f"  MODIFIED: {m}")
    if missing:
        for m in missing:
            print(f"  MISSING: {m}")
    if extra:
        for e in extra:
            print(f"  EXTRA: {e}")
    
    if modified or missing:
        print("[INTEGRITY] TAMPERED")
        return False
    
    print("[INTEGRITY] CLEAN")
    return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="XTOBE Ai File Integrity")
    parser.add_argument("action", choices=["baseline", "verify"])
    args = parser.parse_args()
    
    root = Path(__file__).resolve().parent.parent
    key = get_key()
    
    if args.action == "baseline":
        baseline(root, key)
    else:
        verify(root, key)
