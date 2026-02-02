import os

import pytest

from molt_office.storage import RedisBackend
from molt_office.world import World


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("MOLT_REDIS_URL") is None,
    reason="MOLT_REDIS_URL not set",
)
def test_redis_room_flow():
    backend = RedisBackend(url=os.environ["MOLT_REDIS_URL"], prefix="molt-test")
    world = World(backend=backend)

    world.ensure_private_office("ec")

    event, _ = world.room_enter("ec", "lobby")
    assert event.ok is True

    knock_event, _ = world.room_knock("vk", "office:ec")
    assert knock_event.ok is True
