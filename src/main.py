import requests
import time
import random
import instaloader
import os
import glob

hook_url = os.getenv("HOOK_URL")
USER = os.getenv("USER")
profileNames = os.getenv("PROFILE_NAMES").split(",")

if not hook_url or not USER or not profileNames:
    raise ValueError(
        "HOOK_URL and USER and profileNames environment variables must be set."
    )

# Get instance


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


L = instaloader.Instaloader(
    save_metadata=False,
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
            send_image(file)
            os.remove(file)


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
