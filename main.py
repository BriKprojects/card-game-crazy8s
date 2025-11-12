"""
FastAPI server for Crazy Eights multiplayer card game
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict
from contextlib import contextmanager
from datetime import datetime
import json
import uuid

from game import CrazyEights, Card, GameState, Suit, Rank
from database import (
    SessionLocal,
    Game as DBGame,
    GameSession as DBGameSession,
    GameMove as DBGameMove,
    GameStateEnum,
)

class PlayerJoinRequest(BaseModel):
    name: str


class PlayCardRequest(BaseModel):
    card: str  # Format: "Rank Suit" e.g., "8♥"
    declared_suit: str | None = None


class DrawCardRequest(BaseModel):
    pass


app = FastAPI(title="Crazy Eights", description="Two Player Crazy Eights card game")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:8000", "http://localhost",": http://172.18.0.3:5173", ": http://172.18.0.3:8000", "*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "DELETE", "PUT"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)

# Game State Mgmt

games: Dict[str, CrazyEights] = {}
game_players: Dict[str, Dict[str, int]] = {}  # game_id -> {player_id: player_idx}
active_connections: Dict[str, Dict[str, WebSocket]] = {}  # game_id -> {player_id: websocket}


@contextmanager
def db_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def broadcast_to_game(game_id: str, event_type: str, event_payload: dict | None = None):
    """Broadcast a unified message to all players in a game."""
    connections = active_connections.get(game_id)
    if not connections:
        return

    game = games.get(game_id)
    if not game:
        return

    game_state = game.get_game_state()
    disconnected = set()

    for player_id, connection in list(connections.items()):
        try:
            payload = {
                "type": event_type,
                "data": {
                    "game_state": game_state,
                    "event": event_payload or {}
                }
            }
            player_mapping = game_players.get(game_id, {})
            player_idx = player_mapping.get(player_id)
            if player_idx is not None:
                payload["data"]["player_state"] = game.get_player_state(player_idx)
            await connection.send_json(payload)
        except Exception:
            disconnected.add(player_id)

    for player_id in disconnected:
        connection = connections.pop(player_id, None)
        if connection:
            try:
                await connection.close()
            except Exception:
                pass


def _parse_suit(value: str) -> Suit:
    """Convert user-provided suit string or symbol to Suit enum"""
    if not value:
        raise ValueError("Suit cannot be empty")

    normalized = value.strip().upper()
    for suit in Suit:
        if value == suit.value or normalized == suit.name:
            return suit

    raise ValueError(f"Invalid suit: {value}")


def _parse_rank(value: str) -> Rank:
    """Convert user-provided rank string to Rank enum"""
    if not value:
        raise ValueError("Rank cannot be empty")

    normalized = value.strip().upper()
    for rank in Rank:
        if value == rank.value or normalized == rank.name:
            return rank

    raise ValueError(f"Invalid rank: {value}")


def parse_card(card_str: str) -> Card:
    """Parse card string like '8♥' to Card data"""
    if len(card_str) < 2:
        raise ValueError(f"Invalid card format: {card_str}")

    suit_value = card_str[-1]
    rank_value = card_str[:-1]

    suit = _parse_suit(suit_value)
    rank = _parse_rank(rank_value)

    return Card(suit=suit, rank=rank)


def refresh_player_indexes(game_id: str) -> None:
    """Rebuild the player-id -> index map for a game."""
    game = games.get(game_id)
    if not game:
        return
    game_players[game_id] = {
        player["id"]: idx for idx, player in enumerate(game.players)
    }


def persist_game_state(game_id: str, session=None, **extra_updates) -> None:
    """Serialize and store the current game state in the database."""
    if game_id not in games:
        return

    serialized = json.dumps(games[game_id].to_dict())

    def _write(sess):
        db_game = sess.get(DBGame, game_id)
        if not db_game:
            db_game = DBGame(id=game_id)
            sess.add(db_game)
        db_game.state_data = serialized  
        db_game.state = GameStateEnum(games[game_id].state.value) 
        db_game.winner_name = games[game_id].winner_name 
        for key, value in extra_updates.items():
            setattr(db_game, key, value)

    if session:
        _write(session)
    else:
        with db_session() as sess:
            _write(sess)


def load_games_from_db() -> None:
    """Load previously stored games into memory (rehydration)."""
    with db_session() as session:
        db_games = session.query(DBGame).all()
        for db_game in db_games:
            try:
                if db_game.state_data: 
                    data = json.loads(db_game.state_data) 
                    game = CrazyEights.from_dict(data)
                else:
                    game = CrazyEights()
            except Exception:
                game = CrazyEights()
            games[db_game.id] = game 
            refresh_player_indexes(db_game.id)
            active_connections.setdefault(db_game.id, {}) 


load_games_from_db()

# REST Endpoints

@app.post("/games/create")
async def create_game() -> dict:
    """Create a new game"""
    game_id = str(uuid.uuid4())
    games[game_id] = CrazyEights()
    refresh_player_indexes(game_id)
    active_connections[game_id] = {}

    persist_game_state(game_id)

    return {
        "game_id": game_id,
        "message": "Game created successfully"
    }


@app.post("/games/{game_id}/join")
async def join_game(game_id: str, request: PlayerJoinRequest) -> dict:
    """Join an existing game"""
    if game_id not in games:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found"
        )

    game = games[game_id]

    if len(game.players) >= 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game is full (2 players max)"
        )

    if game.state not in (GameState.WAITING, GameState.READY):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game has already started"
        )

    with db_session() as session:
        existing = session.query(DBGameSession).filter_by(
            game_id=game_id,
            player_name=request.name
        ).first()
        if existing:
            refresh_player_indexes(game_id)
            if existing.id not in game_players[game_id]:
                refresh_player_indexes(game_id)
            return {
                "player_id": existing.id,
                "game_id": game_id,
                "message": f"Player {request.name} already joined"
            }

    player_id = str(uuid.uuid4())
    game.add_player(player_id, request.name)
    refresh_player_indexes(game_id)
    persist_game_state(game_id)

    with db_session() as session:
        session.add(DBGameSession(
            id=player_id,
            game_id=game_id,
            player_name=request.name,
            player_index=len(game.players) - 1
        ))

    await broadcast_to_game(game_id, "player_joined")

    return {
        "player_id": player_id,
        "game_id": game_id,
        "message": f"Player {request.name} joined the game"
    }


@app.post("/games/{game_id}/start")
async def start_game(game_id: str) -> dict:
    """Start the game"""
    if game_id not in games:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found"
        )

    game = games[game_id]

    if game.state == GameState.ACTIVE:
        return {
            "message": "Game already started",
            "data": game.get_game_state()
        }

    if game.state == GameState.FINISHED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game already finished"
        )

    try:
        game.start_game()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    with db_session() as session:
        persist_game_state(game_id, session=session, started_at=datetime.utcnow())

    await broadcast_to_game(game_id, "game_started")

    return {"message": "Game started"}


@app.get("/games/{game_id}/state")
async def get_game_state(game_id: str, player_id: str) -> dict:
    """Get current game state for a player"""
    if game_id not in games:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found"
        )

    if game_id not in game_players:
        refresh_player_indexes(game_id)
    if game_id not in game_players:
        refresh_player_indexes(game_id)
    if game_id not in game_players:
        refresh_player_indexes(game_id)
    if player_id not in game_players[game_id]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Player not in this game"
        )

    game = games[game_id]
    player_idx = game_players[game_id][player_id]

    return game.get_player_state(player_idx)


@app.post("/games/{game_id}/play")
async def play_card(game_id: str, player_id: str, request: PlayCardRequest) -> dict:
    """Play a card"""
    if game_id not in games:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found"
        )

    if player_id not in game_players[game_id]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Player not in this game"
        )

    game = games[game_id]
    player_idx = game_players[game_id][player_id]

    try:
        card = parse_card(request.card)
        declared_suit = _parse_suit(request.declared_suit) if request.declared_suit else None
        result = game.play_card(player_idx, card, declared_suit)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    player_name = game.players[player_idx]["name"]
    with db_session() as session:
        session.add(DBGameMove(
            id=str(uuid.uuid4()),
            game_id=game_id,
            player_name=player_name,
            move_type="play_card",
            card_played=result["card_played"],
            declared_suit=result.get("declared_suit")
        ))
        extra = {}
        if game.state == GameState.FINISHED:
            extra["finished_at"] = datetime.utcnow()
        persist_game_state(game_id, session=session, **extra)

    await broadcast_to_game(game_id, "card_played", {"result": result})

    return result


@app.post("/games/{game_id}/draw")
async def draw_card(game_id: str, player_id: str) -> dict:
    """Draw a card"""
    if game_id not in games:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found"
        )

    if player_id not in game_players[game_id]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Player not in this game"
        )

    game = games[game_id]
    player_idx = game_players[game_id][player_id]

    try:
        result = game.draw_card(player_idx)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    player_name = game.players[player_idx]["name"]
    with db_session() as session:
        session.add(DBGameMove(
            id=str(uuid.uuid4()),
            game_id=game_id,
            player_name=player_name,
            move_type="draw_card",
            card_played=result.get("card"),
            declared_suit=None
        ))
        persist_game_state(game_id, session=session)

    await broadcast_to_game(game_id, "card_drawn", {"result": result})

    return result


# ============= WebSocket =============


@app.websocket("/ws/{game_id}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str, player_id: str):
    """WebSocket connection for real-time game updates"""
    try:
        if game_id not in games:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Game not found")
            return

        if game_id not in game_players or player_id not in game_players[game_id]:
            refresh_player_indexes(game_id)
        if player_id not in game_players.get(game_id, {}):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Player not in game")
            return

        if game_id not in active_connections:
            active_connections[game_id] = {}

        await websocket.accept()
        active_connections[game_id][player_id] = websocket

        # Send initial game state
        game = games[game_id]
        player_idx = game_players[game_id][player_id]
        await websocket.send_json({
            "type": "connected",
            "data": {
                "game_state": game.get_game_state(),
                "player_state": game.get_player_state(player_idx)
            }
        })

        # Keep connection open
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        if game_id in active_connections:
            active_connections[game_id].pop(player_id, None)
    except Exception as e:
        print(f"WebSocket error for {game_id}/{player_id}: {e}")
        if game_id in active_connections:
            active_connections[game_id].pop(player_id, None)
        try:
            await websocket.close(code=status.WS_1011_SERVER_ERROR, reason=str(e))
        except:
            pass
 

@app.options("/{full_path:path}")
async def preflight(full_path: str):
    """Handle CORS preflight requests"""
    return {}


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
