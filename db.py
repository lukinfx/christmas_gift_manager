"""All Supabase access lives here. No UI code, no visibility rules."""
import os
from datetime import datetime, timezone
import warnings

import httpx
import streamlit as st
from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

# Local-only escape hatch for networks that intercept TLS (e.g. corporate proxies).
# Set DEV_INSECURE_SSL=1 in your .env to enable. Never needed on Streamlit Cloud.
if os.getenv("DEV_INSECURE_SSL") == "1":
    warnings.filterwarnings("ignore", message="Unverified HTTPS request")
    _original_client_init = httpx.Client.__init__

    def _patched_client_init(self, *args, **kwargs):
        kwargs["verify"] = False
        _original_client_init(self, *args, **kwargs)

    httpx.Client.__init__ = _patched_client_init


def _secret(name: str) -> str | None:
    """Read from the environment/.env first, then Streamlit secrets."""
    value = os.getenv(name)
    if value:
        return value
    try:
        return st.secrets.get(name)
    except Exception:
        return None


@st.cache_resource
def get_client() -> Client:
    url = _secret("SUPABASE_URL")
    key = _secret("SUPABASE_KEY")
    if not url or not key:
        st.error("Please set SUPABASE_URL and SUPABASE_KEY (.env locally, Secrets on Streamlit Cloud)")
        st.stop()
    return create_client(supabase_url=url, supabase_key=key)


# Reads are cached briefly so a page render costs 3 queries total instead of
# 2 per list + 1 per gift. Every write below clears the cache.
CACHE_TTL = 15


def _invalidate() -> None:
    st.cache_data.clear()


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_all_lists() -> list[dict]:
    return get_client().table("gift_lists").select("*").order("created_at", desc=True).execute().data


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_gifts_by_list() -> dict[int, list[dict]]:
    """All gifts grouped by list_id (oldest first)."""
    rows = get_client().table("gifts").select("*").order("created_at", desc=False).execute().data
    grouped: dict[int, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row["list_id"], []).append(row)
    return grouped


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_comments_by_gift() -> dict[int, list[dict]]:
    """All comments grouped by gift_id (oldest first)."""
    rows = get_client().table("gift_comments").select("*").order("created_at", desc=False).execute().data
    grouped: dict[int, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row["gift_id"], []).append(row)
    return grouped


@st.cache_data(ttl=60, show_spinner=False)
def get_app_users() -> list[dict]:
    """Family members allowed to sign in (username, display_name, email)."""
    return get_client().table("app_users").select("*").order("username").execute().data



# ---------- writes ----------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log_event(list_id: int, gift_id: int | None, gift_name: str | None, actor: str, kind: str) -> None:
    """Record activity. Best-effort: a logging failure must never block the real action."""
    try:
        get_client().table("gift_events").insert(
            {"list_id": list_id, "gift_id": gift_id, "gift_name": gift_name, "actor": actor, "kind": kind}
        ).execute()
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] could not log event {kind}: {exc}")


def _gift_ref(gift_id: int) -> tuple[int | None, str | None]:
    rows = get_client().table("gifts").select("list_id,name").eq("id", gift_id).execute().data
    return (rows[0]["list_id"], rows[0]["name"]) if rows else (None, None)


def create_gift_list(name: str, recipients: list[str], created_by: str, year: int | None = None) -> list[dict]:
    data: dict = {"name": name, "recipients": recipients, "created_by": created_by}
    if year is not None:  # otherwise the database default (current year) applies
        data["year"] = year
    result = get_client().table("gift_lists").insert(data).execute().data
    _invalidate()
    return result


def create_gift_lists(rows: list[dict], created_by: str, year: int) -> int:
    """Create several empty lists for a year in one insert. Returns how many were created."""
    if not rows:
        return 0
    data = [
        {"name": r["name"], "recipients": r["recipients"], "created_by": created_by, "year": year}
        for r in rows
    ]
    result = get_client().table("gift_lists").insert(data).execute().data
    _invalidate()
    return len(result)


def add_gift(
    list_id: int,
    name: str,
    description: str,
    added_by: str,
    url: str | None = None,
    price: float | None = None,
    image_url: str | None = None,
) -> list[dict]:
    data: dict = {
        "list_id": list_id,
        "name": name,
        "description": description,
        "added_by": added_by,
        "status": "available",
    }
    if url:
        data["url"] = url
    if price is not None:
        data["price"] = price
    if image_url:
        data["image_url"] = image_url
    result = get_client().table("gifts").insert(data).execute().data
    if result:
        _log_event(list_id, result[0]["id"], name, added_by, "gift_added")
    _invalidate()
    return result


def update_gift_status(gift_id: int, status: str, user: str) -> list[dict]:
    data: dict = {"status": status}
    if status in ("want_to_buy", "want_to_buy_shared"):
        data["interested_buyer"] = user
    elif status == "bought":
        data["bought_by"] = user
        data["bought_at"] = _now()
    result = get_client().table("gifts").update(data).eq("id", gift_id).execute().data
    list_id, name = _gift_ref(gift_id)
    if list_id is not None:
        _log_event(list_id, gift_id, name, user, status)
    _invalidate()
    return result


def release_gift(gift_id: int, user: str) -> list[dict]:
    """Undo a reservation / purchase: back to 'available'."""
    data = {"status": "available", "interested_buyer": None, "bought_by": None, "bought_at": None}
    result = get_client().table("gifts").update(data).eq("id", gift_id).execute().data
    list_id, name = _gift_ref(gift_id)
    if list_id is not None:
        _log_event(list_id, gift_id, name, user, "released")
    _invalidate()
    return result


def delete_gift(gift_id: int) -> list[dict]:
    client = get_client()
    client.table("gift_comments").delete().eq("gift_id", gift_id).execute()
    result = client.table("gifts").delete().eq("id", gift_id).execute().data
    _invalidate()
    return result


def add_comment(gift_id: int, comment: str, user: str) -> list[dict]:
    data = {"gift_id": gift_id, "comment": comment, "username": user}
    result = get_client().table("gift_comments").insert(data).execute().data
    list_id, name = _gift_ref(gift_id)
    if list_id is not None:
        _log_event(list_id, gift_id, name, user, "comment")
    _invalidate()
    return result


# ---------- activity ----------

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_recent_events(limit: int = 200) -> list[dict]:
    return (
        get_client().table("gift_events").select("*").order("created_at", desc=True).limit(limit).execute().data
    )


def touch_last_seen(username: str) -> None:
    get_client().table("app_users").update({"last_seen_at": _now()}).eq("username", username).execute()
    _invalidate()  # app_users is cached; the next read must see the new timestamp
