import rules

LIST = {"id": 1, "recipients": ["anna", "bob"]}
GIFTS = [
    {"id": 1, "added_by": "anna"},
    {"id": 2, "added_by": "carl"},
    {"id": 3, "added_by": "bob"},
]


def test_recipient_sees_only_own_gifts():
    assert [g["id"] for g in rules.visible_gifts(LIST, GIFTS, "anna")] == [1]


def test_non_recipient_sees_everything():
    assert len(rules.visible_gifts(LIST, GIFTS, "carl")) == 3


def test_status_hidden_from_recipient_only():
    assert not rules.can_see_status(LIST, "bob")
    assert rules.can_see_status(LIST, "carl")


def test_only_creator_can_delete():
    assert rules.can_delete_gift(GIFTS[0], "anna")
    assert not rules.can_delete_gift(GIFTS[0], "carl")


USERS = [
    {"username": "lukas", "email": "Lukas@Gmail.com"},
    {"username": "verca", "email": "verca@gmail.com"},
]


def test_email_match_is_case_insensitive():
    assert rules.find_user_by_email(USERS, " lukas@gmail.COM ")["username"] == "lukas"


def test_unknown_or_empty_email_rejected():
    assert rules.find_user_by_email(USERS, "evil@gmail.com") is None
    assert rules.find_user_by_email(USERS, "") is None
    assert rules.find_user_by_email([{"username": "x", "email": None}], "") is None


def test_only_the_reserver_can_release():
    reserved = {"status": "want_to_buy", "interested_buyer": "carl"}
    assert rules.can_release_gift(reserved, "carl")
    assert not rules.can_release_gift(reserved, "dana")
    bought = {"status": "bought", "bought_by": "dana"}
    assert rules.can_release_gift(bought, "dana")
    assert not rules.can_release_gift(bought, "carl")
    assert not rules.can_release_gift({"status": "available"}, "carl")


def test_events_hidden_for_lists_where_user_is_recipient():
    lists = {1: {"id": 1, "recipients": ["anna"]}, 2: {"id": 2, "recipients": ["bob"]}}
    events = [{"list_id": 1, "kind": "bought"}, {"list_id": 2, "kind": "bought"}, {"list_id": 99, "kind": "x"}]
    assert [e["list_id"] for e in rules.visible_events(events, lists, "anna")] == [2]
    assert [e["list_id"] for e in rules.visible_events(events, lists, "carl")] == [1, 2]


from datetime import date


def test_clean_url():
    assert rules.clean_url("example.com/x") == "https://example.com/x"
    assert rules.clean_url("http://shop.cz") == "http://shop.cz"
    assert rules.clean_url("javascript:alert(1)") is None
    assert rules.clean_url("ftp://x.com") is None
    assert rules.clean_url("not a url") is None
    assert rules.clean_url("   ") is None and rules.clean_url(None) is None


def test_parse_price():
    assert rules.parse_price("1 200") == 1200.0
    assert rules.parse_price("1200,50 Kč") == 1200.5
    assert rules.parse_price("") is None and rules.parse_price("abc") is None
    assert rules.parse_price("1.2.3") is None


def test_days_until_christmas():
    assert rules.days_until_christmas(date(2026, 12, 24)) == 0
    assert rules.days_until_christmas(date(2026, 12, 20)) == 4
    assert rules.days_until_christmas(date(2026, 12, 25)) == 364


def test_default_year():
    assert rules.default_year([2025], 2026) == 2025
    assert rules.default_year([2025, 2026], 2026) == 2026
    assert rules.default_year([], 2026) == 2026


def test_purchase_summary_and_totals():
    lists = [{"id": 1, "recipients": ["anna"]}, {"id": 2, "recipients": ["me"]}]
    gifts = {
        1: [
            {"id": 1, "status": "want_to_buy", "interested_buyer": "me", "price": 100},
            {"id": 2, "status": "bought", "bought_by": "me", "price": 250.5},
            {"id": 3, "status": "bought", "bought_by": "other", "price": 999},
            {"id": 4, "status": "want_to_buy_shared", "interested_buyer": "me", "price": None},
        ],
        2: [{"id": 5, "status": "bought", "bought_by": "me", "price": 5}],
    }
    summary = rules.purchase_summary(lists, gifts, "me")
    assert [s["list"]["id"] for s in summary] == [1]  # list 2: I'm the recipient
    assert [g["id"] for g in summary[0]["gifts"]] == [1, 2, 4]
    assert rules.money_totals(summary[0]["gifts"], "me") == {"reserved": 100.0, "bought": 250.5, "unpriced": 1}


def test_parse_ts_and_new_events():
    since = rules.parse_ts("2026-11-01T10:00:00+00:00")
    assert rules.parse_ts("nonsense") is None and rules.parse_ts(None) is None
    events = [
        {"list_id": 1, "actor": "carl", "created_at": "2026-11-02T08:00:00.123456+00:00"},  # new
        {"list_id": 1, "actor": "me", "created_at": "2026-11-02T09:00:00+00:00"},           # mine
        {"list_id": 2, "actor": "carl", "created_at": "2026-10-30T09:00:00+00:00"},         # old
        {"list_id": 2, "actor": "dana", "created_at": "2026-11-03T09:00:00Z"},              # new
    ]
    new = rules.new_events(events, since, "me")
    assert [e["actor"] for e in new] == ["carl", "dana"]
    assert rules.count_by_list(new) == {1: 1, 2: 1}
    assert rules.new_events(events, None, "me") == []


def test_is_admin():
    assert rules.is_admin({"is_admin": True})
    assert not rules.is_admin({"is_admin": False}) and not rules.is_admin({}) and not rules.is_admin(None)


def test_lists_to_copy_skips_existing():
    src = [{"name": "Vojta dárky", "recipients": ["vojta"]}, {"name": "Rodiče", "recipients": ["tomas", "lucie"]}]
    tgt = [{"name": " vojta dárky ", "recipients": ["vojta"]}, {"name": "Rodiče", "recipients": ["lucie", "tomas"]}]
    assert rules.lists_to_copy(src, tgt) == []
    assert rules.lists_to_copy(src, tgt[:1]) == [src[1]]


def test_is_recent():
    from datetime import datetime, timezone
    now = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)
    assert rules.is_recent("2026-11-18T13:00:00+00:00", now)       # 2 days 23 h
    assert not rules.is_recent("2026-11-17T11:00:00+00:00", now)   # 3 days 1 h
    assert not rules.is_recent("2026-11-21T00:00:00+00:00", now)   # in the future (clock skew)
    assert not rules.is_recent(None, now) and not rules.is_recent("junk", now)


def _split(price, people, status="want_to_buy_shared", **extra):
    return {"id": 1, "status": status, "price": price, "split_buyers": people,
            "interested_buyer": people[0] if people else None, **extra}


def test_split_share_is_equal_parts():
    assert rules.my_share(_split(100, ["a", "b"]), "a") == 50.0
    assert rules.my_share(_split(100, ["a", "b", "c"]), "c") == 33.33
    assert rules.my_share(_split(100, ["a"]), "a") == 100.0
    assert rules.my_share(_split(None, ["a", "b"]), "a") is None
    # not part of the split -> not their share
    assert rules.my_share(_split(100, ["a", "b"]), "z") == 100.0
    # bought split gift keeps the split
    assert rules.my_share(_split(90, ["a", "b", "c"], status="bought", bought_by="a"), "b") == 30.0


def test_split_participants_fallback_for_old_rows():
    old = {"status": "want_to_buy_shared", "interested_buyer": "a", "split_buyers": []}
    assert rules.split_participants(old) == ["a"]
    assert rules.split_participants({"status": "available"}) == []


def test_join_leave_and_mark_bought_permissions():
    g = _split(100, ["a", "b"])
    assert rules.can_join_split(g, "c") and not rules.can_join_split(g, "a")
    assert rules.can_leave_split(g, "a") and not rules.can_leave_split(g, "c")
    assert rules.can_mark_bought(g, "a") and not rules.can_mark_bought(g, "c")
    assert rules.can_mark_bought({"status": "want_to_buy", "interested_buyer": "a"}, "z")
    assert not rules.can_mark_bought({"status": "bought"}, "a")
    assert not rules.can_release_gift(g, "a")  # split gifts use "leave", not "release"


def test_purchases_include_split_gifts_with_my_share():
    lists = [{"id": 1, "recipients": ["anna"]}]
    gifts = {1: [_split(100, ["me", "carl"], id=7), _split(60, ["carl", "dana"], id=8),
                 _split(90, ["me", "carl", "dana"], id=9, status="bought", bought_by="carl")]}
    mine = rules.purchase_summary(lists, gifts, "me")[0]["gifts"]
    assert [g["id"] for g in mine] == [7, 9]
    assert rules.money_totals(mine, "me") == {"reserved": 50.0, "bought": 30.0, "unpriced": 0}


def test_only_author_can_edit():
    assert rules.can_edit_gift({"added_by": "anna"}, "anna")
    assert not rules.can_edit_gift({"added_by": "anna"}, "carl")


def test_move_permissions_and_targets():
    assert rules.can_move_gift({"added_by": "anna"}, "anna")
    assert not rules.can_move_gift({"added_by": "anna"}, "carl")
    lists = [
        {"id": 1, "year": 2025}, {"id": 2, "year": 2026}, {"id": 3, "year": 2026}, {"id": 4, "year": 2025},
    ]
    assert [l["id"] for l in rules.move_targets(lists, 2, 2026)] == [3]   # not the list it is already in
    assert [l["id"] for l in rules.move_targets(lists, 2, 2025)] == [1, 4]
    assert rules.move_targets(lists, 2, 2030) == []
