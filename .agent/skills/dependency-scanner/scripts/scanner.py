import sys
import json
import datetime
import re

try:
    import requests
except ImportError:
    print("Error: The 'requests' library is required. Please install it using 'pip install requests'")
    sys.exit(1)

def parse_package_json(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            deps = list(data.get('dependencies', {}).keys()) + list(data.get('devDependencies', {}).keys())
            return [('npm', d) for d in deps]
    except Exception as e:
        print(f"Error reading package.json: {e}")
        return []

def parse_requirements_txt(filepath):
    deps = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.split('#')[0].strip()
                if not line:
                    continue
                match = re.match(r'^([a-zA-Z0-9_\-]+)', line)
                if match:
                    deps.append(('pypi', match.group(1).lower()))
    except Exception as e:
        print(f"Error reading requirements.txt: {e}")
    return deps

def fetch_json(url):
    try:
        response = requests.get(url, headers={'User-Agent': 'Antigravity/DependencyScanner'})
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return None
        else:
            print(f"Warning: HTTP {response.status_code} for {url}")
            return None
    except requests.RequestException as e:
        print(f"Request Error for {url}: {e}")
        return None

def score_npm(package):
    score = 0
    now = datetime.datetime.now(datetime.timezone.utc)
    
    metadata_url = f"https://registry.npmjs.org/{package}"
    meta = fetch_json(metadata_url)
    
    if meta is None:
        # 404 means it doesn't exist. Max risk.
        return 100
        
    # 1. Age (40 pts)
    created_str = meta.get('time', {}).get('created')
    if created_str:
        created_str = created_str.replace('Z', '+00:00')
        try:
            created_date = datetime.datetime.fromisoformat(created_str)
            age_days = (now - created_date).days
            if age_days < 30:
                score += 40
            elif age_days < 90:
                score += int(40 - ((age_days - 30) / 60) * 40)
        except ValueError:
            pass
            
    # 2. Maintainer (30 pts)
    maintainers = meta.get('maintainers', [])
    if len(maintainers) == 0:
        score += 30
    elif len(maintainers) == 1:
        score += 15
        
    latest_version = meta.get('dist-tags', {}).get('latest')
    if latest_version:
        latest_data = meta.get('versions', {}).get(latest_version, {})
        signatures = latest_data.get('dist', {}).get('signatures', [])
        if not signatures:
            score += 15

    # 3. Downloads (30 pts)
    downloads_url = f"https://api.npmjs.org/downloads/range/last-month/{package}"
    dl_data = fetch_json(downloads_url)
    if dl_data and 'downloads' in dl_data:
        downloads = [d.get('downloads', 0) for d in dl_data['downloads']]
        total_dl = sum(downloads)
        if total_dl < 100:
            score += 30
        else:
            avg_dl = total_dl / len(downloads)
            max_dl = max(downloads)
            if avg_dl > 0 and max_dl > 10 * avg_dl:
                score += 15
                
    return min(100, score)

def score_pypi(package):
    score = 0
    now = datetime.datetime.now(datetime.timezone.utc)
    
    metadata_url = f"https://pypi.org/pypi/{package}/json"
    meta = fetch_json(metadata_url)
    
    if meta is None:
        # 404 means it doesn't exist. Max risk.
        return 100
        
    info = meta.get('info', {})
    
    releases = meta.get('releases', {})
    earliest_date = now
    has_releases = False
    for version, release_list in releases.items():
        for release in release_list:
            upload_time = release.get('upload_time_iso_8601')
            if upload_time:
                has_releases = True
                try:
                    upload_time = upload_time.replace('Z', '+00:00')
                    dt = datetime.datetime.fromisoformat(upload_time)
                    if dt < earliest_date:
                        earliest_date = dt
                except ValueError:
                    pass
    
    # 1. Age (40 pts)
    age_days = 0
    if has_releases:
        age_days = (now - earliest_date).days
        if age_days < 30:
            score += 40
        elif age_days < 90:
            score += int(40 - ((age_days - 30) / 60) * 40)
    else:
        score += 40

    # 2. Maintainer (30 pts)
    author_email = info.get('author_email', '')
    maintainer_email = info.get('maintainer_email', '')
    
    if not author_email and not maintainer_email:
        score += 30
    elif author_email and ("example.com" in author_email or "test.com" in author_email):
        score += 30
        
    # 3. Velocity / Active Maintenance (30 pts fallback)
    if has_releases:
        num_releases = len(releases)
        if num_releases == 1 and age_days < 30:
            score += 30
        elif num_releases < 3 and age_days < 60:
            score += 15

    return min(100, score)

def main():
    if len(sys.argv) < 2:
        print("Usage: python scanner.py <path_to_package.json_or_requirements.txt>")
        sys.exit(1)
        
    filepath = sys.argv[1]
    
    deps = []
    if filepath.endswith('package.json'):
        deps = parse_package_json(filepath)
    elif filepath.endswith('requirements.txt'):
        deps = parse_requirements_txt(filepath)
    else:
        print("Unsupported file format. Please provide a package.json or requirements.txt file.")
        sys.exit(1)
        
    if not deps:
        print("No dependencies found or error parsing relative to package formatting.")
        sys.exit(0)
        
    print(f"Scanning {len(deps)} dependencies from {filepath}...\n")
    
    for ecosystem, package in deps:
        if ecosystem == 'npm':
            score = score_npm(package)
        else:
            score = score_pypi(package)
            
        print(f"[{ecosystem.upper()}] Package: {package}")
        print(f"Risk Score: {score}/100")
        if score > 70:
            print("⚠️ HIGH RISK: Propensity indicating an AI hallucinated package.\n")
        elif score > 40:
            print("🟡 MODERATE RISK: Suspicious indicators observed.\n")
        else:
            print("✅ CLEAR: Normal indicators.\n")

if __name__ == "__main__":
    main()
