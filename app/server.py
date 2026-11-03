from __future__ import annotations

import importlib
import inspect
import json
import pkgutil
import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import agents
from src.game import Game
from src.player import Player


def discover_agents() -> dict[str, type[Player]]:
    discovered: dict[str, type[Player]] = {}
    for module_info in pkgutil.iter_modules(agents.__path__):
        module = importlib.import_module(f"agents.{module_info.name}")
        for name, candidate in inspect.getmembers(module, inspect.isclass):
            if (
                candidate is not Player
                and candidate.__module__ == module.__name__
                and issubclass(candidate, Player)
            ):
                discovered[name] = candidate
    return discovered


AGENT_TYPES = discover_agents()


def display_name(agent_id: str) -> str:
    result: list[str] = []
    for index, character in enumerate(agent_id):
        if index and character.isupper() and (
            agent_id[index - 1].islower()
            or (index + 1 < len(agent_id) and agent_id[index + 1].islower())
        ):
            result.append(" ")
        result.append(character)
    return "".join(result)


class WebGame(Game):
    decision_handler: Any

    def perform_action(
        self,
        player_id: str,
        action: str,
        target_id: str | None = None,
        decision_provider: Any = None,
    ) -> dict:
        if decision_provider is None:
            decision_provider = self.decision_handler
        return super().perform_action(
            player_id, action, target_id, decision_provider
        )


class GameSession:
    def __init__(self) -> None:
        self.condition = threading.Condition()
        self.game: WebGame | None = None
        self.players_by_id: dict[str, Player] = {}
        self.agent_names: dict[str, str] = {}
        self.prompt: dict[str, Any] | None = None
        self.pending_answer: dict[str, Any] | None = None
        self.busy = False
        self.turn = 1
        self.error: str | None = None
        self.worker: threading.Thread | None = None

    def create(self, selected_agents: list[str]) -> dict[str, Any]:
        if not 1 <= len(selected_agents) <= 5:
            raise ValueError("Choose between 1 and 5 agents.")
        if any(agent_id not in AGENT_TYPES for agent_id in selected_agents):
            raise ValueError("The selected agent is not available.")

        with self.condition:
            if self.busy:
                raise ValueError("Wait for the current turn to finish.")
            players: list[Player] = [Player("human", "You")]
            self.players_by_id = {"human": players[0]}
            self.agent_names = {}
            for index, agent_id in enumerate(selected_agents, start=1):
                name = display_name(agent_id)
                player_id = f"agent-{index}"
                agent = AGENT_TYPES[agent_id](player_id, name=name)
                players.append(agent)
                self.players_by_id[player_id] = agent
                self.agent_names[player_id] = agent_id

            self.game = WebGame(players)
            self.game.decision_handler = self.decide
            self.prompt = None
            self.pending_answer = None
            self.turn = 1
            self.error = None
            return self.state()

    def state(self) -> dict[str, Any]:
        game = self.game
        if game is None:
            return {
                "game": None,
                "prompt": None,
                "busy": self.busy,
                "error": self.error,
            }

        players = []
        for player in game.players:
            players.append(
                {
                    "id": player.id,
                    "name": player.name,
                    "kind": "human" if player.id == "human" else "agent",
                    "agentId": self.agent_names.get(player.id),
                    "coins": player.coins,
                    "influence": player.influence,
                    "cards": [
                        {
                            "role": (
                                card.role.value
                                if player.id == "human" or card.revealed
                                else None
                            ),
                            "revealed": card.revealed,
                        }
                        for card in player.cards
                    ],
                }
            )
        return {
            "game": {
                "players": players,
                "currentPlayerIndex": game.current_player,
                "turn": self.turn,
                "winnerId": game.winner.id if game.winner else None,
                "log": list(game.log),
                "availableActions": (
                    ["coup"]
                    if game.current.coins >= 10
                    else [
                        "income",
                        "foreign_aid",
                        *(["coup"] if game.current.coins >= 7 else []),
                        "tax",
                        *(["assassinate"] if game.current.coins >= 3 else []),
                        "exchange",
                        "steal",
                    ]
                )
                if game.current.id == "human" and game.winner is None
                else [],
            },
            "prompt": self.prompt,
            "busy": self.busy,
            "error": self.error,
        }

    def _human_decision(
        self,
        player: Player,
        kind: str,
        context: dict[str, Any],
    ) -> Any:
        prompt_id = str(uuid.uuid4())
        if kind == "challenge":
            prompt = {
                "id": prompt_id,
                "type": "challenge",
                "decisionPlayerId": player.id,
                "claimantId": context["claimant_id"],
                "role": context["role"],
                "action": context.get("action"),
            }
        elif kind == "block":
            action = context["action"]
            prompt = {
                "id": prompt_id,
                "type": "block",
                "decisionPlayerId": player.id,
                "actorId": context["actor_id"],
                "targetId": context.get("target_id"),
                "action": action,
                "roles": (
                    ["duke"]
                    if action == "foreign_aid"
                    else context["allowed_roles"]
                ),
            }
        elif kind == "reveal_influence":
            prompt = {
                "id": prompt_id,
                "type": "influence",
                "playerId": player.id,
                "cards": context["cards"],
            }
        elif kind == "exchange":
            prompt = {
                "id": prompt_id,
                "type": "exchange",
                "playerId": player.id,
                "cards": context["cards"],
                "keepCount": context["keep_count"],
            }
        else:
            raise ValueError(f"Unknown decision type: {kind}")

        with self.condition:
            self.prompt = prompt
            self.pending_answer = {"id": prompt_id, "ready": False}
            while not self.pending_answer["ready"]:
                self.condition.wait()
            answer = self.pending_answer["value"]
            self.pending_answer = None
            self.prompt = None
            return answer

    def _decide_for(
        self,
        player: Player,
        kind: str,
        context: dict[str, Any],
    ) -> Any:
        if player.id == "human":
            return self._human_decision(player, kind, context)
        agent_decide = getattr(player, "decide", None)
        if not callable(agent_decide):
            raise ValueError(
                f"{player.name} must implement decide(kind, context)."
            )
        return agent_decide(kind, context)

    def decide(self, kind: str, context: dict[str, Any]) -> Any:
        game = self.game
        if game is None:
            raise RuntimeError("There is no active game.")

        if kind == "block" and context["action"] == "foreign_aid":
            actor_index = game.current_player
            ordered_players = [
                game.players[(actor_index + offset) % len(game.players)]
                for offset in range(1, len(game.players))
            ]
            eligible = set(context["eligible_blockers"])
            for player in ordered_players:
                if player.id not in eligible or not player.alive:
                    continue
                player_context = {
                    **context,
                    "decision_player_id": player.id,
                    "eligible_blockers": [player.id],
                }
                selection = self._decide_for(player, kind, player_context)
                if selection is None:
                    continue
                if not isinstance(selection, dict):
                    raise ValueError("A block decision must be a mapping or None.")
                return {"blocker_id": player.id}
            return None

        decision_player_id = context.get(
            "decision_player_id", context.get("player_id")
        )
        if not isinstance(decision_player_id, str):
            raise ValueError("The decision does not identify a player.")
        player = self.players_by_id[decision_player_id]
        decision = self._decide_for(player, kind, context)
        if player.id != "human":
            return decision

        if kind == "block":
            if not isinstance(decision, dict) or not decision.get("block"):
                return None
            role = decision.get("role")
            return {"blocker_id": player.id, "role": role}
        return decision

    def start_action(self, action: str, target_id: str | None) -> None:
        with self.condition:
            game = self.game
            if game is None:
                raise ValueError("Start a game first.")
            if self.busy:
                raise ValueError("The current turn is still resolving.")
            if game.current.id != "human":
                raise ValueError("It is not your turn.")
            self.busy = True
            self.error = None
            self.worker = threading.Thread(
                target=self._play_from_human,
                args=(action, target_id),
                daemon=True,
            )
            self.worker.start()

    def submit_decision(self, prompt_id: str, decision: Any) -> None:
        with self.condition:
            pending = self.pending_answer
            if pending is None or pending["id"] != prompt_id:
                raise ValueError("That decision is no longer pending.")
            kind = self.prompt["type"] if self.prompt else None
            if kind == "block":
                if not isinstance(decision, dict) or not isinstance(
                    decision.get("block"), bool
                ):
                    raise ValueError("Block decision must include a boolean.")
            elif kind == "challenge" and not isinstance(decision, bool):
                raise ValueError("Challenge decision must be a boolean.")
            elif kind == "influence" and (
                not isinstance(decision, int) or isinstance(decision, bool)
            ):
                raise ValueError("Influence decision must be a card index.")
            elif kind == "exchange" and not isinstance(decision, list):
                raise ValueError("Exchange decision must be a list of card indices.")

            pending["value"] = decision
            pending["ready"] = True
            self.condition.notify_all()

    def _play_from_human(self, action: str, target_id: str | None) -> None:
        game = self.game
        if game is None:
            return
        try:
            game.perform_action("human", action, target_id)
            self._advance_turn()
            while game.winner is None and game.current.id != "human":
                current = game.current
                choose_action = getattr(current, "choose_action", None)
                if not callable(choose_action):
                    raise ValueError(
                        f"{current.name} must implement choose_action(game)."
                    )
                choose_action(game)
                self._advance_turn()
        except Exception as error:
            with self.condition:
                self.error = str(error)
        finally:
            with self.condition:
                self.busy = False
                self.prompt = None
                if self.pending_answer is not None:
                    self.pending_answer["ready"] = True
                    self.pending_answer["value"] = False
                    self.condition.notify_all()

    def _advance_turn(self) -> None:
        game = self.game
        if game and game.current_player <= 0 and game.winner is None:
            self.turn += 1


SESSION = GameSession()


class Handler(BaseHTTPRequestHandler):
    server_version = "CoupWeb/1.0"

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/agents":
            self._send_json(
                200,
                [
                    {"id": agent_id, "name": display_name(agent_id)}
                    for agent_id in AGENT_TYPES
                ],
            )
        elif path == "/api/game":
            self._send_json(200, SESSION.state())
        else:
            self._send_json(404, {"error": "Not found."})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            body = self._read_json()
            if path == "/api/game":
                agents_selected = body.get("agents")
                if not isinstance(agents_selected, list) or not all(
                    isinstance(agent_id, str) for agent_id in agents_selected
                ):
                    raise ValueError("Agents must be a list of agent IDs.")
                self._send_json(200, SESSION.create(agents_selected))
            elif path == "/api/action":
                action = body.get("action")
                target_id = body.get("targetId")
                if not isinstance(action, str) or (
                    target_id is not None and not isinstance(target_id, str)
                ):
                    raise ValueError("Action or target is invalid.")
                SESSION.start_action(action, target_id)
                self._send_json(202, {"accepted": True})
            elif path == "/api/decision":
                prompt_id = body.get("promptId")
                if not isinstance(prompt_id, str):
                    raise ValueError("A prompt ID is required.")
                SESSION.submit_decision(prompt_id, body.get("decision"))
                self._send_json(200, {"accepted": True})
            else:
                self._send_json(404, {"error": "Not found."})
        except (ValueError, KeyError) as error:
            self._send_json(400, {"error": str(error)})

    def _read_json(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            value = json.loads(self.rfile.read(length))
        except (ValueError, json.JSONDecodeError) as error:
            raise ValueError("Request body must be valid JSON.") from error
        if not isinstance(value, dict):
            raise ValueError("Request body must be a JSON object.")
        return value

    def _send_json(self, status: int, value: Any) -> None:
        encoded = json.dumps(value).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format % args}")


if __name__ == "__main__":
    address = ("127.0.0.1", 8000)
    print(f"Coup API listening on http://{address[0]}:{address[1]}")
    ThreadingHTTPServer(address, Handler).serve_forever()
