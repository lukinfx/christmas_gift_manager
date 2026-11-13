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
