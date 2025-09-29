import requests
import time
import random
import instaloader
import os
import glob
import json

hook_url = os.getenv("HOOK_URL")
USER = os.getenv("USER")
profileNames = os.getenv("PROFILE_NAMES")

if not hook_url or not USER or not profileNames:
    raise ValueError(
        "HOOK_URL and USER and profileNames environment variables must be set."
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
        else:
            print(f"Failed to send {file_path}. Status code: {response.status_code}")


L = instaloader.Instaloader(
    save_metadata=True,
    compress_json=False,
    download_video_thumbnails=False,
)
L.load_session_from_file(USER, "./config/session-" + USER)  # (login)
profiles = [instaloader.Profile.from_username(L.context, name) for name in profileNames]


def main():
    L.download_stories(
        userids=profiles,
        filename_target="stories",
        latest_stamps=instaloader.LatestStamps("./config/latest_stamps.txt"),
    )
    # find all files in stories folder and send them to discord and delete them

    files = glob.glob("stories/*")
    if files:
        send_webhook_message("@here")
        for file in files:
            if file.endswith(".json"):
                continue  # skip meta files directly
            username, story_id, timestamp = get_story_info(file)
            send_image_with_username(file, username, story_id, timestamp)

            os.remove(file)
            base, _ = os.path.splitext(file)
            meta_file = base + ".json"
            if os.path.exists(meta_file):
                os.remove(meta_file)


if __name__ == "__main__":
    try:
        while True:
            main()
            sleepTime = random.randint(30 * 60, 60 * 60)
            print(f"Waiting for {int(sleepTime/60)} mins {sleepTime%60} secs")
            time.sleep(sleepTime)  # wait between 30 minutes to 1 hour
    except KeyboardInterrupt:
        print("Program terminated by user.")
    except Exception as e:
        send_webhook_message(f"Program terminated with error: {e}")
        print(f"Program terminated with error: {e}")
