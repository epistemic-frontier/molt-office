from molt_office.world import World


def test_board_read_returns_recent_entries():
    world = World()
    world.board_write("ec", "lobby", "msg1")
    world.board_write("ec", "lobby", "msg2")

    event, _ = world.board_read("ec", "lobby", limit=1)
    entries = event.data["entries"]
    assert len(entries) == 1
    assert entries[0]["message"] == "msg2"
