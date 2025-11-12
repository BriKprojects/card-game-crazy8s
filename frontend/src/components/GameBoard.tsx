import { useState, useEffect, useRef } from 'react'
import { API_BASE_URL, WS_BASE_URL } from '../config'
import '../styles/GameBoard.css'

interface GameBoardProps {
  gameId: string
  playerId: string
  playerName: string
}

interface Card {
  suit: string
  rank: string
}

interface GameUpdate {
  type: string
  data: any
}

// Parse card string like "8♥" to { rank: "8", suit: "♥" }
function parseCard(cardStr: string): Card {
  if (!cardStr || cardStr.length < 2) {
    return { rank: '', suit: '' }
  }
  
  const suits = ['♥', '♦', '♣', '♠']
  const suit = suits.find(s => cardStr.includes(s)) || ''
  const rank = cardStr.replace(suit, '')
  
  return { rank, suit }
}

function parseHand(cards: string[]): Card[] {
  return cards.map(parseCard)
}

function cardsEqual(a: Card | null, b: Card | null): boolean {
  if (!a || !b) return false
  return a.rank === b.rank && a.suit === b.suit
}

export default function GameBoard({ gameId, playerId }: GameBoardProps) {
  const [gameState, setGameState] = useState<any>(null)
  const [hand, setHand] = useState<Card[]>([])
  const [selectedCard, setSelectedCard] = useState<Card | null>(null)
  const [declaredSuit, setDeclaredSuit] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    // Fetch initial game state
    const fetchGameState = async () => {
      try {
        const response = await fetch(
          `${API_BASE_URL}/games/${gameId}/state?player_id=${playerId}`
        )
        const data = await response.json()
        setGameState(data)
        setHand(parseHand(data.your_hand || []))
        setLoading(false)
      } catch (error) {
        console.error('Failed to fetch game state:', error)
      }
    }

    fetchGameState()

    // Connect to WebSocket
    const ws = new WebSocket(`${WS_BASE_URL}/ws/${gameId}/${playerId}`)

    ws.onopen = () => {
      console.log('WebSocket connected')
    }

    ws.onmessage = (event) => {
      const update: GameUpdate = JSON.parse(event.data)
      const data = update.data || {}
      const playerState = data.player_state
      const boardState = playerState || data.game_state || data

      if (boardState) {
        setGameState(boardState)
        const handSource = playerState?.your_hand || boardState.your_hand || []
        setHand(parseHand(handSource))
        setLoading(false)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    ws.onclose = () => {
      console.log('WebSocket closed')
    }

    wsRef.current = ws

    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close()
      }
    }
  }, [gameId, playerId])

  const canPlayCard = (card: Card): boolean => {
    if (!gameState) return false

    if (card.rank === '8') {
      return true
    }

    if (gameState.active_suit) {
      return card.suit === gameState.active_suit
    }

    if (!gameState.top_card) return false
    const topCard = parseCard(gameState.top_card)
    return card.suit === topCard.suit || card.rank === topCard.rank
  }

  const handlePlayCard = async () => {
    if (!selectedCard || !gameState) return

    const isEight = selectedCard.rank === '8'

    try {
      const response = await fetch(`${API_BASE_URL}/games/${gameId}/play?player_id=${playerId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          card: `${selectedCard.rank}${selectedCard.suit}`,
          declared_suit: isEight ? declaredSuit : null
        })
      })
      if (!response.ok) {
        const error = await response.json().catch(() => ({}))
        alert(error.detail || 'Failed to play card')
        return
      }
      setSelectedCard(null)
      setDeclaredSuit(null)
    } catch (error) {
      console.error('Failed to play card:', error)
      alert('Failed to play card')
    }
  }

  const handleDrawCard = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/games/${gameId}/draw?player_id=${playerId}`, {
        method: 'POST'
      })
      if (!response.ok) {
        const error = await response.json().catch(() => ({}))
        alert(error.detail || 'Failed to draw card')
      }
    } catch (error) {
      console.error('Failed to draw card:', error)
      alert('Failed to draw card')
    }
  }

  if (loading) return <div className="game-board">Loading...</div>
  if (!gameState) return <div className="game-board">Error loading game</div>

  const isCurrentPlayer = gameState.current_player_id === playerId
  const topCard = gameState.top_card ? parseCard(gameState.top_card) : null
  const otherPlayer = gameState.players?.find((p: any) => p.id !== playerId)

  return (
    <div className="game-board">
      <div className="header">
        <h1>🃏 Crazy Eights</h1>
        <div className="game-info">
          <span>Game ID: {gameId}</span>
        </div>
      </div>

      <div className="game-area">
        {/* Other player's info */}
        {otherPlayer && (
          <div className="other-player">
            <h3>{otherPlayer.name}</h3>
            <p>{otherPlayer.hand_size} cards</p>
          </div>
        )}

        {/* Discard pile - Top card */}
        <div className="pile-area">
          <div className="top-card">
            {topCard ? (
              <div className={`card rank-${topCard.rank} suit-${topCard.suit}`}>
                <span>{topCard.rank}</span>
                <span>{topCard.suit}</span>
              </div>
            ) : (
              <div className="card empty">-</div>
            )}
          </div>
          <p>Top Card</p>
          {gameState.active_suit && (
            <div className="active-suit">
              Active suit: <span>{gameState.active_suit}</span>
            </div>
          )}
        </div>

        {/* Deck - Draw pile */}
        <div className="pile-area">
          <div
            className="deck"
            onClick={isCurrentPlayer ? handleDrawCard : undefined}
            style={{ cursor: isCurrentPlayer ? 'pointer' : 'default' }}
          >
            <div className="card deck-back">DECK</div>
          </div>
          <p>Draw ({gameState.deck_size} cards)</p>
        </div>
      </div>

      {/* Player's hand */}
      <div className="hand">
        <h3>Your Hand</h3>
        <div className="cards-container">
          {hand.map((card, idx) => (
            <div
              key={idx}
              className={`card playable rank-${card.rank} suit-${card.suit} ${
                cardsEqual(selectedCard, card) ? 'selected' : ''
              } ${canPlayCard(card) ? 'can-play' : 'cannot-play'}`}
              onClick={() => setSelectedCard((prev) => (cardsEqual(prev, card) ? null : card))}
            >
              <span>{card.rank}</span>
              <span>{card.suit}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Action buttons */}
      {isCurrentPlayer && selectedCard && (
        <div className="actions">
          {selectedCard.rank === '8' ? (
            <div className="suit-selector">
              <label>Declare suit for 8:</label>
              <select value={declaredSuit || ''} onChange={(e) => setDeclaredSuit(e.target.value)}>
                <option value="">Select suit...</option>
                <option value="♥">Hearts ♥</option>
                <option value="♦">Diamonds ♦</option>
                <option value="♣">Clubs ♣</option>
                <option value="♠">Spades ♠</option>
              </select>
              <button
                onClick={handlePlayCard}
                disabled={!declaredSuit}
                className="btn btn-primary"
              >
                Play 8
              </button>
            </div>
          ) : (
            <button onClick={handlePlayCard} className="btn btn-primary">
              Play Card
            </button>
          )}
        </div>
      )}

      {/* Game status */}
      {gameState.winner_id && (
        <div className="game-over">
          <h2>🎉 {gameState.winner_name} Wins!</h2>
        </div>
      )}

      {!isCurrentPlayer && !gameState.winner_id && (
        <div className="waiting">
          Waiting for {gameState.current_player_name}...
        </div>
      )}
    </div>
  )
}
