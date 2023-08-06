"""assessment update

Revision ID: 74880d597341
Revises: d74f1fb1ad92
Create Date: 2023-08-06 17:34:22.884977

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '74880d597341'
down_revision = 'd74f1fb1ad92'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('assessments', sa.Column('is_active', sa.Boolean(), server_default='FALSE', nullable=False))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('assessments', 'is_active')
    # ### end Alembic commands ###