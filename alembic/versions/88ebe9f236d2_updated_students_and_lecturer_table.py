"""updated students and lecturer table

Revision ID: 88ebe9f236d2
Revises: 3ccc2d757e94
Create Date: 2023-06-19 19:17:09.305531

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '88ebe9f236d2'
down_revision = '3ccc2d757e94'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('instructors', sa.Column('major', sa.String(), nullable=True))
    op.add_column('instructors', sa.Column('bio', sa.String(), nullable=True))
    op.add_column('instructors', sa.Column('photo_url', sa.String(), nullable=True))
    op.add_column('students', sa.Column('major', sa.String(), nullable=True))
    op.add_column('students', sa.Column('bio', sa.String(), nullable=True))
    op.add_column('students', sa.Column('photo_url', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('students', 'photo_url')
    op.drop_column('students', 'bio')
    op.drop_column('students', 'major')
    op.drop_column('instructors', 'photo_url')
    op.drop_column('instructors', 'bio')
    op.drop_column('instructors', 'major')
    # ### end Alembic commands ###
