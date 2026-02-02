from molt_office.world import World


def test_enter_unknown_room_is_bad_arg():
    world = World()
    event, diag = world.room_enter("ec", "unknown-room")

    assert event.ok is False
    assert event.err["code"] == "E_BAD_ARG"
    assert diag is not None
