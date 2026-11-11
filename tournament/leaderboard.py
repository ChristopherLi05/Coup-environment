from collections.abc import Mapping
from dataclasses import dataclass

from tournament.scoring import Standing


@dataclass(frozen=True)
class LeaderboardEntry:
    rank: int
    player_id: str
    name: str
    points: int
    wins: int
    draws: int
    byes: int
    playoff_wins: int


def create_leaderboard(
    standings: Mapping[str, Standing],
    playoff_wins: Mapping[str, int] | None = None,
) -> list[LeaderboardEntry]:
    if not standings:
        raise ValueError("A leaderboard requires at least one standing.")
    playoff_wins = playoff_wins or {}
    ordered = sorted(
        standings.values(),
        key=lambda standing: (
            -standing.points,
            -standing.wins,
            -playoff_wins.get(standing.player.id, 0),
            standing.player.name.casefold(),
            standing.player.id,
        ),
    )

    entries = []
    previous_rank_key: tuple[int, int, int] | None = None
    rank = 0
    for index, standing in enumerate(ordered, start=1):
        player_id = standing.player.id
        rank_key = (
            standing.points,
            standing.wins,
            playoff_wins.get(player_id, 0),
        )
        if rank_key != previous_rank_key:
            rank = index
            previous_rank_key = rank_key
        entries.append(
            LeaderboardEntry(
                rank=rank,
                player_id=player_id,
                name=standing.player.name,
                points=standing.points,
                wins=standing.wins,
                draws=standing.draws,
                byes=standing.byes,
                playoff_wins=playoff_wins.get(player_id, 0),
            )
        )

    return entries
