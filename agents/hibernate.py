import random

from agents.aggressive_belief import AggressiveBelief
from src.cards import Role
from src.game import Game


class Hibernate(AggressiveBelief):
	"""Fish for a Duke, play passively, then turn aggressive in the endgame."""

	def __init__(
		self,
		player_id: str,
		name: str | None = None,
		seed: int | None = None,
	):
		super().__init__(player_id, name, seed)
		self.rng = random.Random(seed)
		self._remaining_influences: int | None = None
		self._has_acquired_duke = False

	def observe(self, kind: str, context: dict[str, object]) -> None:
		super().observe(kind, context)

		if kind == "new_game":
			player_count = context["player_count"]
			if not isinstance(player_count, int):
				raise ValueError("New game observation has an invalid player count.")
			self._remaining_influences = player_count * 2
			self._has_acquired_duke = False
			return

		if kind == "initial_hand" and context.get("player_id") == self.id:
			self._has_acquired_duke |= any(
				card.role == Role.DUKE for card in self.cards
			)
		elif kind == "exchange" and context.get("player_id") == self.id:
			self._has_acquired_duke |= any(
				card.role == Role.DUKE and not card.revealed
				for card in self.cards
			)
		elif kind == "reveal":
			if self._remaining_influences is not None:
				self._remaining_influences -= 1
			if context.get("player_id") == self.id:
				self._has_acquired_duke |= any(
					card.role == Role.DUKE and not card.revealed
					for card in self.cards
				)

	def choose_action(self, game: Game) -> dict:
		if game.current.id != self.id:
			raise ValueError("It is not this agent's turn.")
		self._game = game
		self._has_acquired_duke |= any(
			card.role == Role.DUKE for card in self.cards
		)

		if self._is_endgame:
			return super().choose_action(game)

		if self._has_acquired_duke:
			if self.coins >= 10:
				opponents = [
					player
					for player in game.alive_players
					if player.id != self.id
				]
				return game.perform_action(
					self.id, "coup", target_id=opponents[0].id
				)
			return game.perform_action(self.id, "income")

		if self.coins >= 7:
			opponents = [
				player for player in game.alive_players if player.id != self.id
			]
			highest_coin_total = max(player.coins for player in opponents)
			top_coin_opponents = [
				player for player in opponents
				if player.coins == highest_coin_total
			]
			return game.perform_action(
				self.id, "coup", target_id=self.rng.choice(top_coin_opponents).id
			)

		revealed_dukes = sum(
			card.role == Role.DUKE and card.revealed
			for player in game.players
			for card in player.cards
		)
		if revealed_dukes >= 3:
			return game.perform_action(self.id, "foreign_aid")
		return game.perform_action(self.id, "exchange")

	def decide(self, kind: str, context: dict[str, object]) -> object:
		if self._is_endgame:
			return super().decide(kind, context)

		if kind == "challenge":
			return False
		if kind == "block":
			return None
		if kind == "reveal_influence":
			return context["cards"][0]["index"]
		if kind == "exchange":
			return self._choose_fish_exchange(
				context["cards"], context["keep_count"]
			)
		raise ValueError(f"Unknown decision type: {kind}")

	@property
	def _is_endgame(self) -> bool:
		return (
			self._remaining_influences is not None
			and self._remaining_influences <= 4
		)

	def _choose_fish_exchange(
		self, cards: list[dict[str, object]], keep_count: int
	) -> list[int]:
		role_indices = {
			role: [card["index"] for card in cards if card["role"] == role.value]
			for role in Role
		}
		dukes = role_indices[Role.DUKE]
		contessas = role_indices[Role.CONTESSA]
		ambassadors = role_indices[Role.AMBASSADOR]

		preferred: list[int] = []
		if keep_count >= 2 and dukes and contessas:
			preferred = [dukes[0], contessas[0]]
		elif keep_count >= 2 and dukes and ambassadors:
			preferred = [dukes[0], ambassadors[0]]
		elif keep_count >= 2 and not dukes and contessas and ambassadors:
			preferred = [contessas[0], ambassadors[0]]
		elif dukes:
			preferred = [dukes[0]]
		elif contessas or ambassadors:
			preferred = [ambassadors[0]] if ambassadors else [contessas[0]]

		remaining = [
			card["index"]
			for card in cards
			if card["index"] not in preferred
		]
		return preferred + self.rng.sample(
			remaining, keep_count - len(preferred)
		)
