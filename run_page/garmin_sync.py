"""
Python 3 API wrapper for Garmin Connect to get your statistics.
Copy most code from https://github.com/cyberjunky/python-garminconnect
"""

import argparse
import asyncio
import json
import logging
import os
import random
import sys
import time
import traceback
import zipfile
from io import BytesIO

import aiofiles
import cloudscraper
import garth
import httpx
from config import FOLDER_DICT, GARMIN_META_FILE, JSON_FILE, SQL_FILE, config

# Patch garth to use a browser User-Agent to bypass bot detection
garth.http.USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"

from garmin_device_adaptor import wrap_device_info
from utils import make_activities_file_only

# logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

TIME_OUT = httpx.Timeout(240.0, connect=360.0)
GARMIN_COM_URL_DICT = {
    "SSO_URL_ORIGIN": "https://sso.garmin.com",
    "SSO_URL": "https://sso.garmin.com/sso",
    "MODERN_URL": "https://connectapi.garmin.com",
    "SIGNIN_URL": "https://sso.garmin.com/sso/signin",
    "UPLOAD_URL": "https://connectapi.garmin.com/upload-service/upload/",
    "ACTIVITY_URL": "https://connectapi.garmin.com/activity-service/activity/{activity_id}",
}

GARMIN_CN_URL_DICT = {
    "SSO_URL_ORIGIN": "https://sso.garmin.com",
    "SSO_URL": "https://sso.garmin.cn/sso",
    "MODERN_URL": "https://connectapi.garmin.cn",
    "SIGNIN_URL": "https://sso.garmin.cn/sso/signin",
    "UPLOAD_URL": "https://connectapi.garmin.cn/upload-service/upload/",
    "ACTIVITY_URL": "https://connectapi.garmin.cn/activity-service/activity/{activity_id}",
}

# set to True if you want to sync all-time activities
GET_ALL = False


class Garmin:
    def __init__(self, secret_string, auth_domain, is_only_running=False):
        """
        Init module
        """
        self.cf_req = cloudscraper.create_scraper()
        self.URL_DICT = (
            GARMIN_CN_URL_DICT
            if auth_domain and str(auth_domain).upper() == "CN"
            else GARMIN_COM_URL_DICT
        )
        if auth_domain and str(auth_domain).upper() == "CN":
            garth.configure(domain="garmin.cn")
        self.modern_url = self.URL_DICT.get("MODERN_URL")
        garth.client.loads(secret_string)
        if garth.client.oauth2_token.expired:
            garth.client.refresh_oauth2()

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            "origin": self.URL_DICT.get("SSO_URL_ORIGIN"),
            "nk": "NT",
            "Authorization": str(garth.client.oauth2_token),
        }
        self.is_only_running = is_only_running
        self.upload_url = self.URL_DICT.get("UPLOAD_URL")
        self.activity_url = self.URL_DICT.get("ACTIVITY_URL")

    async def fetch_data(self, url, retrying=False):
        """
        Fetch and return data using cloudscraper to bypass Cloudflare
        """
        try:
            # Shift to synchronous cloudscraper (running in thread to stay async-compatible)
            # Or just use it directly since it is more reliable for 429 bypass
            response = self.cf_req.get(url, headers=self.headers)
            if response.status_code == 429:
                raise GarminConnectTooManyRequestsError("Too many requests from Garmin")
            
            logger.debug(f"fetch_data got response code {response.status_code}")
            response.raise_for_status()
            return response.json()
        except Exception as err:
            print(f"Error fetching data: {err}")
            if retrying:
                logger.debug(
                    "Exception occurred during data retrieval, relogin without effect: %s"
                    % err
                )
                raise GarminConnectConnectionError("Error connecting") from err
            else:
                logger.debug(
                    "Exception occurred during data retrieval - perhaps session expired - trying relogin: %s"
                    % err
                )
                return await self.fetch_data(url, retrying=True)

    async def get_activities(self, start, limit):
        """
        Fetch available activities
        """
        url = f"{self.modern_url}/activitylist-service/activities/search/activities?start={start}&limit={limit}"
        if self.is_only_running:
            url = url + "&activityType=running"
        return await self.fetch_data(url)

    async def download_activity(self, activity_id, file_type="gpx"):
        url = f"{self.modern_url}/download-service/export/{file_type}/activity/{activity_id}"
        if file_type == "fit":
            url = f"{self.modern_url}/download-service/files/activity/{activity_id}"
        logger.info(f"Download activity from {url}")
        
        # Using cloudscraper for downloads as well
        response = self.cf_req.get(url, headers=self.headers)
        response.raise_for_status()
        return response.content

    async def upload_activities_original(self, datas, use_fake_garmin_device=False):
        print(
            "start upload activities to garmin!, use_fake_garmin_device:",
            use_fake_garmin_device,
        )
        for data in datas:
            print(data.filename)
            with open(data.filename, "wb") as f:
                for chunk in data.content:
                    f.write(chunk)
            f = open(data.filename, "rb")
            # wrap fake garmin device to origin fit file, current not support gpx file
            if use_fake_garmin_device:
                file_body = wrap_device_info(f)
            else:
                file_body = BytesIO(f.read())
            files = {"file": (data.filename, file_body)}

            try:
                # Using cloudscraper for uploads
                res = self.cf_req.post(
                    self.upload_url, files=files, headers=self.headers
                )
                os.remove(data.filename)
                f.close()
            except Exception as e:
                print(str(e))
                # just pass for now
                continue
            try:
                resp = res.json()["detailedImportResult"]
                print("garmin upload success: ", resp)
            except Exception as e:
                print("garmin upload failed: ", e)
        # cloudscraper doesn't need explicit close like httpx AsyncClient


class GarminConnectHttpError(Exception):
    def __init__(self, status):
        super(GarminConnectHttpError, self).__init__(status)
        self.status = status


class GarminConnectConnectionError(Exception):
    """Raised when communication ended in error."""

    def __init__(self, status):
        """Initialize."""
        super(GarminConnectConnectionError, self).__init__(status)
        self.status = status


class GarminConnectTooManyRequestsError(Exception):
    """Raised when rate limit is exceeded."""

    def __init__(self, status):
        """Initialize."""
        super(GarminConnectTooManyRequestsError, self).__init__(status)
        self.status = status


class GarminConnectAuthenticationError(Exception):
    """Raised when login returns wrong result."""

    def __init__(self, status):
        """Initialize."""
        super(GarminConnectAuthenticationError, self).__init__(status)
        self.status = status


def build_garmin_client(secret_string, auth_domain, is_only_running=False):
    if secret_string is None or not str(secret_string).strip():
        raise GarminConnectAuthenticationError(
            "GARMIN_SECRET_STRING is missing. "
            "Set GARMIN_SECRET_STRING or generate a new one with "
            "run_page/get_garmin_secret.py."
        )

    try:
        return Garmin(secret_string, auth_domain, is_only_running)
    except Exception as err:
        raise GarminConnectAuthenticationError(
            "Unable to authenticate with Garmin using the provided secret string. "
            "The secret may be expired, revoked, or malformed. "
            "Generate a new secret with run_page/get_garmin_secret.py and update "
            "GARMIN_SECRET_STRING."
        ) from err


async def download_garmin_data(client, activity_id, file_type="gpx"):
    # Add random jitter to avoid 429
    await asyncio.sleep(random.uniform(1.0, 3.0))
    folder = FOLDER_DICT.get(file_type, "gpx")
    try:
        file_data = await client.download_activity(activity_id, file_type=file_type)
        file_path = os.path.join(folder, f"{activity_id}.{file_type}")
        need_unzip = False
        if file_type == "fit":
            file_path = os.path.join(folder, f"{activity_id}.zip")
            need_unzip = True
        async with aiofiles.open(file_path, "wb") as fb:
            await fb.write(file_data)
        if need_unzip:
            zip_file = zipfile.ZipFile(file_path, "r")
            for file_info in zip_file.infolist():
                zip_file.extract(file_info, folder)
                os.rename(
                    os.path.join(folder, f"{activity_id}_ACTIVITY.fit"),
                    os.path.join(folder, f"{activity_id}.fit"),
                )
            os.remove(file_path)
    except Exception as e:
        print(f"Failed to download activity {activity_id}: {str(e)}")
        traceback.print_exc()


async def get_activity_id_list(client, start=0):
    limit = 100 if GET_ALL else 20
    activities = await client.get_activities(start, limit)
    if not activities:
        return []

    ids = [str(a.get("activityId", "")) for a in activities if a.get("activityId")]
    print("Syncing Activity IDs")
    if GET_ALL:
        return ids + await get_activity_id_list(client, start + limit)
    return ids


def _extract_activity_meta(activity):
    activity_id = str(activity.get("activityId", "")).strip()
    if not activity_id:
        return None, None
    activity_type = activity.get("activityType", {}) or {}
    return activity_id, {
        "distance": activity.get("distance"),
        "movingDuration": activity.get("movingDuration"),
        "duration": activity.get("duration"),
        "elapsedDuration": activity.get("elapsedDuration"),
        "name": activity.get("activityName"),
        "type": activity_type.get("typeKey"),
        "startTimeLocal": activity.get("startTimeLocal"),
        "startTimeGMT": activity.get("startTimeGMT"),
    }


async def get_activity_meta_map(client, start=0):
    limit = 100 if GET_ALL else 20
    activities = await client.get_activities(start, limit)
    if not activities:
        return {}

    meta_map = {}
    for activity in activities:
        activity_id, meta = _extract_activity_meta(activity)
        if activity_id:
            meta_map[activity_id] = meta

    if GET_ALL:
        meta_map.update(await get_activity_meta_map(client, start + limit))
    return meta_map


def save_activity_meta_map(meta_map):
    if not meta_map:
        return
    old_meta = {}
    if os.path.exists(GARMIN_META_FILE):
        try:
            with open(GARMIN_META_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    old_meta = loaded
        except Exception:
            pass

    old_meta.update(meta_map)
    with open(GARMIN_META_FILE, "w", encoding="utf-8") as f:
        json.dump(old_meta, f, ensure_ascii=False)


async def gather_with_concurrency(n, tasks):
    semaphore = asyncio.Semaphore(n)

    async def sem_task(task):
        async with semaphore:
            return await task

    return await asyncio.gather(*(sem_task(task) for task in tasks))


def get_downloaded_ids(folder):
    return [i.split(".")[0] for i in os.listdir(folder) if not i.startswith(".")]


async def download_new_activities(
    secret_string, auth_domain, downloaded_ids, is_only_running, folder, file_type
):
    client = build_garmin_client(secret_string, auth_domain, is_only_running)
    activity_meta_map = await get_activity_meta_map(client)
    save_activity_meta_map(activity_meta_map)
    # because I don't find a para for after time, so I use garmin-id as filename
    # to find new run to generage
    activity_ids = list(activity_meta_map.keys()) or await get_activity_id_list(client)
    to_generate_garmin_ids = sorted(list(set(activity_ids) - set(downloaded_ids)))
    print(f"{len(to_generate_garmin_ids)} new activities to be downloaded")

    start_time = time.time()
    if options.summary_only:
        print("Summary only mode: Metadata saved. Skipping GPX/FIT downloads.")
        client.cf_req.close()
        return []

    await gather_with_concurrency(
        10,
        [
            download_garmin_data(client, id, file_type=file_type)
            for id in to_generate_garmin_ids
        ],
    )
    print(f"Download finished. Elapsed {time.time()-start_time} seconds")

    # cloudscraper scraper is a requests.Session, no need to await aclose
    client.cf_req.close()
    return to_generate_garmin_ids


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "secret_string", nargs="?", help="secret_string fro get_garmin_secret.py"
    )
    parser.add_argument(
        "--is-cn",
        dest="is_cn",
        action="store_true",
        help="if garmin accout is cn",
    )
    parser.add_argument(
        "--only-run",
        dest="only_run",
        action="store_true",
        help="if is only for running",
    )
    parser.add_argument(
        "--tcx",
        dest="download_file_type",
        action="store_const",
        const="tcx",
        default="gpx",
        help="to download personal documents or ebook",
    )
    parser.add_argument(
        "--fit",
        dest="download_file_type",
        action="store_const",
        const="fit",
        default="gpx",
        help="to download personal documents or ebook",
    )
    parser.add_argument(
        "--summary-only",
        dest="summary_only",
        action="store_true",
        help="only sync activity summary metadata, skip files download",
    )
    options = parser.parse_args()
    secret_string = options.secret_string
    auth_domain = (
        "CN" if options.is_cn else config("sync", "garmin", "authentication_domain")
    )
    file_type = options.download_file_type
    is_only_running = options.only_run
    if secret_string is None:
        print("Missing argument nor valid configuration file")
        sys.exit(1)
    folder = FOLDER_DICT.get(file_type, "gpx")
    # make gpx or tcx dir
    if not os.path.exists(folder):
        os.mkdir(folder)
    downloaded_ids = get_downloaded_ids(folder)

    try:
        loop = asyncio.get_event_loop()
        future = asyncio.ensure_future(
            download_new_activities(
                secret_string,
                auth_domain,
                downloaded_ids,
                is_only_running,
                folder,
                file_type,
            )
        )
        loop.run_until_complete(future)
        # ⚠️ Restore Data accuracy: use make_activities_file instead of make_activities_file_only
        # This ensures all activities > 0.1km are included, avoiding restrictive mapping filters.
        from utils import make_activities_file
        make_activities_file(SQL_FILE, folder, JSON_FILE, garmin_meta_file=GARMIN_META_FILE, file_suffix=file_type)
    except GarminConnectAuthenticationError as err:
        print(str(err))
        sys.exit(1)
