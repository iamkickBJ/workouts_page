import json
from collections import defaultdict

def audit_2025_monthly():
    meta_path = 'run_page/garmin_activity_meta.json'
    with open(meta_path, 'r') as f:
        meta = json.load(f)
    
    monthly_data = defaultdict(lambda: {'count': 0, 'dist': 0.0})
    running_types = ['running', 'treadmill_running', 'virtual_run']
    
    for run_id, m in meta.items():
        start_time = m.get('startTimeLocal', '')
        if not start_time.startswith('2025'):
            continue
            
        r_type = m.get('type', 'unknown')
        if r_type not in running_types:
            continue
            
        month = start_time[:7]
        dist = m.get('distance', 0) or 0
        
        monthly_data[month]['count'] += 1
        monthly_data[month]['dist'] += dist

    print("===== 2025 Monthly Running Audit (Truth Source) =====")
    total_dist_km = 0
    total_count = 0
    for month in sorted(monthly_data.keys()):
        count = monthly_data[month]['count']
        dist_km = monthly_data[month]['dist'] / 1000.0
        print(f"{month} | {count:3} Runs | {dist_km:8.3f} km")
        total_dist_km += dist_km
        total_count += count
    
    print("-" * 50)
    print(f"Grand Total: {total_count} Runs | {total_dist_km:8.3f} km")
    
    # Check for anything near 2.231km discrepancy
    if abs(total_dist_km - 2498) > 0.1:
        print(f"\nDiscrepancy (vs 2498.0): {total_dist_km - 2498.0:.3f} km")

if __name__ == "__main__":
    audit_2025_monthly()
