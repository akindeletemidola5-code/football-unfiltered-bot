from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests
import os
import json


# =========================================================
# SETTINGS
# =========================================================

FOOTBALL_DATA_TOKEN = os.getenv("FOOTBALL_DATA_TOKEN")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = "@footballInFilteredX"

LAGOS = ZoneInfo("Africa/Lagos")


# =========================================================
# AUTOMATION SETTINGS
# =========================================================

MAX_POSTS_PER_RUN = 3

WIDTH = 1200
HEIGHT = 700

POSTED_FILE = "posted_upcoming_matches.json"
MATCH_EVE_FILE = "posted_match_eve.json"

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
    "WC": "World Cup",
}


# =========================================================
# FONTS
# =========================================================

def get_font(size, bold=False):
    paths = [
        (
            "/usr/share/fonts/truetype/dejavu/"
            "DejaVuSans-Bold.ttf"
            if bold
            else
            "/usr/share/fonts/truetype/dejavu/"
            "DejaVuSans.ttf"
        ),
        (
            "C:/Windows/Fonts/arialbd.ttf"
            if bold
            else "C:/Windows/Fonts/arial.ttf"
        ),
        (
            "C:/Windows/Fonts/segoeuib.ttf"
            if bold
            else "C:/Windows/Fonts/segoeui.ttf"
        ),
    ]

    for path in paths:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass

    return ImageFont.load_default()


# =========================================================
# DOWNLOAD TEAM CREST
# =========================================================

def download_crest(url):
    if not url:
        return None

    try:
        response = requests.get(
            url,
            timeout=20,
            headers={"User-Agent": "Football-Unfiltered"},
        )
        response.raise_for_status()

        crest = Image.open(
            BytesIO(response.content)
        ).convert("RGBA")

        crest.thumbnail((190, 190))

        return crest

    except Exception as error:
        print("Could not download crest:", error)
        return None


# =========================================================
# TEAM NAME TEXT
# =========================================================

def draw_centered_wrapped(
    draw,
    text,
    x,
    y,
    font,
    fill,
    max_width=300,
):
    words = text.split()
    lines = []
    current = ""

    for word in words:
        test = f"{current} {word}".strip()

        width = draw.textbbox(
            (0, 0),
            test,
            font=font,
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
                y + index * line_height,
            ),
            line,
            fill=fill,
            font=font,
            anchor="ma",
        )


# =========================================================
# CREATE MATCH CARD
# =========================================================

def create_match_card(
    home_team,
    away_team,
    competition,
    match_date,
    match_time,
    home_crest_url,
    away_crest_url,
    output_file,
    title="UPCOMING MATCH",
):
    # Both crests are required. Never knowingly send
    # a match card with a missing team crest.

    home_crest = download_crest(home_crest_url)
    away_crest = download_crest(away_crest_url)

    if home_crest is None or away_crest is None:
        raise RuntimeError(
            f"Both team crests are required: "
            f"{home_team} vs {away_team}"
        )

    image = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        (18, 18, 18),
    )

    draw = ImageDraw.Draw(image)

    white = (255, 255, 255)
    grey = (175, 175, 175)
    line = (65, 65, 65)

    title_font = get_font(30, True)
    competition_font = get_font(21)
    team_font = get_font(30, True)
    vs_font = get_font(34, True)
    date_font = get_font(27, True)
    time_font = get_font(22, True)
    footer_font = get_font(23, True)

    # Top line
    draw.rectangle(
        (0, 0, WIDTH, 8),
        fill=white,
    )

    # Header
    draw.text(
        (WIDTH // 2, 50),
        title,
        fill=white,
        font=title_font,
        anchor="ma",
    )

    # Competition
    draw.text(
        (WIDTH // 2, 90),
        competition,
        fill=grey,
        font=competition_font,
        anchor="ma",
    )

    # Home crest
    x = 145 + (190 - home_crest.width) // 2
    y = 165 + (190 - home_crest.height) // 2

    image.paste(
        home_crest,
        (x, y),
        home_crest,
    )

    # Away crest
    x = 865 + (190 - away_crest.width) // 2
    y = 165 + (190 - away_crest.height) // 2

    image.paste(
        away_crest,
        (x, y),
        away_crest,
    )

    draw = ImageDraw.Draw(image)

    # VS
    draw.text(
        (600, 270),
        "VS",
        fill=white,
        font=vs_font,
        anchor="mm",
    )

    # Team names
    draw_centered_wrapped(
        draw,
        home_team,
        240,
        395,
        team_font,
        white,
    )

    draw_centered_wrapped(
        draw,
        away_team,
        960,
        395,
        team_font,
        white,
    )

    # Divider
    draw.line(
        (250, 490, 950, 490),
        fill=line,
        width=2,
    )

    # Date
    draw.text(
        (600, 525),
        match_date,
        fill=white,
        font=date_font,
        anchor="ma",
    )

    # Time
    draw.text(
        (600, 565),
        match_time + " WAT",
        fill=grey,
        font=time_font,
        anchor="ma",
    )

    # Footer
    draw.text(
        (600, 650),
        "FOOTBALL UNFILTERED",
        fill=white,
        font=footer_font,
        anchor="ma",
    )

    image.save(output_file, "PNG")


# =========================================================
# LAGOS TIME HELPERS
# =========================================================

def now_in_lagos():
    return datetime.now(LAGOS)


def parse_match_datetime(utc_date):
    if not utc_date:
        raise ValueError("Fixture has no kickoff date.")

    dt = datetime.fromisoformat(
        utc_date.replace("Z", "+00:00")
    )

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))

    return dt.astimezone(LAGOS)


def format_lagos_time(utc_date):
    lagos = parse_match_datetime(utc_date)

    date_text = lagos.strftime("%A, %d %b %Y")
    time_text = lagos.strftime("%I:%M %p").lstrip("0")

    return date_text, time_text


# =========================================================
# DUPLICATE TRACKER HELPERS
# =========================================================

def load_tracker(filename):
    if not os.path.exists(filename):
        return set()

    try:
        with open(
            filename,
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        if not isinstance(data, list):
            print("Invalid tracker format:", filename)
            return set()

        return {str(item) for item in data}

    except Exception as error:
        # Do not silently reset a damaged tracker.
        # Otherwise previously posted fixtures could be
        # sent again as duplicates.
        raise RuntimeError(
            f"Could not read {filename}: {error}"
        ) from error


def save_tracker(filename, posted):
    temporary_file = filename + ".tmp"

    with open(
        temporary_file,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            sorted(posted),
            file,
            indent=2,
        )

    os.replace(temporary_file, filename)


def load_posted_matches():
    return load_tracker(POSTED_FILE)


def save_posted_matches(posted):
    save_tracker(POSTED_FILE, posted)


def load_match_eve_matches():
    return load_tracker(MATCH_EVE_FILE)


def save_match_eve_matches(posted):
    save_tracker(MATCH_EVE_FILE, posted)


# =========================================================
# GET UPCOMING MATCHES
# =========================================================

def get_upcoming_matches():
    if not FOOTBALL_DATA_TOKEN:
        raise RuntimeError(
            "FOOTBALL_DATA_TOKEN is missing."
        )

    matches = []

    # Use Lagos calendar dates instead of UTC dates.
    today = now_in_lagos().date()

    windows = [
        (
            today,
            today + timedelta(days=9),
        ),
        (
            today + timedelta(days=10),
            today + timedelta(days=19),
        ),
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
                    "X-Auth-Token": FOOTBALL_DATA_TOKEN,
                },
                timeout=30,
            )

            print(
                "Football-Data HTTP:",
                response.status_code,
            )

            if response.status_code != 200:
                print(
                    "Football-Data error:",
                    response.text,
                )
                continue

            data = response.json()

            for match in data.get("matches", []):
                competition = match.get(
                    "competition", {}
                )

                code = competition.get("code")

                if code not in ALLOWED_COMPETITIONS:
                    continue

                home = match.get("homeTeam", {})
                away = match.get("awayTeam", {})

                match_id = match.get("id")
                utc_date = match.get("utcDate")

                if match_id is None or not utc_date:
                    continue

                matches.append({
                    "id": str(match_id),
                    "home": home.get(
                        "name", "Home Team"
                    ),
                    "away": away.get(
                        "name", "Away Team"
                    ),
                    "competition": ALLOWED_COMPETITIONS[code],
                    "utcDate": utc_date,
                    "homeCrest": home.get("crest"),
                    "awayCrest": away.get("crest"),
                })

        except Exception as error:
            print("Error getting fixtures:", error)

    # Deduplicate API results by fixture ID.
    unique = {
        match["id"]: match
        for match in matches
    }

    matches = list(unique.values())

    matches.sort(
        key=lambda match: match["utcDate"]
    )

    print("Total upcoming matches:", len(matches))

    return matches


# =========================================================
# SEND PHOTO TO TELEGRAM
# =========================================================

def send_to_telegram(image_file, caption):
    if not BOT_TOKEN:
        print("BOT_TOKEN is missing.")
        return False

    url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendPhoto"
    )

    try:
        with open(image_file, "rb") as photo:
            response = requests.post(
                url,
                data={
                    "chat_id": CHAT_ID,
                    "caption": caption,
                },
                files={
                    "photo": photo,
                },
                timeout=60,
            )

        print(
            "Telegram HTTP:",
            response.status_code,
        )

        try:
            result = response.json()
        except ValueError:
            result = {}

        if (
            response.status_code == 200
            and result.get("ok") is True
        ):
            print("Telegram photo sent successfully.")
            return True

        print("Telegram error:", response.text)
        return False

    except Exception as error:
        print("Telegram sending error:", error)
        return False


# =========================================================
# CREATE AND SEND ONE MATCH CARD
# =========================================================

def post_match(match, match_eve=False):
    match_id = match["id"]

    match_date, match_time = format_lagos_time(
        match["utcDate"]
    )

    image_file = f"match_{match_id}.png"

    title = (
        "TOMORROW'S MATCH"
        if match_eve
        else "UPCOMING MATCH"
    )

    caption = (
        f"{'📣 TOMORROW’S MATCH' if match_eve else '⚽ UPCOMING MATCH'}\n\n"
        f"{match['home']} vs {match['away']}\n\n"
        f"🏆 {match['competition']}\n"
        f"📅 {match_date}\n"
        f"🕐 {match_time} WAT"
    )

    try:
        create_match_card(
            home_team=match["home"],
            away_team=match["away"],
            competition=match["competition"],
            match_date=match_date,
            match_time=match_time,
            home_crest_url=match["homeCrest"],
            away_crest_url=match["awayCrest"],
            output_file=image_file,
            title=title,
        )

        # Do not send the card if it was not created.
        if not os.path.exists(image_file):
            print("Image file was not created:", match_id)
            return False

        if os.path.getsize(image_file) == 0:
            print("Image file is empty:", match_id)
            return False

        return send_to_telegram(image_file, caption)

    except Exception as error:
        print(
            f"Could not post {match['home']} vs "
            f"{match['away']}: {error}"
        )
        return False

    finally:
        try:
            if os.path.exists(image_file):
                os.remove(image_file)
        except Exception as error:
            print("Could not remove temporary image:", error)


# =========================================================
# CHECK AND POST MATCHES
# =========================================================

def check_and_post_matches():
    print("\nChecking upcoming football matches...")

    # Preserve both histories between GitHub Actions runs.
    posted = load_posted_matches()
    match_eve_posted = load_match_eve_matches()

    matches = get_upcoming_matches()

    today = now_in_lagos().date()
    tomorrow = today + timedelta(days=1)

    posts_this_run = 0

    # First, identify fixtures whose kickoff is tomorrow.
    tomorrow_matches = []

    for match in matches:
        try:
            kickoff = parse_match_datetime(match["utcDate"])

            if kickoff.date() == tomorrow:
                tomorrow_matches.append(match)

        except Exception as error:
            print(
                "Could not interpret kickoff for",
                match.get("id"),
                error,
            )

    # These fixtures must not also be posted by the
    # ordinary upcoming-fixture loop during this run.
    tomorrow_ids = {
        match["id"]
        for match in tomorrow_matches
    }

    # -----------------------------------------------------
    # PRIORITY 1: MATCH-EVE POSTS
    # -----------------------------------------------------

    for match in tomorrow_matches:
        if posts_this_run >= MAX_POSTS_PER_RUN:
            break

        match_id = match["id"]

        # This fixture has already had its match-eve post.
        if match_id in match_eve_posted:
            print(
                "Match-eve post already sent:",
                match["home"],
                "vs",
                match["away"],
            )
            continue

        success = post_match(
            match,
            match_eve=True,
        )

        if not success:
            print(
                "Match-eve post failed; will retry later:",
                match["home"],
                "vs",
                match["away"],
            )
            continue

        # Record successful Telegram photo delivery.
        # If this was a fixture never posted before,
        # save it in both trackers so it is not posted
        # again by the ordinary upcoming loop.
        match_eve_posted.add(match_id)
        posted.add(match_id)

        save_match_eve_matches(match_eve_posted)
        save_posted_matches(posted)

        posts_this_run += 1

        print(
            "Posted match-eve card:",
            match["home"],
            "vs",
            match["away"],
        )

    # -----------------------------------------------------
    # PRIORITY 2: ORDINARY UPCOMING POSTS
    # -----------------------------------------------------

    for match in matches:
        if posts_this_run >= MAX_POSTS_PER_RUN:
            break

        match_id = match["id"]

        # Tomorrow's fixtures were already considered
        # above, even if their photo send failed.
        if match_id in tomorrow_ids:
            continue

        # Previously posted ordinary fixtures are skipped.
        if match_id in posted:
            continue

        success = post_match(
            match,
            match_eve=False,
        )

        if not success:
            print(
                "Upcoming post failed; will retry later:",
                match["home"],
                "vs",
                match["away"],
            )
            continue

        posted.add(match_id)
        save_posted_matches(posted)

        posts_this_run += 1

        print(
            "Posted upcoming match:",
            match["home"],
            "vs",
            match["away"],
        )

    print(
        f"Posted {posts_this_run} card(s) this run."
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
