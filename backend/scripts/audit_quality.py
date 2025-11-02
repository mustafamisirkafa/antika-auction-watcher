"""
Antika Auction Watcher — Audit Script v1.0
Checks code quality, file size limits, duplication, and environment consistency
based on rules.yaml configuration.
"""

import os
import re
import yaml
import hashlib
from collections import defaultdict

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
RULES_PATH = os.path.join(BASE_DIR, "../..", "rules.yaml")
REPORT_PATH = os.path.join(BASE_DIR, "../..", "AUDIT_REPORT.md")

def load_rules():
    with open(RULES_PATH, "r") as f:
        return yaml.safe_load(f)

def file_hash(content):
    return hashlib.md5(content.encode()).hexdigest()

def count_lines(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return len(f.readlines())

def scan_python_files(root):
    for dirpath, _, files in os.walk(root):
        for file in files:
            if file.endswith(".py"):
                yield os.path.join(dirpath, file)

def check_file_size(path, max_lines, warnings, errors):
    lines = count_lines(path)
    if lines > 400:
        warnings.append(f"⚠️ {path} has {lines} lines (consider splitting).")
    if lines > max_lines:
        errors.append(f"❌ {path} exceeds {max_lines} lines! Must refactor.")

def check_duplicate_content(paths, similarity_threshold, warnings, errors):
    hashes = defaultdict(list)
    for path in paths:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                hashes[file_hash(content[:2000])] .append(path)
        except Exception:
            continue
    for h, files in hashes.items():
        if len(files) > 1:
            errors.append(f"❌ Duplicate-like files detected: {', '.join(files)}")

def check_env_variables(rules, warnings, errors):
    env_path = os.path.join(BASE_DIR, "../../.env.example")
    if not os.path.exists(env_path):
        errors.append("❌ Missing .env.example file.")
        return
    with open(env_path, "r") as f:
        env_content = f.read()
    for var in rules["environment"]["required_envs"]:
        if var not in env_content:
            errors.append(f"❌ Missing required env variable: {var}")
    for var in rules["environment"]["optional_envs"]:
        if var not in env_content:
            warnings.append(f"⚠️ Optional env variable missing: {var}")

def check_imports(path, warnings, errors):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    if "import *" in content:
        errors.append(f"❌ Wildcard import found in {path}.")
    if re.search(r"from\s+\S+\s+import\s+\S+,\s*\S+", content):
        warnings.append(f"⚠️ Multiple imports on one line in {path}.")

def generate_report(warnings, errors):
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("# 🧾 Audit Quality Report v1.0\n\n")
        if not warnings and not errors:
            f.write("✅ All checks passed successfully!\n")
        else:
            if warnings:
                f.write("## ⚠️ Warnings\n" + "\n".join(warnings) + "\n\n")
            if errors:
                f.write("## ❌ Errors\n" + "\n".join(errors) + "\n\n")
        f.write(f"---\nTotal Warnings: {len(warnings)} | Total Errors: {len(errors)}\n")

def main():
    print("🔍 Running Audit Script v1.0...")
    rules = load_rules()
    max_lines = rules["file_size"]["max_lines_per_file"]
    similarity_threshold = rules["duplication"]["similarity_threshold"]

    warnings, errors = [], []
    all_py_files = list(scan_python_files(BASE_DIR))

    # Core checks
    for file_path in all_py_files:
        check_file_size(file_path, max_lines, warnings, errors)
        check_imports(file_path, warnings, errors)

    # Global checks
    check_duplicate_content(all_py_files, similarity_threshold, warnings, errors)
    check_env_variables(rules, warnings, errors)

    generate_report(warnings, errors)
    print("✅ Audit complete. See AUDIT_REPORT.md for details.")

if __name__ == "__main__":
    main()
