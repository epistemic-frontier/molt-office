from molt_office.world import World


def test_private_room_requires_knock():
    world = World()
    world.ensure_private_office("ec")

    event, diag = world.room_enter("vk", "office:ec")

    assert event.ok is False
    assert event.err["code"] == "E_NEED_KNOCK"
    assert diag is not None
    assert diag.cmd == "agent.diag"


def test_consecutive_failures_trigger_hint():
    world = World()
    world.ensure_private_office("ec")

    for _ in range(4):
        event, _ = world.room_enter("vk", "office:ec")

    assert event.ok is False
    assert event.data["hint"] is not None
