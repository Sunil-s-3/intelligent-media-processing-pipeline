"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-04-18

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "images",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("stored_filename", sa.String(length=512), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("perceptual_hash", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_images_status", "images", ["status"])
    op.create_index("ix_images_perceptual_hash", "images", ["perceptual_hash"])
    op.create_index("ix_images_created_at", "images", ["created_at"])
    op.create_index("ix_images_status_created_at", "images", ["status", "created_at"])

    op.create_table(
        "analysis_results",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("image_id", sa.String(length=36), nullable=False),
        sa.Column("blur_result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("brightness_result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("duplicate_result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ocr_result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "vehicle_number_result",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("screenshot_result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["image_id"], ["images.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("image_id"),
    )
    op.create_index("ix_analysis_results_image_id", "analysis_results", ["image_id"])


def downgrade() -> None:
    op.drop_index("ix_analysis_results_image_id", table_name="analysis_results")
    op.drop_table("analysis_results")
    op.drop_index("ix_images_status_created_at", table_name="images")
    op.drop_index("ix_images_created_at", table_name="images")
    op.drop_index("ix_images_perceptual_hash", table_name="images")
    op.drop_index("ix_images_status", table_name="images")
    op.drop_table("images")
