from molt_office.world import World


def test_room_list_includes_seed_rooms():
    world = World()
    event, _ = world.room_list("ec")

    room_ids = {r["room_id"] for r in event.data["rooms"]}
    assert "lobby" in room_ids
    assert "meeting:public" in room_ids
    assert "coffee:public" in room_ids
