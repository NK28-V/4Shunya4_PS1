class RiskScorer:
    def __init__(self):
        # Initializing without arguments to fix the TypeError
        pass

    def calculate_risk_score(self, findings: list) -> tuple:
        score = 100
        penalties = {
            "CRITICAL": 25,  # For eval, os.system
            "HIGH": 15,      # For Secrets, Licenses
            "MEDIUM": 5,     # For Unknown Dependencies
            "LOW": 2
        }
        
        for find in findings:
            severity = find.get("severity", "LOW")
            score -= penalties.get(severity, 2)
            
        score = max(0, score)
        
        if score >= 90: grade = "A"
        elif score >= 80: grade = "B"
        elif score >= 70: grade = "C"
        elif score >= 60: grade = "D"
        else: grade = "F"
        
        return score, grade