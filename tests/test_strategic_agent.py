import unittest
from unittest.mock import patch

from agents.aggressive_probabilistic_belief import (
	AggressiveProbabilisticBelief,
)
from agents.probabilistic_belief_duke_fish import StrategicAgent
from src.cards import Card, Role
from src.game import Game
from src.player import Player


class StrategicAgentTests(unittest.TestCase):
	def setUp(self):
		self.agent = StrategicAgent("p1", seed=1)
		self.opponents = [Player("p2", "Opponent 1"), Player("p3", "Opponent 2")]
		self.game = Game([self.agent, *self.opponents])

	def test_reuses_probabilistic_aggressive_strategy(self):
		self.assertIsInstance(self.agent, AggressiveProbabilisticBelief)

	def test_uses_calibrated_challenge_and_block_thresholds(self):
		self.assertEqual(self.agent.challenge_probability, 0.05)
		self.assertEqual(self.agent.block_probability, 0.05)

	def test_fishes_for_a_duke_when_no_duke_is_held(self):
		self.agent.cards = [
			Card(Role.ASSASSIN),
			Card(Role.CONTESSA),
		]

		with patch.object(self.game, "perform_action", return_value={}) as perform:
			self.agent.choose_action(self.game)

		self.assertEqual(perform.call_args.args[1], "exchange")

	def test_exchange_keeps_duke_and_contessa(self):
		cards = [
			{"index": 0, "role": Role.ASSASSIN.value},
			{"index": 1, "role": Role.DUKE.value},
			{"index": 2, "role": Role.CONTESSA.value},
			{"index": 3, "role": Role.AMBASSADOR.value},
		]

		self.assertEqual(
			self.agent.decide("exchange", {"cards": cards, "keep_count": 2}),
			[1, 2],
		)

	def test_bluffs_contessa_only_when_assassination_would_eliminate_it(self):
		self.agent.cards = [Card(Role.CAPTAIN), Card(Role.ASSASSIN)]
		self.agent.reveal_card(0)
		context = {
			"eligible_blockers": [self.agent.id],
			"action": "assassinate",
			"allowed_roles": [Role.CONTESSA.value],
		}

		self.assertEqual(
			self.agent.decide("block", context),
			{"blocker_id": self.agent.id, "role": Role.CONTESSA.value},
		)

		self.agent.cards.append(Card(Role.DUKE))
		self.assertIsNone(self.agent.decide("block", context))

	def test_coups_at_seven_coins(self):
		self.agent.coins = 7

		with patch.object(self.game, "perform_action", return_value={}) as perform:
			self.agent.choose_action(self.game)

		self.assertEqual(perform.call_args.args[1], "coup")


if __name__ == "__main__":
	unittest.main()
