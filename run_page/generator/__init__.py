import datetime
import os
import sys

import arrow
try:
    import stravalib
except Exception:
    stravalib = None
from config import MAPPING_TYPE, TYPE_DICT
from gpxtrackposter import track_loader
from sqlalchemy import func

from polyline_processor import filter_out

from .db import Activity, init_db, update_or_create_activity

from synced_data_file_logger import save_synced_data_file_list


IGNORE_BEFORE_SAVING = os.getenv("IGNORE_BEFORE_SAVING", False)


class Generator:
    def __init__(self, db_path):
        self.client = stravalib.Client() if stravalib else None
        self.session = init_db(db_path)

        self.client_id = ""
        self.client_secret = ""
        self.refresh_token = ""
        self.only_run = False

    def set_strava_config(self, client_id, client_secret, refresh_token):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token

    def check_access(self):
        response = self.client.refresh_access_token(
            client_id=self.client_id,
            client_secret=self.client_secret,
            refresh_token=self.refresh_token,
        )
        # Update the authdata object
        self.access_token = response["access_token"]
        self.refresh_token = response["refresh_token"]

        self.client.access_token = response["access_token"]
        print("Access ok")

    def sync(self, force):
        self.check_access()

        print("Start syncing")
        if force:
            filters = {"before": datetime.datetime.utcnow()}
        else:
            last_activity = self.session.query(func.max(Activity.start_date)).scalar()
            if last_activity:
                last_activity_date = arrow.get(last_activity)
                last_activity_date = last_activity_date.shift(days=-7)
                filters = {"after": last_activity_date.datetime}
            else:
                filters = {"before": datetime.datetime.utcnow()}

        for activity in self.client.get_activities(**filters):
            if self.only_run and activity.type != "Run":
                continue
            if IGNORE_BEFORE_SAVING:
                activity.summary_polyline = filter_out(activity.summary_polyline)
            activity.source = "strava"
            created = update_or_create_activity(self.session, activity)
            if created:
                sys.stdout.write("+")
            else:
                sys.stdout.write(".")
            sys.stdout.flush()
        self.session.commit()

    def sync_from_data_dir(self, data_dir, file_suffix="gpx"):
        loader = track_loader.TrackLoader()
        tracks = loader.load_tracks(data_dir, file_suffix=file_suffix)
        print(f"load {len(tracks)} tracks")
        if not tracks:
            print("No tracks found.")
            return

        synced_files = []

        for t in tracks:
            created = update_or_create_activity(self.session, t.to_namedtuple())
            if created:
                sys.stdout.write("+")
            else:
                sys.stdout.write(".")
            synced_files.extend(t.file_names)
            sys.stdout.flush()

        save_synced_data_file_list(synced_files)
        self.session.commit()

    def sync_from_garmin_meta(self, meta_file, data_dir, file_suffix="gpx"):
        import json
        from collections import namedtuple

        if not os.path.exists(meta_file):
            print(f"Meta file {meta_file} not found, fallback to directory sync.")
            return self.sync_from_data_dir(data_dir, file_suffix=file_suffix)

        with open(meta_file, "r") as f:
            garmin_meta = json.load(f)

        loader = track_loader.TrackLoader()
        # track_map: run_id -> track_object
        tracks = loader.load_tracks(data_dir, file_suffix=file_suffix)
        track_map = {str(t.run_id): t for t in tracks}
        print(f"Loaded {len(tracks)} GPX tracks for mapping.")

        print(f"Processing {len(garmin_meta)} official Garmin activities...")
        synced_files = []

        # Mock object to satisfy update_or_create_activity
        FakeMap = namedtuple("FakeMap", ["summary_polyline"])
        FakeTrack = namedtuple(
            "FakeTrack",
            [
                "id",
                "name",
                "type",
                "distance",
                "moving_time",
                "elapsed_time",
                "average_heartrate",
                "average_speed",
                "start_date",
                "start_date_local",
                "start_latlng",
                "location_country",
                "map",
                "source",
            ],
        )

        for run_id, meta in garmin_meta.items():
            run_id_int = int(run_id)
            distance = float(meta.get("distance", 0) or 0)
            duration = int(meta.get("duration", 0) or 0)
            duration_delta = datetime.timedelta(seconds=duration)
            name = meta.get("name", "Running")
            start_date_str = meta.get("startTimeGMT", "")
            start_date_local_str = meta.get("startTimeLocal", "")
            
            if not start_date_str:
                print(f"Skipping activity {run_id} due to missing startTimeGMT.")
                continue

            # Ensure consistent date formatting for Generator.load
            try:
                dt = datetime.datetime.strptime(start_date_str, "%Y-%m-%d %H:%M:%S")
                dt_local = datetime.datetime.strptime(start_date_local_str, "%Y-%m-%d %H:%M:%S") if start_date_local_str else dt
                # start_date for DB usually expects ISO, start_date_local expects Y-m-d H:M:S
                start_date_db = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                start_date_local_db = dt_local.strftime("%Y-%m-%d %H:%M:%S")
            except Exception as e:
                print(f"Skipping activity {run_id} due to invalid time format: {start_date_str}")
                continue

            # Map official type to internally recognized types
            meta_type = meta.get("type", "running")
            activity_type = TYPE_DICT.get(meta_type, "Run")

            if str(run_id) in track_map:
                t = track_map[str(run_id)]
                # Force official data override
                t.length = distance
                t.moving_time = duration_delta
                # Override internal dates to match metadata truth
                t.start_time = dt
                t.start_time_local = dt_local
                # Ensure type is also updated to official mapping
                t.activity_type = activity_type
                activity_data = t.to_namedtuple()
                synced_files.extend(t.file_names)
            else:
                # Create a "virtual" activity for missing GPX
                activity_data = FakeTrack(
                    id=run_id_int,
                    name=name,
                    type=activity_type,
                    distance=distance,
                    moving_time=duration_delta,
                    elapsed_time=duration_delta,
                    average_heartrate=meta.get("average_heartrate", 0),
                    average_speed=meta.get("average_speed", 0),
                    start_date=start_date_db,
                    start_date_local=start_date_local_db,
                    start_latlng=None,
                    location_country="",
                    map=FakeMap(summary_polyline=""),
                    source="garmin",
                )
            created = update_or_create_activity(self.session, activity_data)
            if created:
                sys.stdout.write("+")
            else:
                sys.stdout.write(".")
            sys.stdout.flush()

        self.session.commit()
        if synced_files:
            save_synced_data_file_list(synced_files)
        print(f"\nSynced {len(garmin_meta)} activities (Absolute Garmin Truth).")

        self.session.commit()

    def sync_from_kml_track(self, track):
        created = update_or_create_activity(self.session, track.to_namedtuple())
        if created:
            sys.stdout.write("+")
        else:
            sys.stdout.write(".")
        sys.stdout.flush()

        self.session.commit()

    def sync_from_app(self, app_tracks):
        if not app_tracks:
            print("No tracks found.")
            return
        print("Syncing tracks '+' means new track '.' means update tracks")
        synced_files = []
        for t in app_tracks:
            created = update_or_create_activity(self.session, t)
            if created:
                sys.stdout.write("+")
            else:
                sys.stdout.write(".")
            if "file_names" in t:
                synced_files.extend(t.file_names)
            sys.stdout.flush()

        self.session.commit()

    def load(self):
        activities = (
            self.session.query(Activity)
            .filter(Activity.distance > 0.1)
            .order_by(Activity.start_date_local)
        )
        activity_list = []

        streak = 0
        last_date = None
        for activity in activities:
            if self.only_run and activity.type != "Run":
                continue
            # Determine running streak.
            try:
                date = datetime.datetime.strptime(
                    activity.start_date_local, "%Y-%m-%d %H:%M:%S"
                ).date()
            except Exception as e:
                print(f"Skipping activity {activity.run_id} due to invalid start_date_local: {activity.start_date_local}")
                continue

            if last_date is None:
                streak = 1
            elif date == last_date:
                pass
            elif date == last_date + datetime.timedelta(days=1):
                streak += 1
            else:
                assert date > last_date
                streak = 1
            activity.streak = streak
            last_date = date
            if not IGNORE_BEFORE_SAVING:
                activity.summary_polyline = filter_out(activity.summary_polyline)
            activity_list.append(activity.to_dict())

        return activity_list

    def loadForMapping(self):
        activities = (
            self.session.query(Activity)
            .filter(Activity.type.in_(MAPPING_TYPE))
            .order_by(Activity.start_date_local)
        )
        activity_list = []

        streak = 0
        last_date = None
        for activity in activities:
            # Determine running streak.
            # if activity.type == "Run" or activity.type == "Walk"
            try:
                date = datetime.datetime.strptime(
                    activity.start_date_local, "%Y-%m-%d %H:%M:%S"
                ).date()
            except Exception as e:
                print(f"Skipping activity {activity.run_id} due to invalid start_date_local: {activity.start_date_local}")
                continue
            if last_date is None:
                streak = 1
            elif date == last_date:
                pass
            elif date == last_date + datetime.timedelta(days=1):
                streak += 1
            else:
                assert date > last_date
                streak = 1
            activity.streak = streak
            last_date = date
            activity_list.append(activity.to_dict())

        return activity_list

    def get_old_tracks_ids(self):
        try:
            activities = self.session.query(Activity).all()
            return [str(a.run_id) for a in activities]
        except Exception as e:
            # pass the error
            print(f"something wrong with {str(e)}")
            return []
