import time
import unittest

from app.server import AGENT_TYPES, GameSession
from src.cards import Card, Role


class WebAppIntegrationTests(unittest.TestCase):
    def test_agent_registry_discovers_existing_player_subclasses(self):
        self.assertIn("HonestRandom", AGENT_TYPES)
        self.assertIn("ProbabilisticBeliefTweaker", AGENT_TYPES)

    def test_python_agent_plays_its_turn_through_game_engine(self):
        session = GameSession()
        session.create(["PassiveAgent"])

        session.start_action("income", None)
        session.worker.join(timeout=2)

        self.assertFalse(session.busy)
        self.assertEqual(session.game.players[0].coins, 3)
        self.assertEqual(session.game.players[1].coins, 3)
        self.assertIn("Passive Agent takes Income.", session.game.log)

    def test_human_challenge_is_sent_to_the_selected_python_agent(self):
        session = GameSession()
        session.create(["AlwaysDuke"])
        agent = session.game.players[1]
        agent.cards = [Card(Role.ASSASSIN), Card(Role.CAPTAIN)]

        session.start_action("income", None)
        deadline = time.monotonic() + 2
        with session.condition:
            while session.prompt is None and time.monotonic() < deadline:
                session.condition.wait(timeout=deadline - time.monotonic())
            prompt = session.prompt

        self.assertIsNotNone(prompt)
        self.assertEqual(prompt["type"], "challenge")
        self.assertEqual(prompt["claimantId"], agent.id)

        session.submit_decision(prompt["id"], True)
        session.worker.join(timeout=2)

        self.assertFalse(session.busy)
        self.assertEqual(agent.influence, 1)
        self.assertIn("Always Duke cannot prove the duke claim.", session.game.log)


if __name__ == "__main__":
    unittest.main()
