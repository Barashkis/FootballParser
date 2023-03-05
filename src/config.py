from os import getenv
from dotenv import load_dotenv
from faker import Faker

from src.mysql import Database

load_dotenv()

host = getenv("DB_HOST")
user = getenv("DB_USER")
password = getenv("DB_PASSWORD")
database = getenv("DB_NAME")
clubs_logo_folder = getenv("CLUBS_LOGO_FOLDER")
players_photo_folder = getenv("PLAYERS_PHOTO_FOLDER")


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


db = Database()
