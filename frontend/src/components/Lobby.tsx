import { useState } from 'react'
import { API_BASE_URL } from '../config'
import '../styles/Lobby.css'

interface LobbyProps {
  onJoinGame: (gameId: string, playerName: string) => void
}

export default function Lobby({ onJoinGame }: LobbyProps) {
  const [gameId, setGameId] = useState('')
  const [playerName, setPlayerName] = useState('')
  const [creatorName, setCreatorName] = useState('')
  const [createdGameId, setCreatedGameId] = useState('')

  const handleCreateGame = async () => {
    if (!creatorName) {
      alert('Please enter your name before creating a game.')
      return
    }
    try {
      const response = await fetch(`${API_BASE_URL}/games/create`, {
        method: 'POST'
      })
      const data = await response.json()
      setCreatedGameId(data.game_id)
      onJoinGame(data.game_id, creatorName)
    } catch (error) {
      console.error('Failed to create game:', error)
    }
  }

  const handleJoin = () => {
    if (gameId && playerName) {
      onJoinGame(gameId, playerName)
    }
  }

  return (
    <div className="lobby">
      <h1>🃏 Crazy Eights</h1>
      
      <div className="lobby-section">
        <h2>Create New Game</h2>
        <input
          type="text"
          placeholder="Enter your name"
          value={creatorName}
          onChange={(e) => setCreatorName(e.target.value)}
          className="input"
        />
        <button onClick={handleCreateGame} className="btn btn-primary">
          Create Game
        </button>
        {createdGameId && (
          <div className="game-id">
            <p>Game ID: <code>{createdGameId}</code></p>
            <input
              type="text"
              value={createdGameId}
              readOnly
              onClick={(e) => e.currentTarget.select()}
              placeholder="Copy game ID"
            />
          </div>
        )}
      </div>

      <div className="lobby-divider">OR</div>

      <div className="lobby-section">
        <h2>Join Existing Game</h2>
        <input
          type="text"
          placeholder="Enter game ID"
          value={gameId}
          onChange={(e) => setGameId(e.target.value)}
          className="input"
        />
      </div>

      <div className="lobby-section">
        <label>Your Name</label>
        <input
          type="text"
          placeholder="Enter your name"
          value={playerName}
          onChange={(e) => setPlayerName(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleJoin()}
          className="input"
        />
      </div>

      <button
        onClick={handleJoin}
        disabled={!gameId || !playerName}
        className="btn btn-primary"
      >
        Join Game
      </button>
    </div>
  )
}
