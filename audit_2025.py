import json
import sqlite3
import os

def audit_2025():
    meta_path = 'run_page/garmin_activity_meta.json'
    db_path = 'run_page/data.db'
    
    if not os.path.exists(meta_path):
        print("Meta file not found.")
        return
        
    with open(meta_path, 'r') as f:
        meta = json.load(f)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Audit 2025 Runs
    db_data = cursor.execute("SELECT run_id, distance, name, start_date_local FROM activities WHERE type = 'Run' AND start_date_local LIKE '2025%'").fetchall()
    
    print(f"Total Runs in DB for 2025: {len(db_data)}")
    
    discrepancies = []
    total_db_dist = 0
    total_meta_dist = 0
    not_in_meta = []
    
    # Pre-sum meta for 2025 to compare totals
    actual_meta_2025_sum = sum(m.get('distance', 0) for m in meta.values() if m.get('type') == 'running' and m.get('startTimeLocal', '').startswith('2025'))
    print(f"Actual Official Meta 2025 Total: {actual_meta_2025_sum/1000.0:.3f} km")

    for run_id, db_dist, name, start_date in db_data:
        total_db_dist += db_dist
        meta_entry = meta.get(str(run_id))
        if meta_entry:
            meta_dist = meta_entry.get('distance', 0)
            total_meta_dist += meta_dist
            diff = abs(db_dist - meta_dist)
            if diff > 0.01: # if more than 1cm difference
                discrepancies.append({
                    'run_id': run_id,
                    'name': name,
                    'db_dist': db_dist,
                    'meta_dist': meta_dist,
                    'diff': diff,
                    'date': start_date
                })
        else:
            not_in_meta.append(run_id)
            
    print(f"Total Distance in DB (2025 Runs): {total_db_dist/1000.0:.3f} km")
    print(f"Number of discrepancies found: {len(discrepancies)}")
    if discrepancies:
        print("\nFirst 10 Discrepancies:")
        for d in discrepancies[:10]:
            print(f"Date: {d['date']} | ID: {d['run_id']} | DB: {d['db_dist']:.2f}m | Meta: {d['meta_dist']:.2f}m | Diff: {d['diff']:.2f}m")
    
    if not_in_meta:
        print(f"\nActivities in DB but NOT in Meta: {len(not_in_meta)}")
        print(not_in_meta[:5])

if __name__ == "__main__":
    audit_2025()
