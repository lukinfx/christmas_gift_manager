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
    if status in ("want_to_buy", "want_to_buy_shared"):
        return gift.get("interested_buyer") == username
    if status == "bought":
        return gift.get("bought_by") == username
    return False


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
