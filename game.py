"""
Crazy Eights card game implementation
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import random


class Suit(Enum):
    """Card suits"""
    HEARTS = "♥"
    DIAMONDS = "♦"
    CLUBS = "♣"
    SPADES = "♠"


class Rank(Enum):
    """Card ranks"""
    ACE = "A"
    TWO = "2"
    THREE = "3"
    FOUR = "4"
    FIVE = "5"
    SIX = "6"
    SEVEN = "7"
    EIGHT = "8"
    NINE = "9"
    TEN = "10"
    JACK = "J"
    QUEEN = "Q"
    KING = "K"


@dataclass
class Card:
    """Represents a card"""
    suit: Suit
    rank: Rank

    def __eq__(self, other):
        if isinstance(other, Card):
            return self.suit == other.suit and self.rank == other.rank
        return False

    def __hash__(self):
        return hash((self.suit, self.rank))

    def __str__(self):
        return f"{self.rank.value}{self.suit.value}"


class GameState(Enum):
    """Game states"""
    WAITING = "waiting"  # Fewer than 2 players
    READY = "ready"      # Two players joined, waiting to start
    ACTIVE = "active"
    FINISHED = "finished"


class CrazyEights:
    """Crazy Eights card game logic"""

    HAND_SIZE = 7
    DRAW_PENALTY = 3

    def __init__(self):
        self.deck: List[Card] = []
        self.discard_pile: List[Card] = []
        self.players: List[dict] = []
        self.current_player_idx = 0
        self.state = GameState.WAITING
        self.active_suit: Optional[Suit] = None  # For when an 8 is played
        self.winner_id: Optional[str] = None
        self.winner_name: Optional[str] = None
        self.draws_this_turn = 0
        self.passes_in_row = 0

    def create_deck(self) -> List[Card]:
        """Create a standard 52-card deck"""
        deck = []
        suits = list(Suit)
        ranks = list(Rank)

        for suit in suits:
            for rank in ranks:
                deck.append(Card(suit=suit, rank=rank))

        random.shuffle(deck)
        return deck

    def add_player(self, player_id: str, name: str) -> None:
        """Add a player to the game"""
        if self.state != GameState.WAITING:
            raise ValueError("Cannot add players after game has started")

        if len(self.players) >= 2:
            raise ValueError("Game is full (2 players max)")

        if any(p["id"] == player_id for p in self.players):
            raise ValueError(f"Player {player_id} already exists")

        self.players.append({
            "id": player_id,
            "name": name,
            "hand": [],
            "card_count": 0
        })

        # Transition to READY once both seats are filled
        if len(self.players) == 2:
            self.state = GameState.READY

    def start_game(self) -> None:
        """Initialize and start the game"""
        if len(self.players) != 2:
            raise ValueError("Need exactly 2 players to start")

        if self.state not in (GameState.WAITING, GameState.READY):
            raise ValueError("Game already started or finished")

        self.winner_id = None
        self.winner_name = None
        self.state = GameState.ACTIVE
        self.deck = self.create_deck()

        # Deal cards to each player
        for _ in range(self.HAND_SIZE):
            for player in self.players:
                if self.deck:
                    player["hand"].append(self.deck.pop())
                    player["card_count"] += 1

        # Flip first card to start discard pile
        if self.deck:
            first_card = self.deck.pop()
            # If it's an 8, put it back and draw again
            while first_card.rank == Rank.EIGHT and self.deck:
                self.deck.append(first_card)
                random.shuffle(self.deck)
                first_card = self.deck.pop()

            self.discard_pile.append(first_card)

        # Randomly select starting player
        self.current_player_idx = random.randint(0, len(self.players) - 1)

    def _can_play_on_active_suit(self, card: Card) -> bool:
        """Check if a card can be played when an 8 was previously played and a suit was declared"""
        return card.suit == self.active_suit or card.rank == Rank.EIGHT

    def can_play_card(self, card: Card) -> bool:
        """Check if a card can be played on the current discard pile"""
        if not self.discard_pile:
            return True

        top_card = self.discard_pile[-1]

        # 8s can always be played
        if card.rank == Rank.EIGHT:
            return True

        # If an 8 was played, check against active suit
        if self.active_suit:
            return self._can_play_on_active_suit(card)

        # Otherwise, match suit or rank
        return card.suit == top_card.suit or card.rank == top_card.rank

    def play_card(self, player_idx: int, card: Card, declared_suit: Optional[Suit] = None) -> dict:
        """
        Play a card from a player's hand

        Args:
            player_idx: Index of the player playing
            card: Card to play
            declared_suit: Suit to declare if playing an 8 (required if playing 8)

        Returns:
            Dictionary with game update info
        """
        if player_idx != self.current_player_idx:
            raise ValueError("Not this player's turn")

        player = self.players[player_idx]

        if card not in player["hand"]:
            raise ValueError("Card not in player's hand")

        if not self.can_play_card(card):
            raise ValueError("Invalid card play")

        # If playing an 8, declared_suit is required
        if card.rank == Rank.EIGHT and not declared_suit:
            raise ValueError("Must declare suit when playing an 8")

        # Remove card from hand and add to discard pile
        player["hand"].remove(card)
        player["card_count"] -= 1
        self.discard_pile.append(card)
        self.active_suit = None

        result = {
            "card_played": str(card),
            "player_id": player["id"],
            "player_name": player["name"],
            "hand_size": player["card_count"],
            "game_over": False,
            "winner": None,
            "winner_id": None,
            "winner_name": None
        }

        # Check if player won
        if player["card_count"] == 0:
            self.state = GameState.FINISHED
            self.winner_id = player["id"]
            self.winner_name = player["name"]
            result["game_over"] = True
            result["winner"] = player["name"]
            result["winner_id"] = player["id"]
            result["winner_name"] = player["name"]
        # Handle 8: player gets to declare suit
        if card.rank == Rank.EIGHT:
            if not isinstance(declared_suit, Suit):
                raise ValueError(f"Invalid declared suit: {declared_suit}")
            self.active_suit = declared_suit
            result["declared_suit"] = declared_suit.value

        # Move to next player
        self.current_player_idx = (self.current_player_idx + 1) % len(self.players)
        self.draws_this_turn = 0
        self.passes_in_row = 0

        return result

    def draw_card(self, player_idx: int) -> dict:
        """
        Player draws a card

        Args:
            player_idx: Index of the player drawing

        Returns:
            Dictionary with draw info
        """
        if player_idx != self.current_player_idx:
            raise ValueError("Not this player's turn")

        player = self.players[player_idx]

        turn_ended = False
        passed = False
        card = None
        can_play = False

        if not self.deck:
            passed = True
            turn_ended = True
            self.passes_in_row += 1
        else:
            card = self.deck.pop()
            player["hand"].append(card)
            player["card_count"] += 1
            self.draws_this_turn += 1
            can_play = self.can_play_card(card)

            if not can_play and self.draws_this_turn >= self.DRAW_PENALTY:
                turn_ended = True
                passed = True
                self.draws_this_turn = 0
                self.passes_in_row += 1
            else:
                self.passes_in_row = 0

        if turn_ended:
            self.current_player_idx = (self.current_player_idx + 1) % len(self.players)
            self.draws_this_turn = 0

        return {
            "player_id": player["id"],
            "drew_card": bool(card),
            "card": str(card) if card else None,
            "hand_size": player["card_count"],
            "card_playable": can_play,
            "draws_this_turn": self.draws_this_turn,
            "turn_ended": turn_ended,
            "passed": passed
        }

    def get_game_state(self) -> dict:
        """Get current game state for broadcasting"""
        top_card = self.discard_pile[-1] if self.discard_pile else None

        if self.state == GameState.FINISHED or not self.players:
            current_player_id = None
            current_player_name = None
        else:
            current_player_id = self.players[self.current_player_idx]["id"]
            current_player_name = self.players[self.current_player_idx]["name"]

        return {
            "state": self.state.value,
            "current_player_id": current_player_id,
            "current_player_name": current_player_name,
            "top_card": str(top_card) if top_card else None,
            "active_suit": self.active_suit.value if self.active_suit else None,
            "deck_size": len(self.deck),
            "discard_pile_size": len(self.discard_pile),
            "players": [
                {
                    "id": p["id"],
                    "name": p["name"],
                    "hand_size": p["card_count"],
                }
                for p in self.players
            ],
            "winner": self.winner_id,
            "winner_id": self.winner_id,
            "winner_name": self.winner_name
        }

    def get_player_hand(self, player_idx: int) -> List[str]:
        """Get the cards in a player's hand"""
        return [str(card) for card in self.players[player_idx]["hand"]]

    def get_player_state(self, player_idx: int) -> dict:
        """Get game state from a specific player's perspective"""
        state = self.get_game_state()
        state["your_hand"] = self.get_player_hand(player_idx)
        return state

    def to_dict(self) -> Dict[str, Any]:
        """Serialize game state to a JSON-friendly dict"""
        def encode_card(card: Card) -> str:
            return f"{card.rank.name}:{card.suit.name}"

        def encode_hand(hand: List[Card]) -> List[str]:
            return [encode_card(card) for card in hand]

        return {
            "deck": [encode_card(card) for card in self.deck],
            "discard_pile": [encode_card(card) for card in self.discard_pile],
            "players": [
                {
                    "id": player["id"],
                    "name": player["name"],
                    "hand": encode_hand(player["hand"]),
                    "card_count": player["card_count"],
                }
                for player in self.players
            ],
            "current_player_idx": self.current_player_idx,
            "state": self.state.value,
            "active_suit": self.active_suit.name if self.active_suit else None,
            "winner_id": self.winner_id,
            "winner_name": self.winner_name,
            "draws_this_turn": self.draws_this_turn,
            "passes_in_row": self.passes_in_row,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CrazyEights":
        """Rehydrate a game from serialized dict"""
        def decode_card(token: str) -> Card:
            rank_name, suit_name = token.split(":")
            return Card(rank=Rank[rank_name], suit=Suit[suit_name])

        game = cls()
        game.deck = [decode_card(token) for token in data.get("deck", [])]
        game.discard_pile = [decode_card(token) for token in data.get("discard_pile", [])]
        game.players = []
        for player in data.get("players", []):
            hand = [decode_card(token) for token in player.get("hand", [])]
            game.players.append({
                "id": player["id"],
                "name": player["name"],
                "hand": hand,
                "card_count": player.get("card_count", len(hand))
            })
        game.current_player_idx = data.get("current_player_idx", 0)
        game.state = GameState(data.get("state", GameState.WAITING.value))
        active_suit = data.get("active_suit")
        game.active_suit = Suit[active_suit] if active_suit else None
        game.winner_id = data.get("winner_id")
        game.winner_name = data.get("winner_name")
        game.draws_this_turn = data.get("draws_this_turn", 0)
        game.passes_in_row = data.get("passes_in_row", 0)
        return game
