import unittest
from unittest.mock import patch

from agents.aggressive_belief import AggressiveBelief
from agents.aggressive_probabilistic_belief import (
	MAX_BLOCK_PROBABILITY,
	AggressiveProbabilisticBelief,
)
from agents.belief_honest_random import BeliefHonestRandom
from agents.probabilistic_belief import ProbabilisticBeliefTracker
from agents.probabilistic_belief_honest_random import (
	CHALLENGE_ROLE_PROBABILITY,
	ProbabilisticBeliefHonestRandom,
)
from agents.probabilistic_belief_tweaker import ProbabilisticBeliefTweaker
from src.cards import Card, Role
from src.game import Game
from src.player import Player


class ProbabilisticBeliefAgentTests(unittest.TestCase):
	def setUp(self):
		self.honest_agent = ProbabilisticBeliefHonestRandom("p1", seed=1)
		self.aggressive_agent = AggressiveProbabilisticBelief("p1", seed=1)
		self.tweaker = ProbabilisticBeliefTweaker("p3", seed=2)
		self.opponent = Player("p2", "Opponent")
		self.game = Game([self.aggressive_agent, self.opponent])

	def test_new_agents_are_independent_player_subclasses(self):
		self.assertIs(ProbabilisticBeliefHonestRandom.__base__, Player)
		self.assertIs(AggressiveProbabilisticBelief.__base__, Player)
		self.assertFalse(
			issubclass(ProbabilisticBeliefHonestRandom, BeliefHonestRandom)
		)
		self.assertFalse(
			issubclass(AggressiveProbabilisticBelief, AggressiveBelief)
		)

	def test_bots_use_probabilistic_tracker_by_composition(self):
		self.assertIsInstance(
			self.honest_agent.belief_tracker, ProbabilisticBeliefTracker
		)
		self.assertIsInstance(
			self.aggressive_agent.belief_tracker, ProbabilisticBeliefTracker
		)

	def test_probabilistic_challenge_rejects_low_probability_claim(self):
		with patch.object(
			self.honest_agent.belief_tracker,
			"role_probability",
			return_value=CHALLENGE_ROLE_PROBABILITY,
		):
			self.assertTrue(
				self.honest_agent.decide(
					"challenge",
					{"claimant_id": "p2", "role": Role.DUKE.value},
				)
			)

	def test_probabilistic_challenge_accepts_plausible_claim(self):
		with patch.object(
			self.aggressive_agent.belief_tracker,
			"role_probability",
			return_value=CHALLENGE_ROLE_PROBABILITY + 0.01,
		), patch.object(
			self.aggressive_agent.belief_tracker,
			"contradicts",
			return_value=True,
		) as contradicts:
			self.assertFalse(
				self.aggressive_agent.decide(
					"challenge",
					{"claimant_id": "p2", "role": Role.DUKE.value},
				)
			)
		contradicts.assert_not_called()

	def test_honest_random_challenge_uses_threshold_not_contradiction(self):
		with patch.object(
			self.honest_agent.belief_tracker,
			"role_probability",
			return_value=CHALLENGE_ROLE_PROBABILITY + 0.01,
		), patch.object(
			self.honest_agent.belief_tracker,
			"contradicts",
			return_value=True,
		) as contradicts:
			self.assertFalse(
				self.honest_agent.decide(
					"challenge",
					{"claimant_id": "p2", "role": Role.DUKE.value},
				)
			)
		contradicts.assert_not_called()

	def test_aggressive_block_estimate_uses_probability_threshold(self):
		self.assertFalse(
			self.aggressive_agent._cannot_block(
				self.opponent, {Role.CONTESSA}, self.game
			)
		)

		with patch.object(
			self.aggressive_agent.belief_tracker,
			"role_probability",
			return_value=MAX_BLOCK_PROBABILITY,
		), patch.object(
			self.aggressive_agent,
			"block_probability",
			MAX_BLOCK_PROBABILITY,
		):
			self.assertTrue(
				self.aggressive_agent._cannot_block(
					self.opponent, {Role.CONTESSA}, self.game
				)
			)

	def test_aggressive_block_estimate_ignores_discrete_role_beliefs(self):
		self.aggressive_agent.belief_tracker.add_belief(
			self.opponent.id, Role.CONTESSA
		)
		with patch.object(
			self.aggressive_agent.belief_tracker,
			"role_probability",
			return_value=0.0,
		):
			self.assertTrue(
				self.aggressive_agent._cannot_block(
					self.opponent, {Role.CONTESSA}, self.game
				)
			)

	def test_aggressive_block_estimate_combines_multiple_block_roles(self):
		with patch.object(
			self.aggressive_agent,
			"block_probability",
			0.2,
		), patch.object(
			self.aggressive_agent.belief_tracker,
			"role_probability",
			side_effect=lambda _player_id, role: (
				0.1 if role == Role.AMBASSADOR else 0.1
			),
		):
			self.assertTrue(
				self.aggressive_agent._cannot_block(
					self.opponent,
					{Role.AMBASSADOR, Role.CAPTAIN},
					self.game,
				)
			)

			with patch.object(
				self.aggressive_agent.belief_tracker,
				"role_probability",
				return_value=0.15,
			):
				self.assertFalse(
					self.aggressive_agent._cannot_block(
						self.opponent,
						{Role.AMBASSADOR, Role.CAPTAIN},
						self.game,
					)
				)

	def test_new_agents_sync_their_own_hand_on_game_setup(self):
		Game([self.honest_agent, Player("p3", "Other")])

		self.assertEqual(
			self.honest_agent.belief_tracker.beliefs[self.honest_agent.id],
			[card.role for card in self.honest_agent.cards],
		)

		self.assertEqual(
			self.aggressive_agent.belief_tracker.beliefs[
				self.aggressive_agent.id
			],
			[card.role for card in self.aggressive_agent.cards],
		)

	def test_aggressive_agent_keeps_original_action_priorities(self):
		self.aggressive_agent.coins = 7
		self.aggressive_agent.cards = [Card(Role.DUKE), Card(Role.ASSASSIN)]

		with patch.object(
			self.game, "perform_action", return_value={}
		) as perform_action:
			self.aggressive_agent.choose_action(self.game)

		self.assertEqual(perform_action.call_args.args[1], "coup")

	def test_tweaker_starts_with_aggressive_probabilistic_thresholds(self):
		self.assertEqual(
			self.tweaker.challenge_probability,
			CHALLENGE_ROLE_PROBABILITY,
		)
		self.assertEqual(
			self.tweaker.block_probability,
			MAX_BLOCK_PROBABILITY,
		)

	def test_tweaker_updates_thresholds_after_one_batch(self):
		self.tweaker.GAMES_PER_CONFIGURATION = 2

		self.tweaker.on_game_end(self.tweaker.id)
		self.assertEqual(
			self.tweaker.challenge_probability,
			CHALLENGE_ROLE_PROBABILITY,
		)

		self.tweaker.on_game_end("another-player")
		self.assertEqual(self.tweaker.games_played, 2)
		self.assertEqual(self.tweaker.wins, 1)
		self.assertEqual(self.tweaker.win_rate, 0.5)
		self.assertNotEqual(
			(
				self.tweaker.challenge_probability,
				self.tweaker.block_probability,
			),
			(CHALLENGE_ROLE_PROBABILITY, MAX_BLOCK_PROBABILITY),
		)

	def test_game_notifies_agents_of_the_winner(self):
		self.tweaker.GAMES_PER_CONFIGURATION = 1
		opponent = Player("p2", "Opponent")
		game = Game([self.tweaker, opponent])
		self.tweaker.coins = 7
		opponent.cards[0].revealed = True

		game.perform_action(self.tweaker.id, "coup", target_id=opponent.id)

		self.assertIs(game.winner, self.tweaker)
		self.assertEqual(self.tweaker.games_played, 1)
		self.assertEqual(self.tweaker.wins, 1)


if __name__ == "__main__":
	unittest.main()
