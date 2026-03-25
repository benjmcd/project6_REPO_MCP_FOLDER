"""Initial schema placeholder for the starter repo.

The repo uses SQLAlchemy metadata create_all() for local bootstrap.
This revision exists as a chain anchor for follow-on migrations.
"""

from __future__ import annotations


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """No-op anchor revision."""


def downgrade() -> None:
    """No-op anchor revision."""
