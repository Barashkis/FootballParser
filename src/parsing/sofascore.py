import time
from pathlib import Path

import requests

from bs4 import BeautifulSoup
from pywebio.output import put_text

from src.config import db, sofascore_headers, clubs_logo_folder
from src.webdriver import get_driver


def parse_sofascore(nation_name):
    put_text("Сбор необходимых API id всех лиг выбранной страны...")

    sofascore_leagues_dict = {}

    sofascore_nations = requests.get("https://api.sofascore.com/api/v1/sport/football/categories", headers=sofascore_headers()) \
        .json()["categories"]
    for nation in sofascore_nations:
        if nation["name"].lower() in [nation_name.lower(), f"{nation_name.lower()} amateur"]:
            sofascore_leagues = requests.get(f"https://api.sofascore.com/api/v1/category/{nation['id']}"
                                             f"/unique-tournaments", headers=sofascore_headers()) \
                .json()["groups"][0]["uniqueTournaments"]
            sofascore_leagues_dict.update({league["id"]: league["slug"] for league in sofascore_leagues})

    nation_id = db.select("nations", False, "ID", name_en=nation_name)["ID"]
    db_leagues = db.select("organizations", True, "sofascore_id", "ID", nation_id=nation_id)

    clubs = {}
    for db_league in db_leagues:
        driver = get_driver()

        db_league_sofascore_id = db_league["sofascore_id"]
        league_id = db_league["ID"]
        if db_league_sofascore_id not in sofascore_leagues_dict.keys():
            continue

        put_text(f"Сбор всех API id лиги с sofascore_id = {db_league_sofascore_id}...")

        try:
            driver.get(f"https://www.sofascore.com/tournament/football/{nation_name.lower()}/"
                       f"{sofascore_leagues_dict[db_league_sofascore_id]}/{db_league_sofascore_id}")

            time.sleep(30)

            soup = BeautifulSoup(driver.page_source, "lxml")
            club_tables = soup.find_all("div", {"class": ["sc-526d246a-8", "eEyhLI"]})
            link_blocks = [table.find_all("a") for table in club_tables]
            with requests.Session() as session:
                for link_block in link_blocks:
                    for link in link_block:
                        uri = link.get("href")
                        if uri:
                            if "/team/football/" in uri:
                                club_sofascore_id = int(uri.split("/")[-1])
                                if club_sofascore_id in clubs:
                                    clubs[club_sofascore_id]["league_ids"].append((db_league_sofascore_id, league_id))
                                club_page = session.get(f"https://www.sofascore.com/team/football/valencia/{club_sofascore_id}",
                                                        headers=sofascore_headers()).text
                                soup = BeautifulSoup(club_page, "lxml")
                                for div in soup.find_all("div", class_="hTmmUs"):
                                    try:
                                        details_id = div.find("a").get("data-id")
                                    except AttributeError:
                                        continue

                                    clubs[club_sofascore_id] = {
                                        "details_id": details_id,
                                        "league_ids": [(db_league_sofascore_id, league_id)]
                                    }

                                    break
        except:
            continue
        finally:
            driver.close()
            driver.quit()

    put_text(f"Обработка информации о всех клубах ({len(clubs)} шт.)...")

    for num, club_sofascore_id in enumerate(clubs, start=1):
        put_text(f"{num}. Обработка информации о клубе с sofascore_id = {club_sofascore_id}...")

        with requests.Session() as session:
            try:
                image = session.get(f"https://api.sofascore.app/api/v1/team/{club_sofascore_id}/image",
                                    headers=sofascore_headers()).content
            except:
                time.sleep(120)

                continue

            stadium_name = ''
            city_name = ''

            event = session.get(f"https://api.sofascore.com/api/v1/event/{clubs[club_sofascore_id]['details_id']}",
                                headers=sofascore_headers()).json()["event"]
            for key in ["homeTeam", "awayTeam"]:
                club_details = event[key]
                if club_sofascore_id == club_details["id"]:
                    club_name = club_details["name"]

                    venue = club_details.get("venue")
                    if venue:
                        stadium = venue.get("stadium")
                        if stadium:
                            stadium_name = stadium["name"]

                        city = venue.get("city")
                        if city:
                            city_name = city["name"]

                    break

            if city_name:
                db_city = db.select("cities", False, "ID", name_en=city_name, nation_id=nation_id)
                if not db_city:
                    db.insert(
                        "cities",
                        nation_id=f"{nation_id}",
                        name_en="'" + city_name.replace("\'", "\'\'") + "'",
                        name_es="'" + city_name.replace("\'", "\'\'") + "'",
                        name_fr="'" + city_name.replace("\'", "\'\'") + "'",
                        latitude=0,
                        longitude=0
                    )
                    city_id = db.select("cities", False, "ID", name_en=city_name, nation_id=nation_id)["ID"]
                else:
                    city_id = db_city["ID"]
            else:
                city_id = 0

            if stadium_name:
                db_stadium = db.select("facilities", False, "ID", name=stadium_name, city_id=city_id)
                if not db_stadium:
                    db.insert(
                        "facilities",
                        name="'" + stadium_name.replace("\'", "\'\'") + "'",
                        facility_type="'stadium'",
                        description="''",
                        owner_id=0,
                        city_id=city_id,
                        city_text="''",
                        country_id=nation_id,
                        latitude=0,
                        longitude=0
                    )
                    stadium_id = db.select("facilities", False, "ID", name=stadium_name, city_id=city_id)["ID"]
                else:
                    stadium_id = db_stadium["ID"]
            else:
                stadium_id = 0

            league_ids = clubs[club_sofascore_id]["league_ids"]
            league_id = league_ids[0][1]

            club = db.select("clubs", False, name=club_name, league_id=league_id)
            if club:
                if len(league_ids) > 1:
                    initial_db_league_data = db.select("organizations", False, "tier", "sofascore_id", sofascore_id=league_ids[0][0])

                    min_tier = initial_db_league_data["tier"]
                    league_id = initial_db_league_data["ID"]
                    for league_ids_tuple in league_ids[1:]:
                        db_league_data = db.select("organizations", False, "tier", "sofascore_id", sofascore_id=league_ids_tuple[0])
                        league_tier = db_league_data["tier"]
                        if league_tier < min_tier:
                            min_tier = league_tier
                            league_id = db_league_data["ID"]

                db_league_id = club["league_id"]
                if db_league_id:
                    if db_league_id != league_id:
                        db.update("clubs", {"league_id": league_id}, {"name": club_name, "league_id": league_id})
                else:
                    db.update("clubs", {"league_id": league_id}, {"name": club_name, "league_id": league_id})

                if club["stadium_id"] != stadium_id:
                    db.update("clubs", {"stadium_id": stadium_id}, {"name": club_name, "league_id": league_id})
            else:
                db.insert(
                    "clubs",
                    name="'" + club_name.replace("\'", "\'\'") + "'",
                    league="''",
                    tm_id=0,
                    website="''",
                    base_id=0,
                    academy_id=0,
                    start_index=4.00,
                    league_id=league_id,
                    stadium_id=stadium_id,
                    city_id=city_id,
                    sofascore_id=club_sofascore_id
                )

            club_id = db.select("clubs", False, "ID", name=club_name, league_id=league_id)["ID"]
            image_path = str(Path(*clubs_logo_folder.split(), f"{club_id}.png"))
            with open(image_path, "wb") as file:
                file.write(image)

            time.sleep(1)
