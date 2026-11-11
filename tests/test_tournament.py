import random
import unittest
from unittest.mock import patch

from agents.aggressive_belief import AggressiveBelief
from src.game import Game
from src.player import Player
from tournament.grouping import create_groups, create_round_groups
from tournament.leaderboard import create_leaderboard
from tournament.manager import TournamentManager
from tournament.runner import GroupResult, play_game, play_group
from tournament.scoring import Standing, points_for_group


class IncomeCoupAgent(Player):
    def choose_action(self, game: Game) -> dict:
        if self.coins < 7:
            action = "income"
            target_id = None
        else:
            action = "coup"
            target_id = next(
                player.id for player in game.alive_players if player.id != self.id
            )
        return game.perform_action(
            self.id,
            action,
            target_id=target_id,
            decision_provider=self.decide,
        )

    def decide(self, kind: str, context: dict[str, object]) -> object:
        if kind == "challenge":
            return False
        if kind == "block":
            return None
        if kind == "reveal_influence":
            return context["cards"][0]["index"]
        if kind == "exchange":
            return list(range(context["keep_count"]))
        raise ValueError(f"Unknown decision type: {kind}")


class PassTurnPlayer(Player):
    def choose_action(self, game: Game) -> None:
        game._end_turn()


def make_players(player_type: type[Player] = IncomeCoupAgent) -> list[Player]:
    return [
        player_type(f"p{index}", f"Player {index}")
        for index in range(4)
    ]


class TournamentGroupingTests(unittest.TestCase):
    def test_creates_shuffled_groups_of_four(self):
        players = [
            IncomeCoupAgent(f"p{index}", f"Player {index}")
            for index in range(8)
        ]

        groups = create_groups(players, random.Random(7))

        self.assertEqual([len(group) for group in groups], [4, 4])
        self.assertEqual(
            {player.id for group in groups for player in group},
            {player.id for player in players},
        )

    def test_rejects_incomplete_groups(self):
        with self.assertRaisesRegex(ValueError, "multiple of 4"):
            create_groups(make_players()[:3])

    def test_round_groups_rotate_byes_evenly(self):
        players = [
            IncomeCoupAgent(f"p{index}", f"Player {index}")
            for index in range(14)
        ]
        bye_counts = dict.fromkeys((player.id for player in players), 0)
        rng = random.Random(7)

        for _ in range(7):
            groups, byes = create_round_groups(players, bye_counts, rng)

            self.assertEqual([len(group) for group in groups], [4, 4, 4])
            self.assertEqual(len(byes), 2)
            self.assertEqual(
                len({player.id for player in byes} | {
                    player.id for group in groups for player in group
                }),
                len(players),
            )
            for player in byes:
                bye_counts[player.id] += 1

        self.assertEqual(set(bye_counts.values()), {1})


class TournamentScoringTests(unittest.TestCase):
    def test_tied_agents_receive_the_points_for_the_highest_shared_rank(self):
        points = points_for_group(
            {"first": 10, "second": 8, "third": 8, "last": 1}
        )

        self.assertEqual(
            points,
            {"first": 4, "second": 3, "third": 3, "last": 1},
        )

    def test_first_place_tie_gives_both_agents_four_points(self):
        points = points_for_group(
            {"first": 10, "second": 10, "third": 8, "last": 1}
        )

        self.assertEqual(points["first"], 4)
        self.assertEqual(points["second"], 4)
        self.assertEqual(points["third"], 2)

    def test_leaderboard_breaks_point_ties_with_total_wins(self):
        players = make_players()
        standings = {
            players[0].id: Standing(players[0], points=4, wins=5),
            players[1].id: Standing(players[1], points=4, wins=6),
            players[2].id: Standing(players[2], points=3, wins=20),
            players[3].id: Standing(players[3], points=4, wins=6),
        }

        entries = create_leaderboard(standings)

        self.assertEqual(
            [(entry.player_id, entry.rank) for entry in entries],
            [("p1", 1), ("p3", 1), ("p0", 3), ("p2", 4)],
        )


class TournamentRunnerTests(unittest.TestCase):
    def test_draws_after_maximum_total_turns(self):
        result = play_game(
            make_players(PassTurnPlayer),
            max_turns=11,
            rng=random.Random(1),
        )

        self.assertTrue(result.is_draw)
        self.assertEqual(result.turns, 11)

    def test_group_runs_requested_games_and_counts_draws_as_no_wins(self):
        players = make_players(PassTurnPlayer)

        result = play_group(
            players,
            games=3,
            max_turns=4,
            rng=random.Random(2),
        )

        self.assertEqual(result.draws, 3)
        self.assertEqual(result.wins, {player.id: 0 for player in players})

    def test_group_runs_games_that_finish_with_a_winner(self):
        result = play_group(make_players(), games=2, rng=random.Random(3))

        self.assertEqual(sum(result.wins.values()), 2)
        self.assertEqual(result.draws, 0)


class TournamentManagerTests(unittest.TestCase):
    def test_runs_rounds_and_returns_standings(self):
        result = TournamentManager(
            make_players(),
            rounds=1,
            games_per_group=1,
            rng=random.Random(4),
        ).run()

        self.assertEqual(result.rounds, 1)
        self.assertEqual(len(result.leaderboard), 4)
        self.assertEqual(sum(standing.wins for standing in result.standings.values()), 1)
        self.assertEqual(result.playoff_wins, {})
        self.assertEqual(sum(standing.byes for standing in result.standings.values()), 0)

    def test_final_tie_uses_a_2v2_series_and_repeatable_agent_copies(self):
        players = [
            AggressiveBelief(f"p{index}", f"Player {index}")
            for index in range(2)
        ]
        standings = {
            player.id: Standing(player=player, points=4, wins=10)
            for player in players
        }

        def left_team_wins(copies, games, max_turns, rng):
            self.assertEqual(max_turns, 100)
            self.assertIsInstance(rng, random.Random)
            return GroupResult(
                wins={
                    player.id: int(index == 0)
                    for index, player in enumerate(copies)
                },
                draws=games - 1,
            )

        manager = TournamentManager(
            make_players(),
            rounds=1,
            games_per_group=1,
            rng=random.Random(5),
        )
        with patch("tournament.manager.play_group", side_effect=left_team_wins):
            playoff_wins = manager._resolve_final_tie(standings)
        copies = manager._create_playoff_series(players[0], players[1])[0]

        self.assertEqual(playoff_wins, {"p0": 1, "p1": 0})
        self.assertTrue(
            all(
                player.belief_tracker.player_id == player.id
                for player in copies
            )
        )


if __name__ == "__main__":
    unittest.main()
