from contextlib import redirect_stdout
from itertools import combinations
import os
from pathlib import Path
import random
import sys

import matplotlib.pyplot as plt
from matplotlib.patches import Patch

from agents.aggressive_belief import AggressiveBelief
from agents.always_duke import AlwaysDuke
from agents.belief_honest_random import BeliefHonestRandom
from agents.duke_fish import DukeFish
from agents.honest_random import HonestRandom
from agents.passive_agent import PassiveAgent
from agents.random_agent import RandomAgent
from src.game import Game
from src.player import Player


GAMES_PER_MATCHUP = 1_000
MATCHUP_COUNT = 21
PLOT_ROWS = 3
PLOT_COLUMNS = 7
AGENT_COLORS = {
    "Always Duke": "#1f77b4",
    "Passive Agent": "#ff7f0e",
    "Aggressive Belief": "#2ca02c",
    "Belief Honest Random": "#d62728",
    "Duke Fish": "#9467bd",
    "Honest Random": "#8c564b",
    "Random Agent": "#e377c2",
}

PlayerFactory = type[Player]
PlayerSpec = tuple[str, PlayerFactory]
MatchupResult = tuple[tuple[str, str], dict[str, float]]


def simulate_matchups(
    playerls: list[PlayerSpec],
    games_per_matchup: int = GAMES_PER_MATCHUP,
) -> list[MatchupResult]:
    results = []

    for matchup_number, matchup in enumerate(combinations(playerls, 2), start=1):
        names = (matchup[0][0], matchup[1][0])
        wins = dict.fromkeys(names, 0)

        for _ in range(games_per_matchup):
            players = [
                factory(f"player-{team_index}-{copy_index}", name)
                for team_index, (name, factory) in enumerate(matchup)
                for copy_index in range(2)
            ]
            random.shuffle(players)
            game = Game(players)

            while game.winner is None:
                game.current.choose_action(game)

            wins[game.winner.name] += 1

        win_rates = {
            name: wins[name] / games_per_matchup * 100
            for name in names
        }
        results.append(((names[0], names[1]), win_rates))
        print(
            f"Completed matchup {matchup_number}/{MATCHUP_COUNT}",
            file=sys.stderr,
            flush=True,
        )

    if len(results) != MATCHUP_COUNT:
        raise ValueError(
            f"Expected {MATCHUP_COUNT} matchups, got {len(results)}."
        )
    return results


def plot_results(results: list[MatchupResult], output_path: Path) -> None:
    figure, axes = plt.subplots(
        PLOT_ROWS,
        PLOT_COLUMNS,
        figsize=(28, 12),
        sharey=True,
    )
    figure.subplots_adjust(
        top=0.85, bottom=0.1, left=0.06, right=0.99, hspace=0.6, wspace=0.3
    )

    for matchup_number, (axis, (names, win_rates)) in enumerate(
        zip(axes.flat, results), start=1
    ):
        rates = [win_rates[name] for name in names]
        bars = axis.bar(
            names,
            rates,
            color=[AGENT_COLORS[name] for name in names],
        )
        axis.set_ylim(0, 100)
        axis.set_yticks((0, 25, 50, 75, 100))
        axis.set_title(f"{names[0]} vs {names[1]}", fontsize=9)
        axis.set_axisbelow(True)
        axis.grid(axis="y", alpha=0.25)
        axis.tick_params(axis="x", labelrotation=35, labelsize=7)
        axis.tick_params(axis="y", labelsize=7)

        for bar, rate in zip(bars, rates):
            axis.annotate(
                f"{rate:.1f}%",
                (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8,
            )

    figure.suptitle(
        f"2 vs 2 bot team win rates ({GAMES_PER_MATCHUP:,} games per matchup)",
        fontsize=16,
        y=0.99,
    )
    figure.legend(
        handles=[
            Patch(facecolor=color, label=name)
            for name, color in AGENT_COLORS.items()
        ],
        loc="upper center",
        bbox_to_anchor=(0.5, 0.94),
        ncol=len(AGENT_COLORS),
        fontsize=10,
    )
    figure.supxlabel("Bot team")
    figure.supylabel("Team win rate (%)")
    figure.savefig(output_path, dpi=180)
    plt.show()


def main() -> None:
    playerls: list[PlayerSpec] = [
        ("Always Duke", AlwaysDuke),
        ("Passive Agent", PassiveAgent),
        ("Aggressive Belief", AggressiveBelief),
        ("Belief Honest Random", BeliefHonestRandom),
        ("Duke Fish", DukeFish),
        ("Honest Random", HonestRandom),
        ("Random Agent", RandomAgent),
    ]

    with open(os.devnull, "w", encoding="utf-8") as null_output:
        with redirect_stdout(null_output):
            results = simulate_matchups(playerls)

    output_path = Path(__file__).with_name("simulation_2v2_results.png")
    plot_results(results, output_path)
    print(f"Saved plot to {output_path}")


if __name__ == "__main__":
    main()
