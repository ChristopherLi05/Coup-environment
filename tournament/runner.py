import random
from collections.abc import Sequence
from dataclasses import dataclass

from src.game import Game
from src.player import Player


DEFAULT_MAX_TURNS = 100


@dataclass(frozen=True)
class GameResult:
    winner_id: str | None
    turns: int

    @property
    def is_draw(self) -> bool:
        return self.winner_id is None


@dataclass(frozen=True)
class GroupResult:
    wins: dict[str, int]
    draws: int


def play_game(
    players: Sequence[Player],
    max_turns: int = DEFAULT_MAX_TURNS,
    rng: random.Random | None = None,
) -> GameResult:
    if not 2 <= len(players) <= 6:
        raise ValueError("Coup requires 2-6 players.")
    if max_turns < 1:
        raise ValueError("The maximum turn count must be positive.")
    if len({player.id for player in players}) != len(players):
        raise ValueError("Player IDs must be unique.")

    seats = list(players)
    (rng or random.Random()).shuffle(seats)
    game = Game(seats)
    turns = 0

    while game.winner is None and turns < max_turns:
        game.current.choose_action(game)
        turns += 1

    winner = game.winner
    return GameResult(winner.id if winner is not None else None, turns)


def play_group(
    players: Sequence[Player],
    games: int = 1_000,
    max_turns: int = DEFAULT_MAX_TURNS,
    rng: random.Random | None = None,
) -> GroupResult:
    if len(players) != 4:
        raise ValueError("A tournament group must contain exactly four agents.")
    if len({player.id for player in players}) != len(players):
        raise ValueError("Agent IDs must be unique.")
    if games < 1:
        raise ValueError("The number of games must be positive.")

    generator = rng or random.Random()
    wins = dict.fromkeys((player.id for player in players), 0)
    draws = 0

    for _ in range(games):
        result = play_game(players, max_turns=max_turns, rng=generator)
        if result.winner_id is None:
            draws += 1
        else:
            wins[result.winner_id] += 1

    return GroupResult(wins=wins, draws=draws)
