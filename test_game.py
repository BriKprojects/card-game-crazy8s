"""
Unit tests for Crazy Eights game logic
"""

import pytest
from game import CrazyEights, Card, GameState, Suit, Rank


class TestCard:
    """Tests for Card class"""

    def test_card_creation(self):
        """Test creating a card"""
        card = Card(suit=Suit.HEARTS, rank=Rank.EIGHT)
        assert card.suit == Suit.HEARTS
        assert card.rank == Rank.EIGHT

    def test_card_equality(self):
        """Test card equality comparison"""
        card1 = Card(suit=Suit.HEARTS, rank=Rank.EIGHT)
        card2 = Card(suit=Suit.HEARTS, rank=Rank.EIGHT)
        card3 = Card(suit=Suit.DIAMONDS, rank=Rank.EIGHT)

        assert card1 == card2
        assert card1 != card3

    def test_card_hash(self):
        """Test card hashing for set/dict usage"""
        card1 = Card(suit=Suit.HEARTS, rank=Rank.EIGHT)
        card2 = Card(suit=Suit.HEARTS, rank=Rank.EIGHT)

        card_set = {card1, card2}
        assert len(card_set) == 1  # Equal cards hash to same value

    def test_card_string_representation(self):
        """Test card string representation"""
        card = Card(suit=Suit.HEARTS, rank=Rank.EIGHT)
        assert str(card) == "8♥"


class TestGameInitialization:
    """Tests for game initialization"""

    def test_game_creation(self):
        """Test creating a new game"""
        game = CrazyEights()
        assert game.state == GameState.WAITING
        assert len(game.players) == 0
        assert game.deck == []
        assert game.discard_pile == []

    def test_add_player(self):
        """Test adding players to a game"""
        game = CrazyEights()
        game.add_player("player1", "Alice")
        game.add_player("player2", "Bob")

        assert len(game.players) == 2
        assert game.players[0]["name"] == "Alice"
        assert game.players[1]["name"] == "Bob"
        assert game.state == GameState.READY

    def test_game_state_ready_with_two_players(self):
        """Game state should move to READY when both seats filled"""
        game = CrazyEights()
        game.add_player("player1", "Alice")
        assert game.state == GameState.WAITING

        game.add_player("player2", "Bob")
        assert game.state == GameState.READY

    def test_add_duplicate_player_fails(self):
        """Test that adding duplicate player fails"""
        game = CrazyEights()
        game.add_player("player1", "Alice")

        with pytest.raises(ValueError, match="already exists"):
            game.add_player("player1", "Bob")

    def test_cannot_add_player_after_start(self):
        """Test that cannot add players after game starts"""
        game = CrazyEights()
        game.add_player("player1", "Alice")
        game.add_player("player2", "Bob")
        game.start_game()

        with pytest.raises(ValueError, match="Cannot add players"):
            game.add_player("player3", "Charlie")

    def test_need_min_players_to_start(self):
        """Test that need at least 2 players to start"""
        game = CrazyEights()
        game.add_player("player1", "Alice")

        with pytest.raises(ValueError, match="Need exactly 2 players"):
            game.start_game()


class TestGameStart:
    """Tests for game start"""

    def test_game_start(self):
        """Test starting a game"""
        game = CrazyEights()
        game.add_player("player1", "Alice")
        game.add_player("player2", "Bob")
        game.start_game()

        assert game.state == GameState.ACTIVE
        assert len(game.deck) > 0  # Cards dealt
        assert len(game.discard_pile) == 1  # First card flipped
        assert all(p["card_count"] == 7 for p in game.players)  # Each got 7 cards

    def test_deck_created_with_52_cards(self):
        """Test that deck has 52 cards"""
        game = CrazyEights()
        deck = game.create_deck()
        assert len(deck) == 52

    def test_first_card_not_eight(self):
        """Test that first card dealt is not an 8"""
        # This may need multiple tries but should happen eventually
        game = CrazyEights()
        game.add_player("player1", "Alice")
        game.add_player("player2", "Bob")
        game.start_game()

        top_card = game.discard_pile[-1]
        assert top_card.rank != "8"


class TestGameRules:
    """Tests for game rules and card play"""

    def setup_method(self):
        """Setup for each test"""
        self.game = CrazyEights()
        self.game.add_player("player1", "Alice")
        self.game.add_player("player2", "Bob")
        self.game.start_game()
        self.game.current_player_idx = 0

    def _remove_card_from_hand(self, player: dict, suit: Suit, rank: Rank) -> None:
        """Ensure no duplicate of a specific card stays in the player's hand."""
        for idx, existing in enumerate(player["hand"]):
            if existing.suit == suit and existing.rank == rank:
                player["hand"].pop(idx)
                player["card_count"] -= 1
                break

    def test_can_play_matching_suit(self):
        """Test that can play card with matching suit"""
        top_card = self.game.discard_pile[-1]
        matching_card = Card(suit=top_card.suit, rank=Rank.FIVE)

        result = self.game.can_play_card(matching_card)
        assert result is True

    def test_can_play_matching_rank(self):
        """Test that can play card with matching rank"""
        top_card = self.game.discard_pile[-1]
        matching_card = Card(suit=Suit.DIAMONDS, rank=top_card.rank)

        result = self.game.can_play_card(matching_card)
        assert result is True

    def test_cannot_play_non_matching_card(self):
        """Test that cannot play non-matching card"""
        top_card = self.game.discard_pile[-1]
        non_matching = Card(suit=Suit.SPADES, rank=Rank.TWO)

        # Ensure it doesn't match
        if non_matching.suit == top_card.suit or non_matching.rank == top_card.rank:
            pytest.skip("Random card happened to match")

        result = self.game.can_play_card(non_matching)
        assert result is False

    def test_eight_always_playable(self):
        """Test that 8s can always be played"""
        eight = Card(suit=Suit.HEARTS, rank=Rank.EIGHT)
        result = self.game.can_play_card(eight)
        assert result is True

    def test_must_declare_suit_for_eight(self):
        """Test that must declare suit when playing 8"""
        player = self.game.players[0]
        eight = Card(suit=Suit.HEARTS, rank=Rank.EIGHT)
        self._remove_card_from_hand(player, Suit.HEARTS, Rank.EIGHT)
        player["hand"].append(eight)
        player["card_count"] += 1

        with pytest.raises(ValueError, match="declare suit"):
            self.game.play_card(0, eight, declared_suit=None)

    def test_play_card_valid(self):
        """Test playing a valid card"""
        player = self.game.players[0]
        top_card = self.game.discard_pile[-1]
        matching_card = Card(suit=top_card.suit, rank=Rank.FIVE)
        self._remove_card_from_hand(player, matching_card.suit, matching_card.rank)
        player["hand"].append(matching_card)
        player["card_count"] += 1

        result = self.game.play_card(0, matching_card)

        assert result["card_played"] == str(matching_card)
        assert matching_card not in player["hand"]
        assert matching_card in self.game.discard_pile

    def test_play_card_turns(self):
        """Test that turns alternate between players"""
        assert self.game.current_player_idx == 0

        player0 = self.game.players[0]
        top_card = self.game.discard_pile[-1]
        matching_card = Card(suit=top_card.suit, rank=Rank.FIVE)
        self._remove_card_from_hand(player0, matching_card.suit, matching_card.rank)
        player0["hand"].append(matching_card)
        player0["card_count"] += 1

        self.game.play_card(0, matching_card)
        assert self.game.current_player_idx == 1

    def test_wrong_player_cannot_play(self):
        """Test that wrong player cannot play"""
        player0 = self.game.players[0]
        top_card = self.game.discard_pile[-1]
        matching_card = Card(suit=top_card.suit, rank=Rank.FIVE)
        self._remove_card_from_hand(player0, matching_card.suit, matching_card.rank)
        player0["hand"].append(matching_card)
        player0["card_count"] += 1

        with pytest.raises(ValueError, match="Not this player"):
            self.game.play_card(1, matching_card)

    def test_card_not_in_hand_fails(self):
        """Test that playing card not in hand fails"""
        card = Card(suit=Suit.HEARTS, rank=Rank.FIVE)
        self._remove_card_from_hand(self.game.players[0], card.suit, card.rank)

        with pytest.raises(ValueError, match="not in player"):
            self.game.play_card(0, card)


class TestDrawCard:
    """Tests for drawing cards"""

    def setup_method(self):
        """Setup for each test"""
        self.game = CrazyEights()
        self.game.add_player("player1", "Alice")
        self.game.add_player("player2", "Bob")
        self.game.start_game()
        self.game.current_player_idx = 0

    def test_draw_card(self):
        """Test drawing a card"""
        player = self.game.players[0]
        initial_count = player["card_count"]
        initial_deck = len(self.game.deck)

        result = self.game.draw_card(0)

        assert result["drew_card"] is True
        assert player["card_count"] == initial_count + 1
        assert len(self.game.deck) == initial_deck - 1
        assert result["turn_ended"] in (True, False)
        assert "card_playable" in result

    def test_draw_three_times_advances_turn(self):
        """Drawing three unplayable cards should pass the turn"""
        game = CrazyEights()
        game.players = [
            {"id": "player1", "name": "Alice", "hand": [], "card_count": 0},
            {"id": "player2", "name": "Bob", "hand": [], "card_count": 0},
        ]
        game.state = GameState.ACTIVE
        game.current_player_idx = 0
        game.discard_pile = [Card(suit=Suit.SPADES, rank=Rank.TWO)]
        game.deck = [
            Card(suit=Suit.HEARTS, rank=Rank.THREE),
            Card(suit=Suit.DIAMONDS, rank=Rank.FOUR),
            Card(suit=Suit.CLUBS, rank=Rank.FIVE),
        ]

        first = game.draw_card(0)
        assert first["turn_ended"] is False
        assert game.current_player_idx == 0

        second = game.draw_card(0)
        assert second["turn_ended"] is False
        assert game.current_player_idx == 0

        third = game.draw_card(0)
        assert third["turn_ended"] is True
        assert third["passed"] is True
        assert game.current_player_idx == 1


class TestGameWin:
    """Tests for game winning"""

    def test_player_wins_on_empty_hand(self):
        """Test that player wins when hand is empty"""
        game = CrazyEights()
        game.add_player("player1", "Alice")
        game.add_player("player2", "Bob")
        game.start_game()

        # Give player 1 only one card
        player0 = game.players[0]
        player0["hand"] = [Card(suit=Suit.HEARTS, rank=Rank.FIVE)]
        player0["card_count"] = 1

        # Make the discard pile compatible
        game.discard_pile = [Card(suit=Suit.HEARTS, rank=Rank.EIGHT)]
        game.current_player_idx = 0

        # Play the last card
        result = game.play_card(0, player0["hand"][0])

        assert result["game_over"] is True
        assert result["winner"] == "Alice"
        assert game.state == GameState.FINISHED


class TestGameState:
    """Tests for getting game state"""

    def test_get_game_state(self):
        """Test getting game state"""
        game = CrazyEights()
        game.add_player("player1", "Alice")
        game.add_player("player2", "Bob")
        game.start_game()

        state = game.get_game_state()

        assert state["state"] == "active"
        assert state["top_card"] is not None
        assert len(state["players"]) == 2
        assert state["deck_size"] > 0

    def test_get_player_state_includes_hand(self):
        """Test that player state includes their hand"""
        game = CrazyEights()
        game.add_player("player1", "Alice")
        game.add_player("player2", "Bob")
        game.start_game()

        player_state = game.get_player_state(0)

        assert "your_hand" in player_state
        assert len(player_state["your_hand"]) == 7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
