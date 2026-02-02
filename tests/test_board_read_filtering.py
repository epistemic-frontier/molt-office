from molt_office.world import World


def test_board_read_filter_and_offset():
    world = World()
    world.board_write("ec", "lobby", "a")
    world.board_write("vk", "lobby", "b")
    world.board_write("ec", "lobby", "c")

    event, _ = world.board_read("ec", "lobby", limit=2, offset=0, entry_actor="ec")
    entries = event.data["entries"]
    assert len(entries) == 2
    assert entries[0]["message"] == "a"
    assert entries[1]["message"] == "c"
