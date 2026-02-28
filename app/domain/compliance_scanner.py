import os
import re

# Restrictive License keywords
RESTRICTIVE_LICENSES = {
    "GNU General Public License",
    "GPL",
    "AGPL",
    "GNU Affero General Public License"
}

# Prompt Injection keywords
PROMPT_INJECTION_KEYWORDS = {
    "ignore all previous instructions",
    "system prompt:",
    "you are now",
    "disregard context"
}

def detect_restrictive_licenses(repo_path: str) -> list:
    """Detects restrictive or 'Copyleft' licenses in the repository."""
    findings = []
    
    # Common license filenames
    license_files = ["LICENSE", "LICENSE.txt", "LICENSE.md", "COPYING", "COPYING.txt"]
    
    for file_name in license_files:
        file_path = os.path.join(repo_path, file_name)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    for keyword in RESTRICTIVE_LICENSES:
                        if keyword.lower() in content.lower():
                            findings.append({
                                "rule_id": "RESTRICTIVE_LICENSE",
                                "description": f"Detected highly restrictive license variant: '{keyword}' in {file_name}.",
                                "severity": "HIGH"
                            })
                            break # Once flagged, no need to flag the same file for other variants
            except Exception as e:
                print(f"Error reading license file {file_path}: {e}")
                
    return findings

def detect_prompt_injection(repo_path: str) -> list:
    """Scans code files for potential prompt injection vectors."""
    findings = []
    
    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.startswith('.') or '/venv/' in root or '/.git/' in root:
                continue
                
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, repo_path)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    lines = content.splitlines()
                    for line_num, line in enumerate(lines, 1):
                        lower_line = line.lower()
                        for keyword in PROMPT_INJECTION_KEYWORDS:
                            if keyword in lower_line:
                                findings.append({
                                    "rule_id": "PROMPT_INJECTION_RISK",
                                    "description": f"Detected potential prompt injection phrasing ('{keyword}') at line {line_num} in {relative_path}.",
                                    "severity": "MEDIUM"
                                })
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"Error reading {file_path} for prompt injection: {e}")
                
    return findings

def run_compliance_scan(repo_path: str) -> list:
    """Runs all compliance and licensing checks on a repository."""
    all_violations = []
    
    # Run License Scan
    all_violations.extend(detect_restrictive_licenses(repo_path))
    
    # Run Prompt Injection Scan
    all_violations.extend(detect_prompt_injection(repo_path))
    
    return all_violations
