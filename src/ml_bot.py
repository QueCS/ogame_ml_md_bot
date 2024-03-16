import os
import tomllib
import time
import json
import highscores as hs
import players as pl
import datetime
import logging
import dhooks

os.chdir(f"{os.path.dirname(__file__)}")

with open("../config.toml", "rb") as config_file:
    config = tomllib.load(config_file)

ml_log_dir = config.get("ML_BOT", {}).get("ml_log_dir")
ml_file_dir = config.get("ML_BOT", {}).get("ml_file_dir")
server = config.get("ML_BOT", {}).get("ml_server")
community = config.get("ML_BOT", {}).get("ml_community")
ml_hook = dhooks.Webhook(config.get("ML_BOT", {}).get("ml_webhook"))

logging.basicConfig(
    filename=f"{ml_log_dir}",
    filemode="a",
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.INFO,
)


def main():
    check_ml(server, community)


def check_ml(server: int, community: str):

    logging.info("Starting up check_ml")

    while True:
        time.sleep(60)

        with open(ml_file_dir, "r") as file:
            old_ml = json.load(file)
        old_ts = int(old_ml.get("timestamp"))

        current_time = datetime.datetime.now()
        current_ts = int(current_time.timestamp())

        if current_ts > old_ts + 3600:
            new_ml, payload = compare_ml(server, community, old_ml, old_ts)

            if payload is False:
                continue

            logging.info("Sending payload")
            try:
                ml_hook.send(payload)
                logging.info("Done\n")
                update_ml_file(new_ml, ml_file_dir)
            except Exception as exception:
                logging.warning(f"Calling hook.send(): {exception}")
                logging.warning("Payload not sent\n")
            continue


def compare_ml(server: int, community: str, old_ml, old_ts):

    ml_api = hs.get_highscore_api(server, community, 1, 4)
    if ml_api is None:
        return "```\nError: ml_api is None\n```"
    new_ts = ml_api.timestamp()

    if old_ts == new_ts:
        logging.info(
            f"Timestamps match: {old_ts} == {new_ts}, API not updated, exiting\n"
        )
        return False
    logging.info(
        f"Timestamps differ: {old_ts} != {new_ts}, API updated, computing differences"
    )

    new_ml = ml_api.data_dict()

    pl_api = pl.get_players_api(server, community)

    payload = ""

    common_keys = old_ml.keys() & new_ml.keys()
    for key in common_keys:
        if key not in ("timestamp", "server"):
            name = pl_api.name_from_id(key)
            if name is None:
                name = key
            diff = new_ml[key]["score"] - old_ml[key]["score"]
            if diff != 0:
                payload += f"\n{name.ljust(22)} + {diff:,}"

    lines = payload.strip().split("\n")
    sorted_lines = sorted(
        lines,
        key=lambda x: float(x.split("+")[-1].replace(",", "").strip()),
        reverse=True,
    )
    payload = "\n".join(sorted_lines)

    update_datetime = datetime.datetime.fromtimestamp(new_ts)
    payload = f"```\n{update_datetime}\n\n{payload}\n```"

    payload = payload.replace(",", ".")

    return new_ml, payload


def update_ml_file(data, dir):
    logging.info(f"Updating {dir}")
    with open(ml_file_dir, "w") as file:
        json.dump(data, file)
    logging.info(f"Done\n")


if __name__ == "__main__":
    main()