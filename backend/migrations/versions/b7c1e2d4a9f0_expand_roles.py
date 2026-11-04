"""expand user roles: super_admin, hr, team_lead, auditor

Revision ID: b7c1e2d4a9f0
Revises: 9f13fd6fcd6c
Create Date: 2026-09-21 12:00:00

"""
from alembic import op
import sqlalchemy as sa


revision = 'b7c1e2d4a9f0'
down_revision = '9f13fd6fcd6c'
branch_labels = None
depends_on = None

OLD = ('admin', 'manager', 'employee')
NEW = ('super_admin', 'admin', 'hr', 'manager', 'team_lead', 'employee', 'auditor')


def upgrade():
    if op.get_bind().dialect.name == 'postgresql':
        # ADD VALUE can't share a transaction with a statement that uses it.
        with op.get_context().autocommit_block():
            for role in ('super_admin', 'hr', 'team_lead', 'auditor'):
                op.execute(f"ALTER TYPE user_role ADD VALUE IF NOT EXISTS '{role}'")
    else:
        with op.batch_alter_table('users') as batch_op:
            batch_op.alter_column(
                'role',
                existing_type=sa.Enum(*OLD, name='user_role'),
                type_=sa.Enum(*NEW, name='user_role'),
                existing_nullable=False,
            )

    # Someone has to be able to manage the admins: promote the oldest admin.
    op.execute(
        "UPDATE users SET role = 'super_admin' WHERE id = "
        "(SELECT id FROM (SELECT MIN(id) AS id FROM users WHERE role = 'admin') AS oldest)"
    )


def downgrade():
    op.execute("UPDATE users SET role = 'admin' WHERE role = 'super_admin'")
    op.execute("UPDATE users SET role = 'manager' WHERE role IN ('hr', 'team_lead')")
    op.execute("UPDATE users SET role = 'employee' WHERE role = 'auditor'")
    if op.get_bind().dialect.name != 'postgresql':
        # Postgres can't drop enum values; the extra labels are simply unused.
        with op.batch_alter_table('users') as batch_op:
            batch_op.alter_column(
                'role',
                existing_type=sa.Enum(*NEW, name='user_role'),
                type_=sa.Enum(*OLD, name='user_role'),
                existing_nullable=False,
            )
