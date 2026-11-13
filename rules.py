"""Who may see / do what. Pure functions: no Streamlit, no database."""


def find_user_by_email(users: list[dict], email: str) -> dict | None:
    """Case-insensitive match of a verified Google email to an app user."""
    email = (email or "").strip().lower()
    if not email:
        return None
    for user in users:
        if (user.get("email") or "").strip().lower() == email:
            return user
    return None


def is_recipient(gift_list: dict, username: str) -> bool:
    return username in (gift_list.get("recipients") or [])


def visible_gifts(gift_list: dict, gifts: list[dict], username: str) -> list[dict]:
    """Recipients only see the gifts they added themselves; everyone else sees all."""
    if is_recipient(gift_list, username):
        return [g for g in gifts if g["added_by"] == username]
    return list(gifts)


def can_see_status(gift_list: dict, username: str) -> bool:
    """Status, buy actions and comments are hidden from recipients (it's a surprise)."""
    return not is_recipient(gift_list, username)


def can_release_gift(gift: dict, username: str) -> bool:
    """Only the person who reserved/bought a gift can undo it."""
    status = gift.get("status", "available")
    if status == "want_to_buy":
        return gift.get("interested_buyer") == username
    if status == "bought":
        return gift.get("bought_by") == username
    return False  # split gifts: each person leaves the split themselves (can_leave_split)


# ---------- split buying ----------

def split_participants(gift: dict) -> list[str]:
    """Everyone sharing the cost. Falls back to the single buyer for older split rows."""
    people = list(gift.get("split_buyers") or [])
    if not people and gift.get("status") == "want_to_buy_shared" and gift.get("interested_buyer"):
        people = [gift["interested_buyer"]]
    return people


def my_share(gift: dict, username: str) -> float | None:
    """What this person pays: price / number of people in an equal split, else the full price."""
    price = gift.get("price")
    if price is None:
        return None
    people = split_participants(gift)
    if username in people and gift.get("status") in ("want_to_buy_shared", "bought"):
        return round(float(price) / len(people), 2)
    return float(price)


def can_join_split(gift: dict, username: str) -> bool:
    return gift.get("status") == "want_to_buy_shared" and username not in split_participants(gift)


def can_leave_split(gift: dict, username: str) -> bool:
    return gift.get("status") == "want_to_buy_shared" and username in split_participants(gift)


def can_mark_bought(gift: dict, username: str) -> bool:
    """Reserved gifts: anyone. Split gifts: only the people in the split."""
    status = gift.get("status", "available")
    if status == "bought":
        return False
    if status == "want_to_buy_shared":
        return username in split_participants(gift)
    return True


def visible_events(events: list[dict], lists_by_id: dict[int, dict], username: str) -> list[dict]:
    """Activity feed: hide everything about lists where I'm a recipient (it's a surprise),
    except gifts I added myself being added."""
    out = []
    for ev in events:
        gift_list = lists_by_id.get(ev["list_id"])
        if gift_list is None:
            continue
        if is_recipient(gift_list, username):
            continue
        out.append(ev)
    return out


def can_delete_gift(gift: dict, username: str) -> bool:
    return gift["added_by"] == username


def can_edit_gift(gift: dict, username: str) -> bool:
    """Only the person who added a gift may change it."""
    return gift["added_by"] == username


def can_move_gift(gift: dict, username: str) -> bool:
    """Only the person who added a gift may move it to another list."""
    return gift["added_by"] == username


def move_targets(all_lists: list[dict], current_list_id: int, year: int) -> list[dict]:
    """Lists in `year` a gift can be moved to (every list of that year except where it already is)."""
    return [l for l in all_lists if l["year"] == year and l["id"] != current_list_id]


# ---------- input cleaning ----------

def clean_url(raw: str | None) -> str | None:
    """Accept only http(s) links (blocks javascript: etc.). Adds https:// if the scheme is missing."""
    raw = (raw or "").strip()
    if not raw:
        return None
    if "://" not in raw:
        raw = "https://" + raw
    lowered = raw.lower()
    if not (lowered.startswith("https://") or lowered.startswith("http://")):
        return None
    rest = raw.split("://", 1)[1]
    if not rest or " " in raw or "." not in rest.split("/")[0]:
        return None
    return raw


def parse_price(raw: str | None) -> float | None:
    """'1 200', '1200,50', '1200 Kč' -> float. Returns None when empty/invalid/negative."""
    cleaned = "".join(ch for ch in (raw or "") if ch.isdigit() or ch in ".,").replace(",", ".")
    if not cleaned or cleaned.count(".") > 1:
        return None
    try:
        value = float(cleaned)
    except ValueError:
        return None
    return round(value, 2) if value >= 0 else None


# ---------- dates ----------

def days_until_christmas(today) -> int:
    """Days until the next 24 December (0 on the day itself, counts to next year after it)."""
    from datetime import date

    target = date(today.year, 12, 24)
    if today > target:
        target = date(today.year + 1, 12, 24)
    return (target - today).days


def default_year(years: list[int], current_year: int) -> int:
    """Current year if it has lists, otherwise the most recent year that does."""
    if current_year in years or not years:
        return current_year
    return max(years)


# ---------- my purchases ----------

def purchase_summary(lists: list[dict], gifts_by_list: dict, username: str) -> list[dict]:
    """My reservations/purchases per list (never lists where I'm the recipient)."""
    out = []
    for gift_list in lists:
        if is_recipient(gift_list, username):
            continue
        mine = []
        for gift in gifts_by_list.get(gift_list["id"], []):
            status = gift.get("status")
            in_split = username in split_participants(gift)
            if status == "want_to_buy" and gift.get("interested_buyer") == username:
                mine.append(gift)
            elif status == "want_to_buy_shared" and in_split:
                mine.append(gift)
            elif status == "bought" and (gift.get("bought_by") == username or in_split):
                mine.append(gift)
        if mine:
            out.append({"list": gift_list, "gifts": mine})
    return out


def money_totals(gifts: list[dict], username: str) -> dict:
    """What `username` pays, reserved vs bought (split gifts count only their share).
    Gifts without a price are counted separately."""
    reserved = bought = 0.0
    unpriced = 0
    for gift in gifts:
        share = my_share(gift, username)
        if share is None:
            unpriced += 1
            continue
        if gift.get("status") == "bought":
            bought += share
        else:
            reserved += share
    return {"reserved": reserved, "bought": bought, "unpriced": unpriced}


# ---------- "new since last visit" ----------

def parse_ts(iso: str | None):
    """ISO timestamp from Supabase -> aware datetime, or None."""
    from datetime import datetime, timezone

    if not iso:
        return None
    try:
        value = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def new_events(events: list[dict], since, username: str) -> list[dict]:
    """Events after `since` caused by someone else (your own actions aren't news)."""
    if since is None:
        return []
    out = []
    for ev in events:
        ts = parse_ts(ev.get("created_at"))
        if ts is not None and ts > since and ev.get("actor") != username:
            out.append(ev)
    return out


def count_by_list(events: list[dict]) -> dict[int, int]:
    counts: dict[int, int] = {}
    for ev in events:
        counts[ev["list_id"]] = counts.get(ev["list_id"], 0) + 1
    return counts


# ---------- admin: start a new year ----------

def is_admin(user: dict | None) -> bool:
    return bool(user and user.get("is_admin"))


def _list_key(gift_list: dict) -> tuple:
    return (gift_list["name"].strip().lower(), tuple(sorted(gift_list.get("recipients") or [])))


def lists_to_copy(source_lists: list[dict], target_lists: list[dict]) -> list[dict]:
    """Source lists that don't already exist (same name + recipients) in the target year."""
    existing = {_list_key(l) for l in target_lists}
    return [l for l in source_lists if _list_key(l) not in existing]


def is_recent(created_at: str | None, now, days: int = 3) -> bool:
    """True if something was created within the last `days` days."""
    from datetime import timedelta

    ts = parse_ts(created_at)
    return ts is not None and timedelta(0) <= now - ts <= timedelta(days=days)
