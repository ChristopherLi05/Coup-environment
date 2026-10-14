from agents.aggressive_belief import AggressiveBelief
from agents.always_duke import AlwaysDuke
from agents.belief_honest_random import BeliefHonestRandom
from agents.duke_fish import DukeFish
from agents.honest_random import HonestRandom
from agents.probabilistic_belief_tweaker import ProbabilisticBeliefTweaker
from agents.random_agent import RandomAgent
from agents.passive_agent import PassiveAgent
from agents.probabilistic_belief_honest_random import ProbabilisticBeliefHonestRandom
from agents.aggressive_probabilistic_belief import AggressiveProbabilisticBelief
from src.game import Game

import random

def main():
    playerls = [
        # AlwaysDuke("Always Duke"),
        PassiveAgent("Passive Agent"),
        # AggressiveBelief("Aggressive Belief"),
        # AggressiveBelief("Aggressive Belief 2"),
        # BeliefHonestRandom("Belief Honest Random"),
        DukeFish("Duke Fish"),
        HonestRandom("Honest Random"),
        # RandomAgent("Random Agent"),
        # ProbabilisticBeliefHonestRandom("Probabilistic Belief Honest Random"),
        # ProbabilisticBeliefHonestRandom("Probabilistic Belief Honest Random 2"),
        # AggressiveProbabilisticBelief("Aggressive Probabilistic Belief"),
        # AggressiveProbabilisticBelief("Aggressive Probabilistic Belief 2"),
        ProbabilisticBeliefTweaker("Probabilistic Belief Tweaker"),
    ]

    winners = {
        player.name: [0, 0] for player in playerls
        }

    games = 10000
    for _ in range(games):
        players = random.sample(playerls, 4)
        for i in players:
            winners[i.name][1] += 1
        random.shuffle(players)
        game = Game(players)
        # displayed_log_length = 0

        while game.winner is None:
            player = game.current

            player.choose_action(game)
            # for event in game.log[displayed_log_length:]:
            #     print(f"  {event}")
            # displayed_log_length = len(game.log)

        print(f"\nWinner: {game.winner.name}")
        winners[game.winner.name][0] += 1

    print("\nNumber of wins:", winners)
    print("Win percentages")
    for i in winners:
        print(f"{i}: {winners[i][0]/winners[i][1]*100:.2f}% ({winners[i][0]}/{winners[i][1]})")


if __name__ == "__main__":
    main()