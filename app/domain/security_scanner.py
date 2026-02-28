import ast
import os
import re
import math
import sys

# 1. FINALIZED WHITELIST: Added codecs, io, yaml, warnings, and ast to prevent false positives
PYTHON_SAFE_MODULES = set(sys.builtin_module_names).union({
    "os", "sys", "re", "math", "collections", "datetime", "json", "urllib", "time",
    "requests", "numpy", "pandas", "Flask", "Django", "FastAPI", "sqlalchemy",
    "pytest", "celery", "redis", "pydantic", "logging", "abc", "typing",
    "io", "yaml", "warnings", "pathlib", "threading", "ast", "codecs"
})

SECRET_PATTERNS = {
    "AWS Access Key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "RSA Private Key": re.compile(r"-----BEGIN RSA PRIVATE KEY-----"),
    "Generic High Entropy": re.compile(r"['\"]([a-zA-Z0-9_-]{32,})['\"]")
}

def calculate_shannon_entropy(data: str) -> float:
    if not data: return 0
    entropy = 0
    for x in set(data):
        p_x = float(data.count(x)) / len(data)
        if p_x > 0:
            entropy += - p_x * math.log(p_x, 2)
    return entropy

def detect_secrets(file_content: str, file_path: str) -> list:
    findings = []
    lines = file_content.splitlines()
    for line_num, line in enumerate(lines, 1):
        for secret_type, pattern in SECRET_PATTERNS.items():
            matches = pattern.findall(line)
            for match in matches:
                if secret_type == "Generic High Entropy":
                    if calculate_shannon_entropy(match) > 3.5:
                        findings.append({
                            "severity": "CRITICAL",
                            "title": "High Entropy String Found",
                            "description": "Potential leaked credential or token.",
                            "file_path": file_path, "line_number": line_num
                        })
                else:
                    findings.append({
                        "severity": "CRITICAL",
                        "title": f"Leaked {secret_type}",
                        "description": f"Found pattern matching {secret_type}.",
                        "file_path": file_path, "line_number": line_num
                    })
    return findings

# 2. AST ANALYSIS ENGINE: Now implemented to find dangerous sinkholes
def detect_ast_sinkholes(file_content: str, file_path: str) -> list:
    findings = []
    try:
        tree = ast.parse(file_content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Detect eval()
                if isinstance(node.func, ast.Name) and node.func.id == 'eval':
                    findings.append({
                        "severity": "CRITICAL", "title": "Dangerous Sinkhole (eval)",
                        "description": "Found eval() which allows arbitrary code execution.",
                        "file_path": file_path, "line_number": node.lineno
                    })
                # Detect os.system()
                elif isinstance(node.func, ast.Attribute) and \
                     isinstance(node.func.value, ast.Name) and \
                     node.func.value.id == 'os' and node.func.attr == 'system':
                    findings.append({
                        "severity": "CRITICAL", "title": "Dangerous Sinkhole (os.system)",
                        "description": "Found os.system() which is vulnerable to command injection.",
                        "file_path": file_path, "line_number": node.lineno
                    })
    except Exception: pass
    return findings

def detect_hallucinated_dependencies(file_content: str, file_path: str) -> list:
    findings = []
    import_pattern = re.compile(r"^(?:from\s+([a-zA-Z0-9_.]+)\s+import|import\s+([a-zA-Z0-9_.]+))")
    for line_num, line in enumerate(file_content.splitlines(), 1):
        clean_line = line.strip()
        if not clean_line: continue 
        match = import_pattern.search(clean_line)
        if match:
            module_name = match.group(1) or match.group(2)
            if module_name: 
                base_module = module_name.split('.')[0]
                if base_module and base_module not in PYTHON_SAFE_MODULES:
                    findings.append({
                        "severity": "MEDIUM", "title": "Unknown Dependency Detected",
                        "description": f"The package '{base_module}' is not in the safe whitelist.",
                        "file_path": file_path, "line_number": line_num
                    })
    return findings

def run_security_scan(repo_path: str) -> list:
    all_vulnerabilities = []
    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.startswith('.') or '/venv/' in root or '/.git/' in root:
                continue
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, repo_path)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                all_vulnerabilities.extend(detect_secrets(content, relative_path))
                if file.endswith('.py'):
                    # 3. INTEGRATION: Call AST and Dependency detection
                    all_vulnerabilities.extend(detect_hallucinated_dependencies(content, relative_path))
                    all_vulnerabilities.extend(detect_ast_sinkholes(content, relative_path))
            except Exception: continue
    return all_vulnerabilities