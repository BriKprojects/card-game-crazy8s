# Crazy Eights 

A tiny end-to-end card table: React handles the player experience, FastAPI keeps the rules straight, SQLite stores long-lived games, and Docker ties everything together. Two players can sit in the same lobby, join with a name, and play Crazy Eights with real-time updates delivered over WebSockets.

---

## What’s Included

- **Frontend (Vite + React + TS)**  
  - Lobby with simple sign-in by player name (no password/OAuth yet).  
  - Waiting room that shows who has joined.  
  - Game board with live opponent info, discard pile, deck, and full hand management.  
  - WebSocket-driven updates so you always see the latest state without polling.

- **Backend (FastAPI)**  
  - Game engine (`game.py`) 
  - REST endpoints for creating/joining/starting games plus play + draw moves.  
  - WebSocket hub that streams each player’s private view (hand + turn info).  
  - Pytest

- **Database (SQLite via SQLAlchemy)**  
  - `games`, `game_sessions`, and `game_moves` tables for persisting lobbies, players, and history.  
  - Migrations aren’t wired up yet; recreating the DB is as simple as running `init_db()` (details below).

- **Infrastructure**  
  - Docker Compose  

---

## Local Setup

### 1. Backend

```bash
python -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Initialize the SQLite database (creates crazy_eights.db if missing)
python -c "from database import init_db; init_db()"

# Run the API
uvicorn main:app --reload
```

API docs live at <http://localhost:8000/docs>.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173> in two browser windows; give each player a name and the same game ID.

### 2b. One-command stack (Docker Compose)

```bash
docker compose up --build
```

This starts the FastAPI backend (port 8000) and the Vite preview server (port 5173) together, which is the easiest way to run the app end-to-end right now.

### 3. SQLite Tips

```bash
sqlite3 crazy_eights.db
sqlite> .tables
sqlite> .schema games
sqlite> SELECT id, state, winner_name FROM games;
sqlite> .quit
```

## Gameplay Walkthrough

1. **Create a lobby:** `POST /games/create` returns a `game_id`. The frontend does this when you click “Create Game”.  
2. **Join with a name:** Each browser tab joins the same `game_id` via `POST /games/{id}/join`.  
3. **Start the match:** Once two seats are filled the UI exposes “Start Game”. Repeated clicks are idempotent—late clicks simply return the current state.  
4. **Take turns:**  
   - Hand + turn info arrives over the `/ws/{game_id}/{player_id}` socket using personalized payloads.  
   - Play a card with `POST /games/{id}/play?player_id=...` and payload `{ card: "Q♣", declared_suit: null }`.  
   - Draw from the deck with `POST /games/{id}/draw?player_id=...`.  
5. **Win condition:** First player to empty their hand triggers `GameState.FINISHED`, updates `winner_id`/`winner_name`, and the UI announces the result.

---

## Testing

```bash
pytest test_game.py -v
```

---

## API Quick Reference

| Method | Path | Notes |
| ------ | ---- | ----- |
| `POST` | `/games/create` | Returns `game_id`. |
| `POST` | `/games/{game_id}/join` | Body: `{ "name": "Alice" }` → returns `player_id`. |
| `POST` | `/games/{game_id}/start` | Safe to call multiple times; returns current state once active. |
| `GET` | `/games/{game_id}/state?player_id=...` | Player-scoped view (includes `your_hand`). |
| `POST` | `/games/{game_id}/play?player_id=...` | Body: `{ "card": "8♥", "declared_suit": "♠" }`. |
| `POST` | `/games/{game_id}/draw?player_id=...` | Draws one card and advances the turn. |
| `WS` | `/ws/{game_id}/{player_id}` | Pushes both the public board state and the player’s private state. |

---

## Known Gaps & Next Steps

1. **More seats:** The in-memory engine and UI currently cap at 2 players. To support up to 4 you’d extend `CrazyEights.players`,`len(self.players) >= 2` checks, and update layouts to show extra opponents.  
2. **Authentication:** Right now “sign in” is just typing a name. Adding password or OAuth-backed sessions would be preferable for a real app.
3. ***Infrastructure:** Scalable and production-ready infra is missing
4. ****Visuals:** Self-explanatory, a lot can be improved! Animations, log out-options, tracking of matches etc.

---
