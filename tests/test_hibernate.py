import unittest
from unittest.mock import patch

from agents.hibernate import Hibernate
from src.cards import Card, Role
from src.game import Game
from src.player import Player


class HibernateTests(unittest.TestCase):
	def setUp(self):
		self.agent = Hibernate("p1", seed=7)
		self.opponent = Player("p2", "Opponent")
		self.game = Game([self.agent, self.opponent, Player("p3", "Third player")])

	def test_fishes_for_duke_before_acquiring_one(self):
		self.agent.cards = [Card(Role.CAPTAIN), Card(Role.ASSASSIN)]
		self.agent._has_acquired_duke = False

		with patch.object(self.game, "perform_action", return_value={}) as perform:
			self.agent.choose_action(self.game)

		self.assertEqual(perform.call_args.args[1], "exchange")

	def test_hibernates_with_income_after_acquiring_duke(self):
		self.agent.cards = [Card(Role.DUKE), Card(Role.CAPTAIN)]

		with patch.object(self.game, "perform_action", return_value={}) as perform:
			self.agent.choose_action(self.game)

		self.assertEqual(perform.call_args.args[1], "income")

	def test_hibernating_agent_coups_when_forced(self):
		self.agent.cards = [Card(Role.DUKE), Card(Role.CAPTAIN)]
		self.agent.coins = 10

		with patch.object(self.game, "perform_action", return_value={}) as perform:
			self.agent.choose_action(self.game)

		self.assertEqual(perform.call_args.args[1], "coup")
		self.assertEqual(perform.call_args.kwargs["target_id"], self.opponent.id)

	def test_passive_challenge_behavior_until_four_influences_remain(self):
		self.agent.belief_tracker.add_belief(self.opponent.id, Role.DUKE)
		self.agent.belief_tracker.add_belief(self.opponent.id, Role.CAPTAIN)

		self.assertFalse(
			self.agent.decide(
				"challenge",
				{"claimant_id": self.opponent.id, "role": Role.ASSASSIN.value},
			)
		)

		self.agent.observe(
			"reveal", {"player_id": self.opponent.id, "role": Role.ASSASSIN.value}
		)
		self.agent.observe(
			"reveal", {"player_id": self.opponent.id, "role": Role.CONTESSA.value}
		)

		self.assertTrue(
			self.agent.decide(
				"challenge",
				{"claimant_id": self.opponent.id, "role": Role.AMBASSADOR.value},
			)
		)

	def test_uses_duke_fish_exchange_preferences(self):
		cards = [
			{"index": index, "role": role.value}
			for index, role in enumerate(
				[Role.ASSASSIN, Role.DUKE, Role.CONTESSA, Role.AMBASSADOR]
			)
		]

		self.assertEqual(
			self.agent.decide("exchange", {"cards": cards, "keep_count": 2}),
			[1, 2],
		)

	def test_tracks_claims_before_endgame(self):
		self.agent.observe(
			"claim",
			{
				"claimant_id": self.opponent.id,
				"role": Role.DUKE.value,
				"disproven": False,
			},
		)

		self.assertIn(Role.DUKE, self.agent.belief_tracker.beliefs[self.opponent.id])

	def test_endgame_uses_aggressive_belief_action_selection(self):
		self.agent.observe(
			"reveal", {"player_id": self.opponent.id, "role": Role.ASSASSIN.value}
		)
		self.agent.observe(
			"reveal", {"player_id": self.opponent.id, "role": Role.CONTESSA.value}
		)
		self.agent.cards = [Card(Role.DUKE), Card(Role.ASSASSIN)]

		with patch.object(self.game, "perform_action", return_value={}) as perform:
			self.agent.choose_action(self.game)

		self.assertEqual(perform.call_args.args[1], "tax")


if __name__ == "__main__":
	unittest.main()
