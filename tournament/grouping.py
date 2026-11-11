import random
from collections.abc import Sequence

from src.player import Player


GROUP_SIZE = 4


def create_groups(
    players: Sequence[Player],
    rng: random.Random | None = None,
) -> list[list[Player]]:
    if not players or len(players) % GROUP_SIZE:
        raise ValueError(
            f"The number of agents must be a positive multiple of {GROUP_SIZE}."
        )
    if len({player.id for player in players}) != len(players):
        raise ValueError("Agent IDs must be unique.")

    shuffled = list(players)
    (rng or random.Random()).shuffle(shuffled)
    return [
        shuffled[index : index + GROUP_SIZE]
        for index in range(0, len(shuffled), GROUP_SIZE)
    ]


def create_round_groups(
    players: Sequence[Player],
    bye_counts: dict[str, int],
    rng: random.Random | None = None,
) -> tuple[list[list[Player]], list[Player]]:
    if len(players) < GROUP_SIZE:
        raise ValueError(f"A tournament requires at least {GROUP_SIZE} agents.")
    if len({player.id for player in players}) != len(players):
        raise ValueError("Agent IDs must be unique.")
    if set(bye_counts) != {player.id for player in players}:
        raise ValueError("Bye counts must be provided for every agent.")
    if any(
        not isinstance(count, int) or isinstance(count, bool) or count < 0
        for count in bye_counts.values()
    ):
        raise ValueError("Bye counts must be non-negative integers.")

    shuffled = list(players)
    (rng or random.Random()).shuffle(shuffled)
    bye_count = len(shuffled) % GROUP_SIZE
    shuffled.sort(key=lambda player: bye_counts[player.id])
    byes = shuffled[:bye_count]
    active = shuffled[bye_count:]

    groups = [
        active[index : index + GROUP_SIZE]
        for index in range(0, len(active), GROUP_SIZE)
    ]
    return groups, byes
