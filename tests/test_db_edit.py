"""update_gift must enforce authorship itself and only touch the editable fields.
Uses a stub client: no network, no real data."""
import db


class _Query:
    def __init__(self, log):
        self.log = log

    def update(self, data):
        self.log.append(("update", data))
        return self

    def eq(self, col, val):
        self.log.append(("eq", col, val))
        return self

    def execute(self):
        return self


class _Client:
    def __init__(self):
        self.log = []

    def table(self, name):
        self.log.append(("table", name))
        return _Query(self.log)


def _setup(monkeypatch, gift):
    client = _Client()
    monkeypatch.setattr(db, "get_client", lambda: client)
    monkeypatch.setattr(db, "_get_gift", lambda gid: gift)
    monkeypatch.setattr(db, "_invalidate", lambda: None)
    return client


GIFT = {"id": 5, "added_by": "anna", "status": "bought", "bought_by": "carl"}


def test_author_can_edit_and_cleared_fields_become_null(monkeypatch):
    client = _setup(monkeypatch, GIFT)
    ok = db.update_gift(5, "anna", name="Lego", description="", url=None, price=None, image_url=None)
    assert ok
    update = next(e for e in client.log if e[0] == "update")[1]
    assert update == {"name": "Lego", "description": "", "url": None, "price": None, "image_url": None}
    assert ("eq", "id", 5) in client.log


def test_edit_never_touches_status_or_buyers(monkeypatch):
    client = _setup(monkeypatch, GIFT)
    db.update_gift(5, "anna", name="x", description="", url=None, price=10.0, image_url=None)
    update = next(e for e in client.log if e[0] == "update")[1]
    assert not {"status", "bought_by", "interested_buyer", "split_buyers", "added_by"} & set(update)


def test_other_user_cannot_edit(monkeypatch):
    client = _setup(monkeypatch, GIFT)
    assert db.update_gift(5, "carl", name="x", description="", url=None, price=None, image_url=None) is False
    assert not any(e[0] == "update" for e in client.log)


def test_missing_gift_is_rejected(monkeypatch):
    client = _setup(monkeypatch, None)
    assert db.update_gift(5, "anna", name="x", description="", url=None, price=None, image_url=None) is False
    assert not any(e[0] == "update" for e in client.log)


# ---------- move_gift ----------

def _setup_move(monkeypatch, gift, target, source_year=2025):
    client = _setup(monkeypatch, gift)
    lists = {1: {"id": 1, "year": source_year}}
    if target:
        lists[target["id"]] = target
    monkeypatch.setattr(db, "_get_list", lambda lid: lists.get(lid))
    events = []
    monkeypatch.setattr(db, "_log_event", lambda *a: events.append(a))
    return client, events


BOUGHT = {"id": 5, "added_by": "anna", "list_id": 1, "name": "Lego", "status": "bought", "bought_by": "carl",
          "interested_buyer": "carl", "split_buyers": ["carl", "dana"]}


def test_author_moves_gift_and_status_is_reset(monkeypatch):
    client, events = _setup_move(monkeypatch, BOUGHT, {"id": 9, "year": 2026})
    assert db.move_gift(5, "anna", 9, 2026) is True
    update = next(e for e in client.log if e[0] == "update")[1]
    assert update == {"list_id": 9, "status": "available", "interested_buyer": None,
                      "split_buyers": [], "bought_by": None, "bought_at": None}
    assert events == [(9, 5, "Lego", "anna", "gift_moved")]  # logged in the target list


def test_only_author_can_move(monkeypatch):
    client, events = _setup_move(monkeypatch, BOUGHT, {"id": 9})
    assert db.move_gift(5, "carl", 9, 2026) is False
    assert not any(e[0] == "update" for e in client.log) and events == []


def test_move_rejects_same_list_and_unknown_target(monkeypatch):
    client, _ = _setup_move(monkeypatch, BOUGHT, {"id": 1})
    assert db.move_gift(5, "anna", 1, 2026) is False            # already there
    client, _ = _setup_move(monkeypatch, BOUGHT, None)
    assert db.move_gift(5, "anna", 99, 2026) is False           # target list doesn't exist
    assert not any(e[0] == "update" for e in client.log)


def test_cannot_move_out_of_a_current_year_list(monkeypatch):
    client, events = _setup_move(monkeypatch, BOUGHT, {"id": 9, "year": 2026}, source_year=2026)
    assert db.move_gift(5, "anna", 9, 2026) is False   # source list is from the current year
    assert not any(e[0] == "update" for e in client.log) and events == []
