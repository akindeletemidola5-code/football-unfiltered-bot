from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from datetime import datetime, timedelta, timezone
import requests
import os
import json
import time


# =========================================================
# 🔐 YOUR SETTINGS
# =========================================================

FOOTBALL_DATA_TOKEN = "8bc926f0226d4dc98a333f232426d609"

BOT_TOKEN = "8258337139:AAGDnZtNuHcVwgrk_LF5PNTs-qJ8Uiq8FGI"

CHAT_ID = "@footballInFilteredX"


# =========================================================
# ⚙️ AUTOMATION SETTINGS
# =========================================================

CHECK_EVERY_SECONDS = 15 * 60

MAX_POSTS_PER_RUN = 3

WIDTH = 1200
HEIGHT = 700

POSTED_FILE = "posted_upcoming_matches.json"


ALLOWED_COMPETITIONS = {
    "PL": "Premier League",
    "CL": "Champions League",
    "PD": "La Liga",
    "SA": "Serie A",
    "BL1": "Bundesliga",
    "FL1": "Ligue 1",
    "EL": "Europa League",
    "FAC": "FA Cup",
    "DFB": "DFB-Pokal",
    "CDR": "Copa del Rey",
    "WC": "World Cup"
}


# =========================================================
# 🖼️ FONTS
# =========================================================

def get_font(size, bold=False):

    paths = [
        "C:/Windows/Fonts/arialbd.ttf"
        if bold else
        "C:/Windows/Fonts/arial.ttf",

        "C:/Windows/Fonts/segoeuib.ttf"
        if bold else
        "C:/Windows/Fonts/segoeui.ttf"
    ]

    for path in paths:

        try:
            return ImageFont.truetype(path, size)

        except:
            pass

    return ImageFont.load_default()


# =========================================================
# 🏆 DOWNLOAD TEAM CREST
# =========================================================

def download_crest(url):

    try:

        response = requests.get(
            url,
            timeout=15,
            headers={
                "User-Agent": "Football-Unfiltered"
            }
        )

        response.raise_for_status()

        crest = Image.open(
            BytesIO(response.content)
        ).convert("RGBA")

        crest.thumbnail((190, 190))

        return crest

    except Exception as error:

        print(
            "Could not download crest:",
            error
        )

        return None


# =========================================================
# ✍️ TEAM NAME TEXT
# =========================================================

def draw_centered_wrapped(
    draw,
    text,
    x,
    y,
    font,
    fill,
    max_width=300
):

    words = text.split()

    lines = []

    current = ""

    for word in words:

        test = (
            current + " " + word
            if current
            else word
        )

        width = draw.textbbox(
            (0, 0),
            test,
            font=font
        )[2]

        if width <= max_width:

            current = test

        else:

            if current:
                lines.append(current)

            current = word

    if current:
        lines.append(current)

    line_height = 38

    for index, line in enumerate(lines):

        draw.text(
            (
                x,
                y + index * line_height
            ),
            line,
            fill=fill,
            font=font,
            anchor="ma"
        )


# =========================================================
# 🎨 CREATE MATCH CARD
# =========================================================

def create_match_card(
    home_team,
    away_team,
    competition,
    match_date,
    match_time,
    home_crest_url,
    away_crest_url,
    output_file
):

    image = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        (18, 18, 18)
    )

    draw = ImageDraw.Draw(image)

    white = (255, 255, 255)

    grey = (175, 175, 175)

    line = (65, 65, 65)


    title_font = get_font(38, True)

    competition_font = get_font(25)

    team_font = get_font(30, True)

    vs_font = get_font(42, True)

    date_font = get_font(30, True)

    time_font = get_font(24)

    footer_font = get_font(23, True)


    # TOP LINE

    draw.rectangle(
        (0, 0, WIDTH, 10),
        fill=white
    )


    # HEADER

    draw.text(
        (WIDTH // 2, 55),
        "UPCOMING MATCH",
        fill=white,
        font=title_font,
        anchor="ma"
    )


    # COMPETITION

    draw.text(
        (WIDTH // 2, 105),
        competition,
        fill=grey,
        font=competition_font,
        anchor="ma"
    )


    # CRESTS

    home_crest = download_crest(
        home_crest_url
    )

    away_crest = download_crest(
        away_crest_url
    )


    # HOME CREST

    if home_crest:

        x = 145 + (
            190 - home_crest.width
        ) // 2

        y = 170 + (
            190 - home_crest.height
        ) // 2

        image.paste(
            home_crest,
            (x, y),
            home_crest
        )


    # AWAY CREST

    if away_crest:

        x = 865 + (
            190 - away_crest.width
        ) // 2

        y = 170 + (
            190 - away_crest.height
        ) // 2

        image.paste(
            away_crest,
            (x, y),
            away_crest
        )


    draw = ImageDraw.Draw(image)


    # VS

    draw.text(
        (600, 270),
        "VS",
        fill=white,
        font=vs_font,
        anchor="mm"
    )


    # TEAM NAMES

    draw_centered_wrapped(
        draw,
        home_team,
        240,
        395,
        team_font,
        white
    )

    draw_centered_wrapped(
        draw,
        away_team,
        960,
        395,
        team_font,
        white
    )


    # DIVIDER

    draw.line(
        (250, 490, 950, 490),
        fill=line,
        width=2
    )


    # DATE

    draw.text(
        (600, 525),
        match_date,
        fill=white,
        font=date_font,
        anchor="ma"
    )


    # TIME

    draw.text(
        (600, 565),
        match_time + " WAT",
        fill=grey,
        font=time_font,
        anchor="ma"
    )


    # FOOTER

    draw.text(
        (600, 650),
        "FOOTBALL UNFILTERED",
        fill=white,
        font=footer_font,
        anchor="ma"
    )


    image.save(
        output_file,
        "PNG"
    )


# =========================================================
# 📅 GET UPCOMING MATCHES
# =========================================================

def get_upcoming_matches():

    matches = []

    today = datetime.now(
        timezone.utc
    ).date()


    # FOOTBALL-DATA.ORG ONLY ALLOWS
    # PERIODS OF UP TO 10 DAYS.
    # SO WE USE TWO WINDOWS.

    windows = [

        (
            today,
            today + timedelta(days=9)
        ),

        (
            today + timedelta(days=10),
            today + timedelta(days=19)
        )
    ]


    for start_date, end_date in windows:

        print(
            f"Searching fixtures: "
            f"{start_date} to {end_date}"
        )


        url = (
            "https://api.football-data.org/v4/matches"
            f"?dateFrom={start_date}"
            f"&dateTo={end_date}"
            "&status=SCHEDULED"
        )


        try:

            response = requests.get(
                url,
                headers={
                    "X-Auth-Token":
                    FOOTBALL_DATA_TOKEN
                },
                timeout=30
            )


            print(
                "Football-Data HTTP:",
                response.status_code
            )


            if response.status_code != 200:

                print(
                    "Football-Data error:",
                    response.text
                )

                continue


            data = response.json()


            for match in data.get(
                "matches",
                []
            ):

                competition = match.get(
                    "competition",
                    {}
                )


                code = competition.get(
                    "code"
                )


                if code not in ALLOWED_COMPETITIONS:

                    continue


                home = match.get(
                    "homeTeam",
                    {}
                )

                away = match.get(
                    "awayTeam",
                    {}
                )


                match_id = str(
                    match.get("id")
                )


                matches.append({

                    "id":
                    match_id,

                    "home":
                    home.get(
                        "name",
                        "Home Team"
                    ),

                    "away":
                    away.get(
                        "name",
                        "Away Team"
                    ),

                    "competition":
                    ALLOWED_COMPETITIONS[
                        code
                    ],

                    "utcDate":
                    match.get(
                        "utcDate"
                    ),

                    "homeCrest":
                    home.get(
                        "crest"
                    ),

                    "awayCrest":
                    away.get(
                        "crest"
                    )
                })


        except Exception as error:

            print(
                "Error getting fixtures:",
                error
            )


    # REMOVE DUPLICATES

    unique = {}

    for match in matches:

        unique[
            match["id"]
        ] = match


    matches = list(
        unique.values()
    )


    # SORT BY DATE

    matches.sort(
        key=lambda x:
        x["utcDate"]
    )


    print(
        "Total upcoming matches:",
        len(matches)
    )


    return matches


# =========================================================
# 🧠 DUPLICATE PROTECTION
# =========================================================

def load_posted_matches():

    if not os.path.exists(
        POSTED_FILE
    ):

        return set()


    try:

        with open(
            POSTED_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

            return set(data)


    except:

        return set()


def save_posted_matches(
    posted
):

    with open(
        POSTED_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            list(posted),
            file,
            indent=2
        )


# =========================================================
# 🇳🇬 CONVERT TIME TO LAGOS
# =========================================================

def format_lagos_time(
    utc_date
):

    dt = datetime.fromisoformat(
        utc_date.replace(
            "Z",
            "+00:00"
        )
    )


    # Lagos is UTC+1

    lagos = dt.astimezone(
        timezone(
            timedelta(hours=1)
        )
    )


    date_text = lagos.strftime(
        "%A, %d %b %Y"
    )


    time_text = lagos.strftime(
        "%I:%M %p"
    ).lstrip("0")


    return (
        date_text,
        time_text
    )


# =========================================================
# 📤 SEND PHOTO TO TELEGRAM
# =========================================================

def send_to_telegram(
    image_file,
    caption
):

    url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendPhoto"
    )


    try:

        with open(
            image_file,
            "rb"
        ) as photo:

            response = requests.post(

                url,

                data={
                    "chat_id":
                    CHAT_ID,

                    "caption":
                    caption
                },

                files={
                    "photo":
                    photo
                },

                timeout=60
            )


        print(
            "Telegram HTTP:",
            response.status_code
        )


        if response.status_code == 200:

            print(
                "Telegram post successful."
            )

            return True


        print(
            "Telegram error:",
            response.text
        )

        return False


    except Exception as error:

        print(
            "Telegram sending error:",
            error
        )

        return False


# =========================================================
# 🚀 CHECK AND POST MATCHES
# =========================================================

def check_and_post_matches():

    print(
        "\nChecking upcoming football matches..."
    )


    posted = load_posted_matches()


    matches = get_upcoming_matches()


    posts_this_run = 0


    for match in matches:

        if posts_this_run >= MAX_POSTS_PER_RUN:

            break


        match_id = match["id"]


        # ALREADY POSTED?

        if match_id in posted:

            continue


        if not match["homeCrest"]:

            print(
                "No home crest:",
                match["home"]
            )

            continue


        if not match["awayCrest"]:

            print(
                "No away crest:",
                match["away"]
            )

            continue


        match_date, match_time = (
            format_lagos_time(
                match["utcDate"]
            )
        )


        image_file = (
            f"match_{match_id}.png"
        )


        # CREATE IMAGE

        create_match_card(

            home_team=
            match["home"],

            away_team=
            match["away"],

            competition=
            match["competition"],

            match_date=
            match_date,

            match_time=
            match_time,

            home_crest_url=
            match["homeCrest"],

            away_crest_url=
            match["awayCrest"],

            output_file=
            image_file
        )


        caption = (
            f"⚽ {match['home']} "
            f"vs {match['away']}\n\n"
            f"🏆 {match['competition']}\n"
            f"📅 {match_date}\n"
            f"🕐 {match_time} WAT"
        )


        success = send_to_telegram(
            image_file,
            caption
        )


        if success:

            posted.add(
                match_id
            )

            save_posted_matches(
                posted
            )

            posts_this_run += 1

            print(
                "Posted:",
                match["home"],
                "vs",
                match["away"]
            )


        # DELETE TEMP IMAGE

        try:

            os.remove(
                image_file
            )

        except:

            pass


    print(
        f"Posted {posts_this_run} "
        f"new upcoming match(es)."
    )


# =========================================================
# GITHUB ACTIONS RUN
# =========================================================

print("====================================")
print(" FOOTBALL UNFILTERED AUTOMATION")
print("====================================")
print("Automation started.")
print()

try:
    check_and_post_matches()

except Exception as error:
    print("Automation error:", error)

print()
print("Automation run finished.")