## Vibe-Audit compliance_core

Beginner-friendly Python compliance rules engine for hackathon use.

### What it does
- Loads a JSON configuration file
- Runs SOC2 and GDPR checks
- Outputs **structured JSON** violations

### Minimal JSON config shape
```json
{
  "logical_access": {
    "mfa_enabled": true,
    "rbac_present": true
  },
  "data_protection": {
    "pii_encrypted": true
  }
}
```

### Run from repo root
```bash
python backend/compliance_core/cli.py --config path/to/config.json --pretty
```

### Output fields (always present)
- `violations`: list of violation objects
- `violation_count`: number of violations
- `frameworks_checked`: frameworks executed (e.g. `["SOC2", "GDPR"]`)

