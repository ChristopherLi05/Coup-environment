import unittest

from simulate import MAX_TURNS_PER_PLAYER, _play_game
from src.game import Game
from src.player import Player


class SimulationTests(unittest.TestCase):
	def test_draws_after_each_surviving_player_has_taken_100_turns(self):
		players = [
			Player("p1", "Player 1"),
			Player("p2", "Player 2"),
			Player("p3", "Player 3"),
		]
		game = Game(players)
		turn_counts = {player.id: 0 for player in players}

		for player in players:
			def end_turn(current_game: Game, player_id: str = player.id) -> None:
				turn_counts[player_id] += 1
				current_game._end_turn()

			player.choose_action = end_turn

		is_draw, reached_endgame = _play_game(game, players[0].id)
		self.assertTrue(is_draw)
		self.assertFalse(reached_endgame)
		self.assertEqual(
			turn_counts,
			{player.id: MAX_TURNS_PER_PLAYER for player in players},
		)

	def test_tracks_when_agent_takes_a_turn_in_the_endgame(self):
		players = [Player("p1", "Player 1"), Player("p2", "Player 2")]
		game = Game(players)

		for player in players:
			def lose_one_influence(current_game: Game, agent: Player = player) -> None:
				if agent.influence > 1:
					card_index = next(
						index
						for index, card in enumerate(agent.cards)
						if not card.revealed
					)
					agent.reveal_card(card_index)
				current_game._end_turn()

			player.choose_action = lose_one_influence

		is_draw, reached_endgame = _play_game(game, players[0].id)

		self.assertTrue(is_draw)
		self.assertTrue(reached_endgame)


if __name__ == "__main__":
	unittest.main()
