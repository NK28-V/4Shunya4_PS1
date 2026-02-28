import ast
import os

# Dangerous global functions
DANGEROUS_FUNCTIONS = {"eval", "exec"}

# Dangerous module attributes (module, attribute)
DANGEROUS_ATTRIBUTES = {
    ("os", "system"),
    ("os", "popen"),
    ("subprocess", "run"),
    ("subprocess", "Popen"),
    ("subprocess", "call")
}

class SinkholeVisitor(ast.NodeVisitor):
    def __init__(self, file_path):
        self.file_path = file_path
        self.findings = []

    def visit_Call(self, node):
        # Check direct function calls like eval()
        if isinstance(node.func, ast.Name):
            if node.func.id in DANGEROUS_FUNCTIONS:
                self.findings.append({
                    "severity": "HIGH",
                    "title": "Dangerous Sink Executed",
                    "description": f"Use of dangerous function '{node.func.id}' detected.",
                    "file_path": self.file_path,
                    "line_number": node.lineno
                })
        
        # Check method/attribute calls like os.system()
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                module_name = node.func.value.id
                attr_name = node.func.attr
                if (module_name, attr_name) in DANGEROUS_ATTRIBUTES:
                    self.findings.append({
                        "severity": "HIGH",
                        "title": "Dangerous Sink Executed",
                        "description": f"Use of dangerous method '{module_name}.{attr_name}' detected.",
                        "file_path": self.file_path,
                        "line_number": node.lineno
                    })

        self.generic_visit(node)

def run_ast_scan(repo_path: str) -> list:
    """Runs AST analysis on all Python files in a directory."""
    all_vulnerabilities = []
    
    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith('.py'):
                # Skip hidden files and virtual envs
                if file.startswith('.') or '/venv/' in root or '/.git/' in root:
                    continue
                    
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, repo_path)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        source = f.read()
                    
                    tree = ast.parse(source, filename=file_path)
                    visitor = SinkholeVisitor(relative_path)
                    visitor.visit(tree)
                    
                    all_vulnerabilities.extend(visitor.findings)
                        
                except SyntaxError as e:
                    print(f"Syntax error in {file_path}, skipping AST analysis.")
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
                    
    return all_vulnerabilities
