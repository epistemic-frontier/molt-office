from molt_office.world import World


def test_only_owner_can_admit():
    world = World()
    world.ensure_private_office("ec")

    knock_event, _ = world.room_knock("vk", "office:ec")
    request_id = knock_event.data["request_id"]

    event, _ = world.room_admit("vk", request_id)
    assert event.ok is False
    assert event.err["code"] == "E_FORBIDDEN"
