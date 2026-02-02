from molt_office.world import World


def test_leave_without_room_returns_conflict():
    world = World()
    event, diag = world.room_leave("ec")

    assert event.ok is False
    assert event.err["code"] == "E_CONFLICT"
    assert diag is not None
