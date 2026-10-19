import os
import io
import json
import time
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from PIL import Image, ImageDraw, ImageFont


# ============================================================
# CONFIGURATION
# ============================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN")
FOOTBALL_DATA_TOKEN = os.environ.get("FOOTBALL_DATA_TOKEN")

CHAT_ID = "@footballInFilteredX"

TIMEZONE = ZoneInfo("Africa/Lagos")

POSTED_FILE = "posted_upcoming_matches.json"
MATCH_EVE_FILE = "posted_match_eve.json"

MAX_POSTS_PER_RUN = 10

FOOTBALL_DATA_BASE = "https://api.football-data.org/v4"

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


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger("FootballUnfiltered")


# ============================================================
# TRACKER MANAGEMENT
# ============================================================

def extract_ids(data):
    """
    Read common tracker formats without discarding existing IDs.
    Supports lists, dictionaries, and dictionaries of match records.
    """

    found = set()

    if isinstance(data, list):
        for item in data:
            if isinstance(item, (str, int)):
                value = str(item)

                if value.isdigit():
                    found.add(value)

            elif isinstance(item, dict):
                for key in ("id", "match_id", "fixture_id"):
                    value = item.get(key)

                    if value is not None:
                        found.add(str(value))

                found.update(extract_ids(item))

    elif isinstance(data, dict):
        for key, value in data.items():

            # Tracker dictionaries sometimes use match IDs as keys.
            if str(key).isdigit():
                found.add(str(key))

            if isinstance(value, dict):
                for id_key in ("id", "match_id", "fixture_id"):
                    match_id = value.get(id_key)

                    if match_id is not None:
                        found.add(str(match_id))

                found.update(extract_ids(value))

            elif isinstance(value, list):
                found.update(extract_ids(value))

    return found


def load_tracker(filename):
    """
    Load an existing tracker without silently resetting its history.
    A missing file starts empty; a damaged file stops the run.
    """

    if not os.path.exists(filename):
        logger.info("%s does not exist yet; starting a new tracker.", filename)
        return set()

    try:
        with open(filename, "r", encoding="utf-8") as file:
            data = json.load(file)

        ids = extract_ids(data)

        logger.info("Loaded %s IDs from %s.", len(ids), filename)

        return ids

    except Exception as error:
        raise RuntimeError(
            f"Could not safely read {filename}. "
            "Fix the file before continuing so posting history is not lost."
        ) from error


def save_tracker(filename, ids):
    """
    Save tracker IDs in a consistent JSON format.
    """

    temporary_file = filename + ".tmp"

    with open(temporary_file, "w", encoding="utf-8") as file:
        json.dump(sorted(ids), file, indent=2)

    os.replace(temporary_file, filename)

    logger.info("Saved %s IDs to %s.", len(ids), filename)


# ============================================================
# FOOTBALL-DATA.ORG API
# ============================================================

def api_get(endpoint, params=None):
    if not FOOTBALL_DATA_TOKEN:
        raise RuntimeError("FOOTBALL_DATA_TOKEN is missing.")

    headers = {
        "X-Auth-Token": FOOTBALL_DATA_TOKEN
    }

    url = f"{FOOTBALL_DATA_BASE}{endpoint}"

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=25,
    )

    if response.status_code != 200:
        logger.warning(
            "Football API returned HTTP %s for %s: %s",
            response.status_code,
            endpoint,
            response.text[:250],
        )
        return None

    try:
        return response.json()

    except ValueError:
        logger.warning("The football API returned invalid JSON.")
        return None


def get_upcoming_matches():
    """
    Fetch scheduled fixtures over the next ten days, including tomorrow.
    """

    today = datetime.now(TIMEZONE).date()

    date_from = today.isoformat()
    date_to = (today + timedelta(days=10)).isoformat()

    matches_by_id = {}

    for code, competition_name in ALLOWED_COMPETITIONS.items():

        data = api_get(
            f"/competitions/{code}/matches",
            params={
                "dateFrom": date_from,
                "dateTo": date_to,
                "status": "SCHEDULED,TIMED",
            },
        )

        # Some competitions may not be available on the API plan.
        if not data:
            continue

        for match in data.get("matches", []):

            match_id = match.get("id")

            if match_id is None:
                continue

            home = match.get("homeTeam") or {}
            away = match.get("awayTeam") or {}

            home_name = home.get("name")
            away_name = away.get("name")

            home_crest = home.get("crest")
            away_crest = away.get("crest")

            utc_date = match.get("utcDate")

            if not all([
                home_name,
                away_name,
                home_crest,
                away_crest,
                utc_date,
            ]):
                logger.info(
                    "Skipping fixture %s because team details or crests are missing.",
                    match_id,
                )
                continue

            try:
                kickoff = datetime.fromisoformat(
                    utc_date.replace("Z", "+00:00")
                ).astimezone(TIMEZONE)

            except ValueError:
                logger.warning(
                    "Could not read kickoff date for match %s.",
                    match_id,
                )
                continue

            # Skip fixtures that are no longer upcoming.
            if kickoff <= datetime.now(TIMEZONE):
                continue

            matches_by_id[str(match_id)] = {
                "id": str(match_id),
                "home": home_name,
                "away": away_name,
                "home_crest": home_crest,
                "away_crest": away_crest,
                "competition": competition_name,
                "kickoff": kickoff,
            }

    matches = list(matches_by_id.values())

    matches.sort(key=lambda match: match["kickoff"])

    logger.info("Found %s upcoming fixtures.", len(matches))

    return matches


# ============================================================
# IMAGE CREATION
# ============================================================

def load_font(size, bold=False):
    possible_fonts = []

    if bold:
        possible_fonts.extend([
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        ])
    else:
        possible_fonts.extend([
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        ])

    for path in possible_fonts:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


def download_crest(url):
    """
    Return a crest image or fail. Do not create a photo card with
    a missing team crest.
    """

    response = requests.get(url, timeout=20)
    response.raise_for_status()

    image = Image.open(io.BytesIO(response.content)).convert("RGBA")
    image.thumbnail((190, 190))

    return image


def create_match_card(match, match_eve=False):
    """
    Create a picture containing both team crests.
    """

    width, height = 1200, 700

    background = (15, 22, 38)
    white = (255, 255, 255)
    muted = (195, 204, 220)

    image = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(image)

    title_font = load_font(46, bold=True)
    team_font = load_font(32, bold=True)
    details_font = load_font(26)
    footer_font = load_font(27, bold=True)

    # Both crests are mandatory.
    home_crest = download_crest(match["home_crest"])
    away_crest = download_crest(match["away_crest"])

    home_position = (245, 190)
    away_position = (765, 190)

    image.paste(home_crest, home_position, home_crest)
    image.paste(away_crest, away_position, away_crest)

    title = (
        "TOMORROW'S MATCH"
        if match_eve
        else "UPCOMING MATCH"
    )

    draw.text(
        (width // 2, 65),
        title,
        font=title_font,
        fill=white,
        anchor="mm",
    )

    draw.text(
        (width // 2, 125),
        match["competition"],
        font=details_font,
        fill=muted,
        anchor="mm",
    )

    draw.text(
        (340, 415),
        match["home"],
        font=team_font,
        fill=white,
        anchor="mm",
    )

    draw.text(
        (860, 415),
        match["away"],
        font=team_font,
        fill=white,
        anchor="mm",
    )

    draw.text(
        (width // 2, 480),
        "VS",
        font=title_font,
        fill=white,
        anchor="mm",
    )

    kickoff_text = match["kickoff"].strftime(
        "%A, %d %B • %H:%M WAT"
    )

    draw.text(
        (width // 2, 550),
        kickoff_text,
        font=details_font,
        fill=muted,
        anchor="mm",
    )

    draw.text(
        (width // 2, 640),
        "FOOTBALL UNFILTERED",
        font=footer_font,
        fill=white,
        anchor="mm",
    )

    output = io.BytesIO()
    image.save(output, format="PNG")
    output.seek(0)

    return output


# ============================================================
# TELEGRAM POSTING
# ============================================================

def send_to_telegram(photo, caption):
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is missing.")

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"

    try:
        response = requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "caption": caption,
            },
            files={
                "photo": ("football_match.png", photo, "image/png")
            },
            timeout=45,
        )

        try:
            result = response.json()

        except ValueError:
            result = {}

        if response.status_code != 200 or not result.get("ok"):
            logger.error(
                "Telegram rejected the photo: HTTP %s, %s",
                response.status_code,
                result,
            )
            return False

        logger.info("Telegram photo sent successfully.")

        return True

    except requests.RequestException as error:
        logger.error("Telegram request failed: %s", error)
        return False


def post_match(match, match_eve=False):
    """
    Create and send a picture.
    Return True only when Telegram confirms the photo was sent.
    """

    try:
        photo = create_match_card(match, match_eve=match_eve)

    except Exception as error:
        logger.warning(
            "Could not create the picture for %s vs %s: %s",
            match["home"],
            match["away"],
            error,
        )
        return False

    kickoff_text = match["kickoff"].strftime(
        "%A, %d %B at %H:%M WAT"
    )

    if match_eve:
        caption = (
            f"⏳ TOMORROW'S MATCH\n\n"
            f"⚽ {match['home']} vs {match['away']}\n"
            f"🏆 {match['competition']}\n"
            f"🕒 {kickoff_text}\n\n"
            f"FOOTBALL UNFILTERED"
        )
    else:
        caption = (
            f"📅 UPCOMING MATCH\n\n"
            f"⚽ {match['home']} vs {match['away']}\n"
            f"🏆 {match['competition']}\n"
            f"🕒 {kickoff_text}\n\n"
            f"FOOTBALL UNFILTERED"
        )

    return send_to_telegram(photo, caption)


# ============================================================
# MAIN AUTOMATION
# ============================================================

def check_and_post_matches():
    logger.info("Starting Football Unfiltered fixture check.")

    # Load regular fixture history and match-eve reminder history separately.
    posted_ids = load_tracker(POSTED_FILE)
    match_eve_ids = load_tracker(MATCH_EVE_FILE)

    matches = get_upcoming_matches()

    today = datetime.now(TIMEZONE).date()
    tomorrow = today + timedelta(days=1)

    posts_this_run = 0

    # --------------------------------------------------------
    # 1. POST REGULAR UPCOMING FIXTURES FIRST
    # --------------------------------------------------------
    # This prevents match-eve reminders from consuming the
    # entire posting allowance before regular fixtures are sent.

    for match in matches:

        if posts_this_run >= MAX_POSTS_PER_RUN:
            break

        match_id = str(match["id"])

        # Do not repost a fixture already published normally.
        if match_id in posted_ids:
            continue

        logger.info(
            "Posting upcoming fixture: %s vs %s",
            match["home"],
            match["away"],
        )

        success = post_match(match, match_eve=False)

        if not success:
            logger.warning(
                "Upcoming fixture failed. It will be retried later."
            )
            continue

        # Save the ID only after Telegram confirms success.
        posted_ids.add(match_id)
        save_tracker(POSTED_FILE, posted_ids)

        posts_this_run += 1
        time.sleep(2)

    # --------------------------------------------------------
    # 2. POST MATCH-EVE REMINDERS SEPARATELY
    # --------------------------------------------------------
    # These reminders have their own history, so a reminder
    # does not prevent a regular fixture post, or vice versa.

    for match in matches:

        if posts_this_run >= MAX_POSTS_PER_RUN:
            break

        match_id = str(match["id"])

        # Only matches taking place tomorrow receive reminders.
        if match["kickoff"].date() != tomorrow:
            continue

        # Do not send the same reminder twice.
        if match_id in match_eve_ids:
            continue

        logger.info(
            "Posting match-eve reminder: %s vs %s",
            match["home"],
            match["away"],
        )

        success = post_match(match, match_eve=True)

        if not success:
            logger.warning(
                "Match-eve reminder failed. It will be retried later."
            )
            continue

        # Record the reminder only after successful delivery.
        match_eve_ids.add(match_id)
        save_tracker(MATCH_EVE_FILE, match_eve_ids)

        posts_this_run += 1
        time.sleep(2)

    logger.info(
        "Fixture check finished. Successful posts this run: %s",
        posts_this_run,
    )
    if __name__ == "__main__":
    check_and_post_matches()
