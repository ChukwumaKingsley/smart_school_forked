"""Modified course table so that the primary key is the course_id, which would be a combination of the coursecode and the session

Revision ID: 74ec682fbbf7
Revises: e458696e0071
Create Date: 2023-11-17 11:22:59.477283

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '74ec682fbbf7'
down_revision = 'e458696e0071'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('courses', sa.Column('course_id', sa.String(), nullable=False))
    op.add_column('courses', sa.Column('session', sa.String(), nullable=False))
    op.drop_index('ix_courses_course_code', table_name='courses')
    op.create_index(op.f('ix_courses_course_id'), 'courses', ['course_id'], unique=True)
    op.add_column('enrollments', sa.Column('course_id', sa.String(), nullable=False))
    op.add_column('enrollments', sa.Column('session', sa.String(), nullable=False))
    op.drop_constraint('enrollments_course_code_fkey', 'enrollments', type_='foreignkey')
    op.create_foreign_key(None, 'enrollments', 'courses', ['course_id'], ['course_id'], ondelete='CASCADE')
    op.drop_column('enrollments', 'course_code')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('enrollments', sa.Column('course_code', sa.VARCHAR(), autoincrement=False, nullable=False))
    op.drop_constraint(None, 'enrollments', type_='foreignkey')
    op.create_foreign_key('enrollments_course_code_fkey', 'enrollments', 'courses', ['course_code'], ['course_code'], ondelete='CASCADE')
    op.drop_column('enrollments', 'session')
    op.drop_column('enrollments', 'course_id')
    op.drop_index(op.f('ix_courses_course_id'), table_name='courses')
    op.create_index('ix_courses_course_code', 'courses', ['course_code'], unique=False)
    op.drop_column('courses', 'session')
    op.drop_column('courses', 'course_id')
    # ### end Alembic commands ###
