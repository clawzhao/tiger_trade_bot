"""
Tests for database models and session.
"""

import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tiger_trade_bot.db.models import Base, Trade, Prediction, ModelVersion


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def db_session(in_memory_db):
    """Provide a fresh database session for each test."""
    Session = sessionmaker(bind=in_memory_db, autocommit=False, autoflush=False)
    session = Session()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_create_trade(db_session):
    """Test creating a Trade record."""
    trade = Trade(
        tiger_order_id="TIGER_123",
        symbol="AAPL",
        side="BUY",
        quantity=100,
        avg_fill_price=150.0,
        order_type="MARKET",
    )
    db_session.add(trade)
    db_session.commit()

    retrieved = db_session.query(Trade).filter_by(tiger_order_id="TIGER_123").first()
    assert retrieved is not None
    assert retrieved.symbol == "AAPL"
    assert retrieved.quantity == 100
    assert retrieved.avg_fill_price == 150.0


def test_create_prediction(db_session):
    """Test creating a Prediction record."""
    pred = Prediction(
        symbol="AAPL",
        timestamp=datetime.utcnow(),
        strategy="gap",
        direction="BUY",
        confidence=0.85,
        features={"gap_pct": 0.025, "volume": 1000000},
        outcome="success",
        realized_pnl=250.0,
        meta={"notes": "test"},
    )
    db_session.add(pred)
    db_session.commit()

    retrieved = db_session.query(Prediction).filter_by(symbol="AAPL").first()
    assert retrieved is not None
    assert retrieved.direction == "BUY"
    assert retrieved.confidence == 0.85
    assert retrieved.features["gap_pct"] == 0.025


def test_create_model_version(db_session):
    """Test creating a ModelVersion record."""
    mv = ModelVersion(
        model_name="gap_strategy_v1",
        version="1.0.0",
        is_active=True,
        metrics={"accuracy": 0.72, "precision": 0.68},
        artifact_path="./models/gap_v1.pkl",
        comments="Initial version",
    )
    db_session.add(mv)
    db_session.commit()

    retrieved = db_session.query(ModelVersion).filter_by(model_name="gap_strategy_v1").first()
    assert retrieved is not None
    assert retrieved.version == "1.0.0"
    assert retrieved.is_active is True
    assert retrieved.metrics["accuracy"] == 0.72


def test_trade_indexes(in_memory_db, db_session):
    """Ensure indexes exist and can be used (basic check)."""
    # Insert some trades with specific timestamps
    import time
    now = datetime.utcnow()
    for i in range(5):
        trade = Trade(
            tiger_order_id=f"ORDER_{i}",
            symbol="AAPL",
            side="BUY",
            quantity=10,
            avg_fill_price=100.0,
            order_type="MARKET",
            filled_at=now,
        )
        db_session.add(trade)
    db_session.commit()

    # Query by symbol (should have index)
    result = db_session.query(Trade).filter_by(symbol="AAPL").all()
    assert len(result) == 5


def test_get_db_session_generator(in_memory_db):
    """Test get_db provides a working session and closes it."""
    from tiger_trade_bot.db.session import get_db

    # Consume generator
    gen = get_db()
    db = next(gen)
    try:
        # Should be a valid session
        result = db.execute("SELECT 1").fetchone()
        assert result[0] == 1
    finally:
        # Generator will close in finally, but we can also close manually if needed
        try:
            next(gen)
        except StopIteration:
            pass

