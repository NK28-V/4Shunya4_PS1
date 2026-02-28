---
name: Dependency Scanner
description: Parses package.json and requirements.txt to detect AI-hallucinated packages based on npm and PyPI API data natively without intermediary third-party APIs.
---

# Dependency Scanner

This skill provides the capability to parse standard ecosystem dependency files (`package.json` for Node.js/npm and `requirements.txt` for Python/PyPI) and analyze the packages to determine if they are likely AI hallucinations. 

## Usage

You can run the scanner script against your target dependency file. The scanner connects natively to the npm and PyPI endpoints without using third-party APIs.

```bash
python .agent/skills/dependency-scanner/scripts/scanner.py path/to/package.json
```
or 
```bash
python .agent/skills/dependency-scanner/scripts/scanner.py path/to/requirements.txt
```

## How It Works

The scoring algorithm assigns a risk probability score (0 to 100) based on three key metrics:
1. **Age (up to 40 pts)**: Packages younger than 30 days are heavily penalized.
2. **Maintainer Credibility (up to 30 pts)**: Analyzes the `maintainers` array, signature strings (npm), and `author_email` validity (PyPI).
3. **Velocity Anomalies (up to 30 pts)**: Penalizes packages with zero downloads, huge unexplained download spikes (npm), or lack of update momentum (PyPI fallback).

Scores over 70 indicate a critically high probability of a hallucinated, dummy, or malicious package.

## Endpoints Used
- `https://registry.npmjs.org/<package>`
- `https://api.npmjs.org/downloads/range/last-month/<package>`
- `https://pypi.org/pypi/<package>/json`
