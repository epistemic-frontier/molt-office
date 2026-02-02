from molt_office.world import World


def test_knock_and_admit_flow():
    world = World()
    world.ensure_private_office("ec")

    knock_event, _ = world.room_knock("vk", "office:ec", msg="May I enter?")
    assert knock_event.ok is True

    request_id = knock_event.data["request_id"]
    admit_event, _ = world.room_admit("ec", request_id)
    assert admit_event.ok is True


def test_board_write_records_entry():
    world = World()
    event, _ = world.board_write("ec", "lobby", "Hello")

    assert event.ok is True
    assert event.data["entry"]["message"] == "Hello"
