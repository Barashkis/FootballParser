import time

from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup
from requests import Session
from pywebio.output import put_text

from src.config import db, transfermarkt_headers, players_photo_folder


def convert_date(date_string):
    try:
        result = datetime.strptime(date_string, "%b %d, %Y").strftime("%Y-%m-%d")
    except ValueError:
        result = "0000-00-00"
    return result


def parse_transfermarkt(nation_name):
    put_text("Сбор tm_id всех лиг выбранной страны...")

    nation_id = db.select("nations", False, "ID", name_en=nation_name)["ID"]
    league_ids = tuple(league["ID"] for league in db.select("organizations", True, "ID", nation_id=nation_id))

    if len(league_ids) > 1:
        tms = db.custom_query(
            f"SELECT tm_id FROM clubs WHERE league_id IN {league_ids};",
            commit=False,
            fetchall=True,
            fetchone=False,
            parameters=tuple()
        )
    else:
        tms = db.select("clubs", True, "tm_id", league_id=league_ids[0])

    tm_ids = list(set([tm["tm_id"] for tm in tms]))

    players = set()
    for tm_id in tm_ids:
        if not tm_id:
            continue

        put_text(f"Сбор tm_id всех игроков клуба с tm_id = {tm_id}...")

        with Session() as session:
            players_response = session.get(f"https://www.transfermarkt.com/as-rom/startseite/verein/{tm_id}",
                                           headers=transfermarkt_headers())
            soup = BeautifulSoup(players_response.text, "lxml")

            try:
                items_tbody = soup.find("table", "items").find("tbody")
                items = items_tbody.find_all("tr", class_="even") + items_tbody.find_all("tr", class_="odd")
                for item in items:
                    players.add((item.find_all("td", recursive=False)[1].find_all("a")[-1].get("href"), tm_id))
            except:
                continue
            finally:
                time.sleep(10)

    put_text(f"Обработка информации о всех игроках ({len(players)} человек)...")

    for num, player in enumerate(players, start=1):
        player_uri, club_tm_id = player

        club = db.select("clubs", False, "ID", tm_id=club_tm_id)
        club_id = club["ID"] if club else 0
        player_tm_id = int(player_uri.split("/")[-1])

        put_text(f"{num}. Обработка игрока с tm_id = {player_tm_id}...")

        with Session() as session:
            player_response = session.get("https://www.transfermarkt.com" + player_uri,
                                          headers=transfermarkt_headers())
            soup = BeautifulSoup(player_response.text, "lxml")

            try:
                display_name = soup.find("h1", class_="data-header__headline-wrapper").text.strip()
                if "#" in display_name:
                    display_name = " ".join(display_name.strip().split()[1:]).replace("'", "''")
                else:
                    display_name = " ".join(display_name.split()).replace("'", "''")

                main_table = soup.find("div", {"class": ["info-table", "info-table--right-space"]})
                main_fields = [field.text.strip() for field in
                               main_table.find_all("span", class_="info-table__content--regular")]
                main_values = [value.text.strip() for value in
                               main_table.find_all("span", class_="info-table__content--bold")]

                home_country_name = ""
                birth_date = "0000-00-00"
                height = 0
                citizenships = ["", ""]
                company_text = ""
                foot = None
                contract_expires = "0000-00-00"
                joined = "0000-00-00"
                for main_field, main_value in zip(main_fields, main_values):
                    if main_field == "Name in home country:":
                        home_country_name = main_value.replace("'", "''")
                    elif main_field == "Date of birth:":
                        if "Happy Birthday" in main_value:
                            main_value = main_value.replace("Happy Birthday", "").strip()
                        birth_date = convert_date(main_value)
                    elif main_field == "Height:":
                        height = int(float(main_value.split()[0].replace(",", ".")) * 100)
                    elif main_field == "Foot:":
                        if main_value in ["left", "right", "both"]:
                            foot = main_value
                    elif main_field == "Citizenship:":
                        citizenships = main_value.split() + ["", ""]
                    elif main_field == "Current club:":
                        company_text = main_value.replace("'", "''")
                    elif main_field == "Contract expires:":
                        contract_expires = convert_date(main_value)
                    elif main_field == "Joined:":
                        joined = convert_date(main_value)

                try:
                    positions = [dd.text.strip() for dd in
                                 soup.find("div", class_="detail-position__box").find_all("dd")] + ["", "", ""]
                except AttributeError:
                    positions = ["", "", ""]

                position_ids = []
                for position in positions:
                    db_position = db.select("positions", False, "ID", name_en=position)
                    if db_position:
                        position_ids.append(db_position["ID"])
                    else:
                        position_ids.append(0)
                position_1, position_2, position_3 = position_ids[:3]

                citizenship_ids = []
                for citizenship in citizenships:
                    db_nation = db.select("nations", False, "ID", name_en=citizenship)
                    if db_nation:
                        citizenship_ids.append(db_nation["ID"])
                    else:
                        citizenship_ids.append(0)
                citizenship_1, citizenship_2 = citizenship_ids[:2]

                image_url = soup.find("img", class_="data-header__profile-image").get("src").split("?")[0]
                image = session.get(image_url, headers=transfermarkt_headers()).content
            except:
                time.sleep(120)

                continue
            finally:
                time.sleep(10)

            wp_user = db.select("wp_users", False, "ID", display_name=f"'{display_name}'",
                                name_home=f"'{home_country_name}'")
            if wp_user:
                wp_user_id = wp_user["ID"]

                db.update("wp_users",
                          {"citizenship2_id": citizenship_2, "country_id": nation_id},
                          {"ID": wp_user_id})
            else:
                wp_user_dict = {
                    "tm_id": player_tm_id,
                    "display_name": f"'{display_name}'",
                    "name": "''",
                    "middlename": "''",
                    "surname": "''",
                    "name_home": f"'{home_country_name}'",
                    "citizenship1_id": citizenship_1,
                    "citizenship2_id": citizenship_2,
                    "date_of_birth": f"'{birth_date}'",
                    "gender": "'male'",
                    "phone": "''",
                    "country_id": nation_id,
                    "city_id": 0,
                    "city_text": "''",
                    "address": "''",
                    "postal_code": 0
                }
                db.insert("wp_users", **wp_user_dict)
                wp_user_id = db.select("wp_users", False, "ID", tm_id=player_tm_id)["ID"]

            career = db.select("careers", False, object_id=wp_user_id)
            if career:
                db.update("careers",
                          {"company_text": f"'{company_text}'", "company_id": club_id,
                           "end_date": f"'{contract_expires}'", "start_date": f"'{joined}'"},
                          {"object_id": wp_user_id})
            else:
                career_dict = {
                    "role_id": 1,
                    "object_id": wp_user_id,
                    "start_date": f"'{joined}'",
                    "end_date": f"'{contract_expires}'",
                    "position": "'player'",
                    "team": "'Senior'",
                    "team_gender": "'male'",
                    "company_type": 1,
                    "company_id": club_id,
                    "loanfrom_id": 0,
                    "company_text": f"'{company_text}'",
                    "achievements": "''",
                    "pos_text": "''"
                }
                db.insert("careers", **career_dict)

            player = db.select("players", False, person_id=wp_user_id)
            if player:
                db.update("players",
                          {"position_1": position_1, "position_2": position_2, "position_3": position_3},
                          {"person_id": wp_user_id})
            else:
                player_dict = {
                    "person_id": wp_user_id,
                    "position_1": position_1,
                    "position_2": position_2,
                    "position_3": position_3,
                    "height": height,
                    "weight": 0,
                    "agent_id": 0,
                    "agent_text": "''",
                    "agent_search": 0,
                    "team_search": 0,
                    "salary": 0,
                    "trial": 0,
                    "other_info": "''",
                }
                if foot:
                    player_dict["strong_foot"] = f"'{foot}'"
                db.insert("players", **player_dict)

            image_path = str(Path(*players_photo_folder.split(), f"{wp_user_id}_1.png"))
            with open(image_path, "wb") as file:
                file.write(image)
