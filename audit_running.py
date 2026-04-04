import json
from collections import defaultdict

def audit_running_totals():
    meta_path = 'run_page/garmin_activity_meta.json'
    with open(meta_path, 'r') as f:
        meta = json.load(f)
    
    # Yearly stats for running types
    # running, treadmill_running, virtual_run
    
    results = defaultdict(lambda: defaultdict(lambda: {'count': 0, 'dist': 0.0}))
    
    for run_id, m in meta.items():
        start_time = m.get('startTimeLocal', '')
        if not start_time:
            continue
        year = start_time[:4]
        if year not in ['2023', '2024', '2025', '2026']:
            continue
            
        r_type = m.get('type', 'unknown')
        dist = m.get('distance', 0) or 0
        
        results[year][r_type]['count'] += 1
        results[year][r_type]['dist'] += dist

    for year in sorted(results.keys()):
        print(f"\n===== Year {year} =====")
        year_total_dist = 0
        running_types = ['running', 'treadmill_running', 'virtual_run']
        
        for r_type in sorted(results[year].keys()):
            count = results[year][r_type]['count']
            dist_km = results[year][r_type]['dist'] / 1000.0
            print(f"- {r_type:20}: {count:3} activities | {dist_km:8.3f} km")
            if r_type in running_types:
                year_total_dist += dist_km
        
        print(f"\n>>> Total for Running types (Outdoor+Treadmill+Virtual): {year_total_dist:8.3f} km")
        # Let's also check ONLY outdoor running
        outdoor_run = results[year].get('running', {}).get('dist', 0) / 1000.0
        print(f">>> Only Outdoor Running: {outdoor_run:8.3f} km")

if __name__ == "__main__":
    audit_running_totals()
