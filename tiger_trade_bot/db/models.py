"""
SQLAlchemy models for Tiger Trade Bot feature store and trade history.

Tables:
- trades: Executed trades (fills)
- predictions: Strategy predictions/features at time of decision
- model_versions: ML model metadata and performance metrics
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, JSON,
    ForeignKey, Index
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Trade(Base):
    """Record of a filled trade."""
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tiger_order_id = Column(String(64), nullable=False, index=True)
    symbol = Column(String(16), nullable=False, index=True)
    side = Column(String(4), nullable=False)  # BUY/SELL
    quantity = Column(Integer, nullable=False)
    avg_fill_price = Column(Float, nullable=False)
    order_type = Column(String(16), nullable=False)
    filled_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    commission = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)  # For closing trades

    __table_args__ = (
        Index('ix_trades_symbol_filled', 'symbol', 'filled_at'),
    )


class Prediction(Base):
    """Strategy prediction with features for ML training."""
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(16), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    strategy = Column(String(32), nullable=False, index=True)
    direction = Column(String(4), nullable=False)  # BUY/SELL/FLAT
    confidence = Column(Float, nullable=False)  # 0-1
    features = Column(JSON, nullable=False)  # Dict of feature values
    outcome = Column(String(16), nullable=True)  # success/failure/flat, set later
    realized_pnl = Column(Float, nullable=True)  # Set when trade completes
    meta = Column(JSON, nullable=True)  # Additional context

    __table_args__ = (
        Index('ix_predictions_symbol_ts', 'symbol', 'timestamp'),
    )


class ModelVersion(Base):
    """ML model version metadata and performance."""
    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_name = Column(String(64), nullable=False, index=True)
    version = Column(String(32), nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    is_active = Column(Boolean, default=True, index=True)
    metrics = Column(JSON, nullable=False)  # accuracy, precision, recall, etc.
    artifact_path = Column(String(256), nullable=True)  # Path to model file/storage
    comments = Column(Text, nullable=True)

    __table_args__ = (
        Index('ix_model_active', 'model_name', 'is_active'),
    )
