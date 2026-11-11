import copy
import random
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import combinations

from src.player import Player
from tournament.grouping import create_round_groups
from tournament.leaderboard import LeaderboardEntry, create_leaderboard
from tournament.runner import DEFAULT_MAX_TURNS, play_group
from tournament.scoring import Standing, points_for_group


DEFAULT_ROUNDS = 100
DEFAULT_GAMES_PER_GROUP = 1_000


@dataclass(frozen=True)
class TournamentResult:
    leaderboard: list[LeaderboardEntry]
    standings: dict[str, Standing]
    rounds: int
    playoff_wins: dict[str, int]


class TournamentManager:
    def __init__(
        self,
        players: Sequence[Player],
        rounds: int = DEFAULT_ROUNDS,
        games_per_group: int = DEFAULT_GAMES_PER_GROUP,
        max_turns: int = DEFAULT_MAX_TURNS,
        rng: random.Random | None = None,
    ) -> None:
        if len(players) < 4:
            raise ValueError("The tournament requires at least four agents.")
        if len({player.id for player in players}) != len(players):
            raise ValueError("Agent IDs must be unique.")
        if rounds < 1:
            raise ValueError("The number of rounds must be positive.")
        if games_per_group < 1:
            raise ValueError("The number of games per group must be positive.")
        if max_turns < 1:
            raise ValueError("The maximum turn count must be positive.")

        self.players = list(players)
        self.rounds = rounds
        self.games_per_group = games_per_group
        self.max_turns = max_turns
        self.rng = rng or random.Random()

    def run(self) -> TournamentResult:
        standings = {
            player.id: Standing(player=player) for player in self.players
        }

        for _ in range(self.rounds):
            groups, byes = create_round_groups(
                self.players,
                {player_id: standing.byes for player_id, standing in standings.items()},
                self.rng,
            )
            for player in byes:
                standings[player.id].byes += 1

            for group in groups:
                result = play_group(
                    group,
                    games=self.games_per_group,
                    max_turns=self.max_turns,
                    rng=self.rng,
                )
                group_points = points_for_group(result.wins)
                for player_id, wins in result.wins.items():
                    standing = standings[player_id]
                    standing.wins += wins
                    standing.draws += result.draws
                    standing.points += group_points[player_id]

        playoff_wins = self._resolve_final_tie(standings)
        return TournamentResult(
            leaderboard=create_leaderboard(standings, playoff_wins),
            standings=standings,
            rounds=self.rounds,
            playoff_wins=playoff_wins,
        )

    def _resolve_final_tie(
        self,
        standings: dict[str, Standing],
    ) -> dict[str, int]:
        initial_leaderboard = create_leaderboard(standings)
        leader = initial_leaderboard[0]
        finalists = [
            standings[entry.player_id]
            for entry in initial_leaderboard
            if (entry.points, entry.wins) == (leader.points, leader.wins)
        ]
        if len(finalists) < 2:
            return {}

        playoff_wins = dict.fromkeys(
            (standing.player.id for standing in finalists), 0
        )
        series = {
            (left.player.id, right.player.id): self._create_playoff_series(
                left.player, right.player
            )
            for left, right in combinations(finalists, 2)
        }

        while True:
            for players, teams in series.values():
                result = play_group(
                    players,
                    games=self.games_per_group,
                    max_turns=self.max_turns,
                    rng=self.rng,
                )
                for copy_id, wins in result.wins.items():
                    playoff_wins[teams[copy_id]] += wins

            highest_wins = max(playoff_wins.values())
            if list(playoff_wins.values()).count(highest_wins) == 1:
                return playoff_wins

    @staticmethod
    def _create_playoff_series(
        left: Player,
        right: Player,
    ) -> tuple[list[Player], dict[str, str]]:
        players = []
        teams: dict[str, str] = {}
        for player in (left, right):
            for copy_number in range(2):
                player_copy = copy.deepcopy(player)
                copy_id = f"playoff-{player.id}-{copy_number}"
                player_copy.id = copy_id
                player_copy.name = player.name
                belief_tracker = getattr(player_copy, "belief_tracker", None)
                if getattr(belief_tracker, "player_id", None) == player.id:
                    setattr(belief_tracker, "player_id", copy_id)
                players.append(player_copy)
                teams[copy_id] = player.id
        return players, teams
