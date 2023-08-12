"""assessment model update

Revision ID: 8ab464820b36
Revises: 8f3a18be7728
Create Date: 2023-08-07 15:02:33.285678

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8ab464820b36'
down_revision = '8f3a18be7728'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('assessments', sa.Column(
        'assessment_type', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('assessments', 'assessment_type')
    # ### end Alembic commands ###