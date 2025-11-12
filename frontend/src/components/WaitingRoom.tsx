import { useState, useEffect, useRef } from 'react'
import { API_BASE_URL, WS_BASE_URL } from '../config'
import '../styles/WaitingRoom.css'

interface WaitingRoomProps {
  gameId: string
  playerId: string
  onStartGame: () => void
}

interface GameState {
  players: Array<{ id: string; name: string }>
  current_player_id: string
}

export default function WaitingRoom({ gameId, playerId, onStartGame }: WaitingRoomProps) {
  const [players, setPlayers] = useState<Array<{ id: string; name: string }>>([])
  const [loading, setLoading] = useState(true)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    const fetchGameState = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/games/${gameId}/state?player_id=${playerId}`)
        const data: GameState = await response.json()
        setPlayers(data.players)
        setLoading(false)
      } catch (error) {
        console.error('Failed to fetch game state:', error)
      }
    }

    fetchGameState()

    // Connect to WebSocket for real-time updates
    const ws = new WebSocket(`${WS_BASE_URL}/ws/${gameId}/${playerId}`)

    ws.onopen = () => {
      console.log('WaitingRoom WebSocket connected')
    }

    ws.onmessage = (event) => {
      try {
        const update = JSON.parse(event.data)
        const data = update.data || {}
        const boardState = data.player_state || data.game_state || data
        if (boardState && boardState.players) {
          setPlayers(boardState.players)
        }
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error)
      }
    }

    ws.onerror = (error) => {
      console.error('WaitingRoom WebSocket error:', error)
    }

    ws.onclose = () => {
      console.log('WaitingRoom WebSocket closed')
    }

    wsRef.current = ws

    // Still keep polling as backup
    const interval = setInterval(fetchGameState, 2000)

    return () => {
      clearInterval(interval)
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [gameId, playerId])

  if (loading) {
    return <div className="waiting-room">Loading...</div>
  }

  const isReady = players.length === 2

  return (
    <div className="waiting-room">
      <h1>🃏 Waiting for Players</h1>
      <p>Game ID: <code>{gameId}</code></p>
      
      <div className="players-list">
        <h2>Players ({players.length}/2)</h2>
        {players.map((player) => (
          <div key={player.id} className="player-item">
            ✓ {player.name}
          </div>
        ))}
        {players.length < 2 && (
          <div className="player-waiting">
            Waiting for another player...
          </div>
        )}
      </div>

      {isReady && (
        <button onClick={onStartGame} className="btn btn-primary">
          Start Game
        </button>
      )}
    </div>
  )
}
