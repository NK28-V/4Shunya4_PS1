from app.domain.scoring import RiskScorer
from app.domain.remediation import RemediationEngine

# 1. Mock findings exactly as detected in your Phase 3 terminal logs
mock_results = [
    {"severity": "CRITICAL", "title": "Dangerous Sinkhole (eval)"},
    {"severity": "CRITICAL", "title": "Dangerous Sinkhole (os.system)"},
    {"severity": "HIGH", "title": "High Entropy String Found"},
    {"severity": "MEDIUM", "title": "Unknown Dependency Detected"}
]

# 2. Execute Scoring Logic
scorer = RiskScorer()
score, grade = scorer.calculate_risk_score(mock_results)

# 3. Execute Remediation Mapping
remediation = RemediationEngine()

print("="*40)
print("   PHASE 4: AUDIT ANALYST VERIFICATION   ")
print("="*40)
print(f"FINAL SCORE: {score}/100")
print(f"FINAL GRADE: {grade}")
print("-" * 40)
print("REMEDIATION STEPS FOR DASHBOARD:")

for find in mock_results:
    # Use the 'get_fix' method from your remediation.py
    tip = remediation.get_fix(find['title'])
    print(f"[*] [{find['severity']}] {find['title']}")
    print(f"    FIX: {tip}\n")