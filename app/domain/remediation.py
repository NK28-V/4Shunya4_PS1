"""
Remediation logic mapping specific findings to actionable fixes.
"""

REMEDIATION_MAPPING = {
    "os.system": "Suggest using the subprocess module with shell=False.",
    "eval": "Suggest ast.literal_eval() or refactoring to a safer dictionary-based approach.",
    "restrictive_license": "Suggest a permissive alternative like MIT or Apache-2.0.",
    "leaked": "Suggest using environment variables or a secret manager like Vault.",
    "unknown dependency": "Verify if the package is legitimate or if it's a hallucinated import. Add to project dependencies if valid.",
    "prompt injection": "Review the LLM instruction prompt to prevent override commands and sanitize user inputs."
}

class RemediationEngine:
    """Class wrapper for remediation logic to support class-based imports."""
    
    def get_fix(self, title: str) -> str:
        """Standardized method name for the verification script."""
        # Call the existing heuristic function for backward compatibility
        return get_remediation_tip(title, "")

def get_remediation_tip(finding_title: str, finding_desc: str) -> str:
    """Returns a remediation tip based on finding title or description heuristics."""
    title = finding_title.lower() if finding_title else ""
    desc = finding_desc.lower() if finding_desc else ""
    
    if "os.system" in title or "os.system" in desc:
        return REMEDIATION_MAPPING["os.system"]
    elif "eval" in title or "eval" in desc:
        return REMEDIATION_MAPPING["eval"]
    elif "leaked" in title or "high entropy" in title or "leaked" in desc:
        return REMEDIATION_MAPPING["leaked"]
    elif "restrictive_license" in title or "restrictive license" in desc:
        return REMEDIATION_MAPPING["restrictive_license"]
    elif "unknown dependency" in title or "unknown dependency" in desc:
        return REMEDIATION_MAPPING["unknown dependency"]
    elif "prompt_injection" in title or "prompt injection" in desc:
        return REMEDIATION_MAPPING["prompt injection"]
        
    return "Review the flagged code and apply relevant security best practices."