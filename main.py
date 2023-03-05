import time
from pathlib import Path

import pywebio
import pywebio.input as inp
from pywebio.output import put_image, clear, toast
from pywebio.session import run_js

from src.config import db
from src.parsing import parse_transfermarkt, parse_sofascore


@pywebio.config()
async def main():
    clear()

    parser_logo_path = Path("src", "assets", "parser.png")
    put_image(open(parser_logo_path, "rb").read())

    method = await inp.select(
        "Выберите сайт, который нужно спарсить",
        [
            "Transfermarkt",
            "SofaScore"
        ]
    )

    nation = await inp.select(
        "Выберите страну",
        [nation["name_en"] for nation in db.select("nations", "name_en")]
    )

    try:
        if method == "Transfermarkt":
            parse_transfermarkt(nation)
        else:
            parse_sofascore(nation)
    except Exception as ex:
        print(ex)

        toast("Во время работы программы произошла ошибка... Повторите попытку еще раз")
    else:
        toast("Работа завершена!")
    finally:
        time.sleep(2)

    run_js("location.reload()")


if __name__ == "__main__":
    pywebio.start_server(main, host="0.0.0.0", port=5555)
