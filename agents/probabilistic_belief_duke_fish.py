from agents.aggressive_probabilistic_belief import (
	AggressiveProbabilisticBelief,
)
from src.cards import Role
from src.game import Game


class ProbabilsticBeliefDukeFish(AggressiveProbabilisticBelief):
	"""Fish for a Duke while using probabilistic challenges and defenses."""

	def choose_action(self, game: Game) -> dict:
		if game.current.id != self.id:
			raise ValueError("It is not this agent's turn.")

		roles = self._active_roles()
		if self.coins >= 7:
			opponents = [
				player for player in game.alive_players if player.id != self.id
			]
			top_coins = max(player.coins for player in opponents)
			targets = [
				player for player in opponents if player.coins == top_coins
			]
			return game.perform_action(
				self.id, "coup", target_id=self.rng.choice(targets).id
			)

		if Role.DUKE in roles:
			return game.perform_action(self.id, "tax")

		revealed_dukes = sum(
			card.role == Role.DUKE and card.revealed
			for player in game.players
			for card in player.cards
		)
		action = "foreign_aid" if revealed_dukes >= 3 else "exchange"
		return game.perform_action(self.id, action)

	def decide(self, kind: str, context: dict[str, object]) -> object:
		if kind == "reveal_influence":
			cards = context["cards"]
			non_dukes = [
				card for card in cards if card["role"] != Role.DUKE.value
			]
			return (non_dukes or cards)[0]["index"]

		if kind == "exchange":
			return self._choose_fish_exchange(
				context["cards"], context["keep_count"]
			)

		decision = super().decide(kind, context)
		if (
			kind == "block"
			and decision is None
			and context["action"] == "assassinate"
			and self.id in context["eligible_blockers"]
			and self.influence == 1
		):
			return {
				"blocker_id": self.id,
				"role": Role.CONTESSA.value,
			}
		return decision

	def _choose_fish_exchange(
		self, cards: list[dict[str, object]], keep_count: int
	) -> list[int]:
		role_indices = {
			role: [
				card["index"] for card in cards if card["role"] == role.value
			]
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
			preferred = [
				ambassadors[0] if ambassadors else contessas[0]
			]

		remaining = [
			card["index"]
			for card in cards
			if card["index"] not in preferred
		]
		return preferred + self.rng.sample(
			remaining, keep_count - len(preferred)
		)

	def _active_roles(self) -> set[Role]:
		return {card.role for card in self.cards if not card.revealed}
