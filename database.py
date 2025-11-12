"""
Simple SQLite database for Crazy Eights
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    create_engine,
    String,
    Integer,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    Text,
    text,
)
from sqlalchemy.orm import (
    declarative_base,
    sessionmaker,
    relationship,
    Mapped,
    mapped_column,
)

# SQLite only
DATABASE_URL = "sqlite:///./crazy_eights.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ============= Enums =============

class GameStateEnum(str, Enum):
    """Game state enumeration"""

    WAITING = "waiting"
    READY = "ready"
    ACTIVE = "active"
    FINISHED = "finished"


# ============= Models =============

class Game(Base):
    """Game model - represents a game instance"""

    __tablename__ = "games"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    state: Mapped[GameStateEnum] = mapped_column(
        SQLEnum(GameStateEnum), default=GameStateEnum.WAITING, nullable=False
    )
    winner_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    state_data: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    sessions: Mapped[list["GameSession"]] = relationship(
        "GameSession", back_populates="game", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Game(id={self.id}, state={self.state}, players={len(self.sessions)})>"


class GameSession(Base):
    """Game session model - represents a player in a game"""

    __tablename__ = "game_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    game_id: Mapped[str] = mapped_column(String, ForeignKey("games.id"), index=True)
    player_name: Mapped[str] = mapped_column(String, nullable=False)
    player_index: Mapped[int] = mapped_column(Integer, nullable=False)
    hand_cards: Mapped[str] = mapped_column(String, default="")
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    game: Mapped[Game] = relationship("Game", back_populates="sessions")

    def __repr__(self):
        return f"<GameSession(id={self.id}, game_id={self.game_id}, player={self.player_name})>"


class GameMove(Base):
    """Move history model - tracks all moves in a game"""

    __tablename__ = "game_moves"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    game_id: Mapped[str] = mapped_column(String, ForeignKey("games.id"), index=True)
    player_name: Mapped[str] = mapped_column(String, nullable=False)
    move_type: Mapped[str] = mapped_column(String, nullable=False)
    card_played: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    declared_suit: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<GameMove(id={self.id}, game_id={self.game_id}, move_type={self.move_type})>"


# ============= Database Functions =============

def get_db():
    """Dependency for FastAPI to get DB session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database with all tables"""
    Base.metadata.create_all(bind=engine)
    _ensure_state_data_column()
    print("✓ Database tables created successfully")


def drop_db():
    """Drop all tables"""
    Base.metadata.drop_all(bind=engine)
    print("✓ Database tables dropped")


def _ensure_state_data_column():
    """Add state_data column to games table if missing."""
    with engine.connect() as conn:
        tables = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='games'")
        ).fetchall()
        if not tables:
            return
        result = conn.execute(text("PRAGMA table_info(games)"))
        columns = [row[1] for row in result]
        if "state_data" not in columns:
            conn.execute(text("ALTER TABLE games ADD COLUMN state_data TEXT DEFAULT '{}'"))
            conn.commit()


_ensure_state_data_column()
