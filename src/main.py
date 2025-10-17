import requests
import time
import random
import instaloader
import os
import glob
import json
import datetime

# from dotenv import load_dotenv

# load_dotenv()  # take environment variables from .env.
hook_url = os.getenv("HOOK_URL")
USER = os.getenv("USER")
profileNames = os.getenv("PROFILE_NAMES")
user_agent = os.getenv("USER_AGENT")
KAPPA_UPLOAD_THRESHOLD_MB = int(os.getenv("KAPPA_UPLOAD_THRESHOLD_MB", 10))  # 10MB
if not hook_url or not USER or not profileNames or not user_agent:
    raise ValueError(
        "HOOK_URL and USER and profileNames and user_agent environment variables must be set."
    )
profileNames = profileNames.split(",")


def send_image(file_url):
    with open(file_url, "rb") as f:
        files = {"file": f}
        response = requests.post(hook_url, files=files)
        if response.status_code == 200:
            print("Image sent successfully.")

        else:
            print(f"Failed to send image. Status code: {response.status_code}")


def send_webhook_message(content):
    data = {"content": content}
    response = requests.post(hook_url, json=data)
    if response.status_code == 204:
        print("Message sent successfully.")
    else:
        print(f"Failed to send message. Status code: {response.status_code}")


def get_story_info(media_file):
    """Extract username, story_id, and taken_at_timestamp from metadata"""
    base, _ = os.path.splitext(media_file)
    meta_file = base + ".json"
    if not os.path.exists(meta_file):
        return None, None, None

    with open(meta_file, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            node = data.get("node", {})
            username = node.get("owner", {}).get("username")
            story_id = node.get("id")
            timestamp = node.get("taken_at_timestamp")
            return username, story_id, timestamp
        except Exception as e:
            print(f"Error reading meta for {media_file}: {e}")
            return None, None, None


def send_image_with_username(file_path, username, story_id, timestamp):
    """Send the media with clickable story link + timestamp"""
    with open(file_path, "rb") as f:
        files = {"file": f}
        profile_url = f"https://instagram.com/stories/{username}/{story_id}"
        data = {
            "content": f"Posted by: [**{username}**](<{profile_url}>) (<t:{timestamp}:R>)"
        }
        response = requests.post(hook_url, data=data, files=files)
        if response.status_code in (200, 204):
            print(f"Sent {file_path} from {username}")
            return True
        else:
            print(f"Failed to send {file_path}. Status code: {response.status_code}")
            return False


class MyRateController(instaloader.RateController):
    def wait_before_query(self, query_type):
        wait_time = random.randint(30, 120)
        print(f"Waiting for {wait_time} seconds before next query...")
        self.sleep(wait_time)
        super().wait_before_query(query_type)


def extract_datetime_from_filename(filename):
    """Extract datetime from filename like '2025-10-03_10-07-54_UTC'."""
    base = os.path.basename(filename)
    name, _ = os.path.splitext(base)
    try:
        dt_str = name.split("_UTC")[0]  # Remove _UTC and extension
        dt = datetime.datetime.strptime(dt_str, "%Y-%m-%d_%H-%M-%S")
        return dt
    except Exception:
        return datetime.datetime.max  # fallback: put unparseable files last


def upload_to_kappa_lol(file_path):
    """
    Uploads a file to https://kappa.lol/api/upload and returns the JSON response.
    """
    url = "https://kappa.lol/api/upload"
    with open(file_path, "rb") as f:
        files = {"file": f}
        response = requests.post(url, files=files)
        if response.status_code == 200:
            try:
                return response.json()
            except Exception as e:
                print(f"Failed to parse kappa.lol response: {e}")
                return None
        else:
            print(f"Failed to upload to kappa.lol. Status code: {response.status_code}")
            return None


def send_with_kappa_link(file_path, username, story_id, timestamp):
    """
    Uploads the file to kappa.lol and sends a Discord embed with the kappa link and story info.
    """
    kappa_resp = upload_to_kappa_lol(file_path)
    if (
        not kappa_resp
        or "link" not in kappa_resp
        or "id" not in kappa_resp
        or "ext" not in kappa_resp
    ):
        print("Failed to upload to kappa.lol or missing link/id/ext.")
        return False

    kappa_url = kappa_resp["link"]
    # Use direct image URL for Discord embed image
    profile_url = f"https://instagram.com/stories/{username}/{story_id}"
    data = {
        "content": f"Posted by: [**{username}**](<{profile_url}>) (<t:{timestamp}:R>)\n[Open on kappa.lol]({kappa_url})",
    }
    response = requests.post(hook_url, json=data)
    if response.status_code in (200, 204):
        print(f"Sent {file_path} from {username} ({kappa_url})")
        return True
    else:
        print(f"Failed to send {file_path}. Status code: {response.status_code}")
        return False


def main(L: instaloader.Instaloader, profiles: list[instaloader.Profile]):
    L.download_stories(
        userids=profiles,
        filename_target="stories",
        latest_stamps=instaloader.LatestStamps("./config/latest_stamps.txt"),
    )
    # find all files in stories folder and send them to discord and delete them

    files = glob.glob("stories/*")
    if files:
        # Sort by datetime in filename (oldest first)
        files = sorted(files, key=extract_datetime_from_filename)
        send_webhook_message("@here")
        for file in files:
            if file.endswith(".json"):
                continue  # skip meta files directly
            username, story_id, timestamp = get_story_info(file)
            file_size = os.path.getsize(file)
            if file_size > KAPPA_UPLOAD_THRESHOLD_MB * 1024 * 1024:
                sent = send_with_kappa_link(file, username, story_id, timestamp)
            else:
                sent = send_image_with_username(file, username, story_id, timestamp)
                if not sent:
                    sent = send_with_kappa_link(file, username, story_id, timestamp)
            if sent:
                os.remove(file)
                base, _ = os.path.splitext(file)
                meta_file = base + ".json"
                if os.path.exists(meta_file):
                    os.remove(meta_file)


if __name__ == "__main__":
    try:
        L = instaloader.Instaloader(
            save_metadata=True,
            compress_json=False,
            download_video_thumbnails=False,
            user_agent=user_agent,
        )
        L.load_session_from_file(USER, "./config/session-" + USER)  # (login)
        logged_in = L.test_login()
        if logged_in is None:
            print("Session file expired, please re-login.")
            send_webhook_message(
                f"@here Session file expired for {USER}, please re-login."
            )
            while True:
                time.sleep(60 * 60)  # wait indefinitely
        print(f"Logged in as {logged_in}")
        profiles = [
            instaloader.Profile.from_username(L.context, name) for name in profileNames
        ]
        print(f"Tracking profiles: {', '.join(p.username for p in profiles)}")
        L2 = instaloader.Instaloader(
            save_metadata=True,
            compress_json=False,
            download_video_thumbnails=False,
            user_agent=user_agent,
            rate_controller=lambda ctx: MyRateController(ctx),
        )
        L2.load_session_from_file(USER, "./config/session-" + USER)  # (login)

        while True:
            main(L2, profiles)
            sleepTime = random.randint(60 * 60 * 1, 60 * 60 * 2)
            print(
                f"Waiting for {int(sleepTime/60/60)} hours {int((sleepTime/60)%60)} minutes {int(sleepTime%60)} seconds"
            )
            time.sleep(sleepTime)  # wait 6-12 hours
    except KeyboardInterrupt:
        print("Program terminated by user.")
    except Exception as e:
        send_webhook_message(f"@here Program terminated with error: {e}")
        print(f"Program terminated with error: {e}")
        input("Press Enter to exit...")
        exit(1)
