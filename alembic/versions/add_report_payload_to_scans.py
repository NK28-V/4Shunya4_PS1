"""Add report_payload to scans

Revision ID: add_report_payload
Revises:
Create Date: 2025-03-01

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_report_payload"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scans", sa.Column("report_payload", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("scans", "report_payload")
