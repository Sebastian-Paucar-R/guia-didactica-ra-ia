"""progreso de la app: progreso_estudiante, eventos_progreso

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "progreso_estudiante",
        sa.Column("uid_firebase", sa.String(128), sa.ForeignKey("usuarios.uid_firebase"), primary_key=True),
        sa.Column("xp_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("racha_actual", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("racha_mejor", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ultima_actividad_fecha", sa.String(40)),
        sa.Column("lecciones_completadas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ejercicios_resueltos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ejercicios_correctos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("actualizado_en", sa.String(40), nullable=False),
    )

    op.create_table(
        "eventos_progreso",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("uid_firebase", sa.String(128), sa.ForeignKey("usuarios.uid_firebase"), nullable=False),
        sa.Column("tipo", sa.String(30), nullable=False),
        sa.Column("leccion_id", sa.String(50)),
        sa.Column("ejercicio_id", sa.String(50)),
        sa.Column("correcto", sa.Boolean()),
        sa.Column("xp_otorgado", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fecha", sa.String(40), nullable=False),
    )
    op.create_index("ix_eventos_progreso_uid_firebase", "eventos_progreso", ["uid_firebase"])
    op.create_index("ix_eventos_progreso_leccion_id", "eventos_progreso", ["leccion_id"])
    op.create_index("ix_eventos_progreso_fecha", "eventos_progreso", ["fecha"])


def downgrade() -> None:
    op.drop_table("eventos_progreso")
    op.drop_table("progreso_estudiante")
