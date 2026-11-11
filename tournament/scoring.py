from collections.abc import Mapping
from dataclasses import dataclass

from src.player import Player


@dataclass
class Standing:
    player: Player
    points: int = 0
    wins: int = 0
    draws: int = 0
    byes: int = 0


def points_for_group(wins: Mapping[str, int]) -> dict[str, int]:
    if len(wins) != 4:
        raise ValueError("Group scoring requires exactly four agents.")
    if any(
        not isinstance(count, int) or isinstance(count, bool) or count < 0
        for count in wins.values()
    ):
        raise ValueError("Win totals must be non-negative integers.")

    ranking = sorted(wins.items(), key=lambda result: result[1], reverse=True)
    points: dict[str, int] = {}
    previous_wins: int | None = None
    rank_index = 0

    for index, (player_id, player_wins) in enumerate(ranking):
        if player_wins != previous_wins:
            rank_index = index
            previous_wins = player_wins
        points[player_id] = 4 - rank_index

    return points
