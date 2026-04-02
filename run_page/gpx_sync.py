"""
If you do not want bind any account
Only the gpx files in GPX_OUT sync
"""

from config import GPX_FOLDER, JSON_FILE, SQL_FILE, GARMIN_META_FILE
from utils import make_activities_file

if __name__ == "__main__":
    print("Syncing activities from Garmin Metadata (Absolute Truth)...")
    make_activities_file(SQL_FILE, GPX_FOLDER, JSON_FILE, garmin_meta_file=GARMIN_META_FILE)
