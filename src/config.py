from os import getenv
from pathlib import Path

from dotenv import load_dotenv
from faker import Faker
import pysftp

from src.mysql import Database

load_dotenv()

host = getenv("HOST")
host_user = getenv("HOST_USER")
host_password = getenv("HOST_PASSWORD")

host_clubs_logo_folder = str(Path(*getenv("HOST_CLUBS_LOGO_FOLDER").split()))
host_players_photo_folder = str(Path(*getenv("HOST_PLAYERS_PHOTO_FOLDER").split()))

local_clubs_logo_folder = getenv("LOCAL_CLUBS_LOGO_FOLDER").split()
local_players_photo_folder = getenv("LOCAL_PLAYERS_PHOTO_FOLDER").split()

user = getenv("DB_USER")
password = getenv("DB_PASSWORD")
database = getenv("DB_NAME")


def sofascore_headers():
    headers = {
        "authority": "api.sofascore.com",
        "method": "GET",
        "scheme": "https",
        "accept": "*/*",
        "origin": "https://www.sofascore.com",
        "referer": "https://www.sofascore.com/",
        "sec-fetch-site": "same-site",
        "user-agent": Faker().chrome()
    }

    return headers


def transfermarkt_headers():
    headers = {
        "accept": "*/*",
        "origin": "https://www.transfermarkt.com",
        "referer": "https://www.transfermarkt.com/",
        "user-agent": Faker().chrome()
    }

    return headers


def upload_image(host_folder_path, local_image_path):
    with pysftp.Connection(host=host, username=host_user, password=host_password) as sftp:
        sftp.cwd(host_folder_path)
        sftp.put(localpath=local_image_path)


db = Database()
