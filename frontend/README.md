# Frontend - Crazy Eights React App

TypeScript + React + Vite frontend for the Crazy Eights card game.

## Setup

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173` when running.

## Build

```bash
npm run build
```

## Features

- 🎮 Create and join games
- 👥 Real-time 2-player gameplay
- 🎨 Interactive card UI
- 💬 WebSocket for live updates
- 📱 Responsive design

## How It Works

1. **Lobby** - Enter your name or create a new game
2. **Waiting Room** - Wait for another player to join
3. **Game Board** - Play cards, declare suits on 8s, draw when needed
4. **Game Over** - First to empty their hand wins!

## Components

- `Lobby.tsx` - Game creation and joining
- `WaitingRoom.tsx` - Player roster and start game
- `GameBoard.tsx` - Main game UI with cards, piles, and actions
