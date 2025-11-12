import { useState } from 'react'
import './App.css'
import GameBoard from './components/GameBoard'
import Lobby from './components/Lobby'
import WaitingRoom from './components/WaitingRoom'
import { API_BASE_URL } from './config'

export type GamePhase = 'lobby' | 'waiting' | 'playing' | 'finished'

interface GameState {
  gameId: string
  playerId: string
  playerName: string
  phase: GamePhase
}

function App() {
  const [gameState, setGameState] = useState<GameState | null>(null)

  const handleJoinGame = async (gameId: string, playerName: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/games/${gameId}/join`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: playerName })
      })
      const data = await response.json()
      setGameState({
        gameId,
        playerId: data.player_id,
        playerName,
        phase: 'waiting'
      })
    } catch (error) {
      console.error('Failed to join game:', error)
    }
  }

  const handleStartGame = async () => {
    if (!gameState) return
    try {
      // Refresh server state to avoid race where a start is attempted
      // before the second player is fully registered.
      const stateResp = await fetch(`${API_BASE_URL}/games/${gameState.gameId}/state?player_id=${gameState.playerId}`)
      if (!stateResp.ok) {
        const err = await stateResp.json()
        alert(`Cannot start: ${err.detail || 'failed to read game state'}`)
        return
      }
      const stateData = await stateResp.json()
      if (!stateData.players || stateData.players.length < 2) {
        alert('Need 2 players to start the game. Waiting for the other player.')
        return
      }

      const response = await fetch(`${API_BASE_URL}/games/${gameState.gameId}/start`, {
        method: 'POST'
      })

      if (!response.ok) {
        const error = await response.json()
        console.error('Start game error:', error)
        alert(`Cannot start game: ${error.detail || 'Unknown error'}`)
        return
      }

      setGameState({ ...gameState, phase: 'playing' })
    } catch (error) {
      console.error('Failed to start game:', error)
      alert('Failed to start game')
    }
  }

  if (!gameState) {
    return <Lobby onJoinGame={handleJoinGame} />
  }

  if (gameState.phase === 'waiting') {
    return <WaitingRoom gameId={gameState.gameId} playerId={gameState.playerId} onStartGame={handleStartGame} />
  }

  if (gameState.phase === 'playing') {
    return <GameBoard gameId={gameState.gameId} playerId={gameState.playerId} playerName={gameState.playerName} />
  }

  return <div>Game Over</div>
}

export default App
