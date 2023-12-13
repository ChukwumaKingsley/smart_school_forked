"""Added assessment time records for students

Revision ID: 01bc9edee04b
Revises: 9c29045ad77d
Create Date: 2023-12-13 19:55:20.904429

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '01bc9edee04b'
down_revision = '9c29045ad77d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('assessment time records',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('student_id', sa.BigInteger(), nullable=False),
    sa.Column('assessment_id', sa.Integer(), nullable=False),
    sa.Column('start_datetime', sa.DateTime(), nullable=True),
    sa.Column('end_datetime', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_assessment time records_id'), 'assessment time records', ['id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_assessment time records_id'), table_name='assessment time records')
    op.drop_table('assessment time records')
    # ### end Alembic commands ###
