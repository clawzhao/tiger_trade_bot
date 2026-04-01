"""initial feature store schema

Revision ID: 001_initial_feature_store
Revises: 
Create Date: 2025-04-01 04:20:00 UTC

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '001_initial_feature_store'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial tables: trades, predictions, model_versions."""
    # trades table
    op.create_table(
        'trades',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('tiger_order_id', sa.String(64), nullable=False, index=True),
        sa.Column('symbol', sa.String(16), nullable=False, index=True),
        sa.Column('side', sa.String(4), nullable=False),
        sa.Column('quantity', sa.Integer, nullable=False),
        sa.Column('avg_fill_price', sa.Float, nullable=False),
        sa.Column('order_type', sa.String(16), nullable=False),
        sa.Column('filled_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('commission', sa.Float, nullable=True, server_default='0.0'),
        sa.Column('realized_pnl', sa.Float, nullable=True, server_default='0.0'),
        sa.Index('ix_trades_symbol_filled', 'symbol', 'filled_at'),
    )

    # predictions table
    op.create_table(
        'predictions',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('symbol', sa.String(16), nullable=False, index=True),
        sa.Column('timestamp', sa.DateTime, nullable=False, index=True),
        sa.Column('strategy', sa.String(32), nullable=False, index=True),
        sa.Column('direction', sa.String(4), nullable=False),
        sa.Column('confidence', sa.Float, nullable=False),
        sa.Column('features', sa.JSON, nullable=False),
        sa.Column('outcome', sa.String(16), nullable=True),
        sa.Column('realized_pnl', sa.Float, nullable=True),
        sa.Column('meta', sa.JSON, nullable=True),
        sa.Index('ix_predictions_symbol_ts', 'symbol', 'timestamp'),
    )

    # model_versions table
    op.create_table(
        'model_versions',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('model_name', sa.String(64), nullable=False, index=True),
        sa.Column('version', sa.String(32), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('is_active', sa.Boolean, nullable=True, server_default='1', index=True),
        sa.Column('metrics', sa.JSON, nullable=False),
        sa.Column('artifact_path', sa.String(256), nullable=True),
        sa.Column('comments', sa.Text, nullable=True),
        sa.Index('ix_model_active', 'model_name', 'is_active'),
    )


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table('model_versions')
    op.drop_table('predictions')
    op.drop_table('trades')
