"""esquema inicial: usuarios, perfiles, conversaciones, mensajes, eventos_perfil

Revision ID: 0001
Revises:
Create Date: 2026-09-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("uid_firebase", sa.String(128), primary_key=True),
        sa.Column("correo", sa.String(255), nullable=False),
        sa.Column("nombre", sa.String(255)),
        sa.Column("foto_url", sa.String(1000)),
        sa.Column("proveedor", sa.String(30), nullable=False),
        sa.Column("rol", sa.String(20), nullable=False, server_default="estudiante"),
        sa.Column("fecha_registro", sa.String(40), nullable=False),
        sa.Column("ultimo_acceso", sa.String(40), nullable=False),
        sa.Column("consentimiento_aceptado", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("consentimiento_fecha", sa.String(40)),
    )

    op.create_table(
        "perfiles",
        sa.Column("uid_firebase", sa.String(128), sa.ForeignKey("usuarios.uid_firebase"), primary_key=True),
        sa.Column("datos", sa.JSON(), nullable=False),
        sa.Column("creado_en", sa.String(40), nullable=False),
        sa.Column("actualizado_en", sa.String(40), nullable=False),
    )

    op.create_table(
        "conversaciones",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("uid_firebase", sa.String(128), sa.ForeignKey("usuarios.uid_firebase"), nullable=False),
        sa.Column("titulo", sa.String(200)),
        sa.Column("fecha_inicio", sa.String(40), nullable=False),
        sa.Column("fecha_ultimo_mensaje", sa.String(40), nullable=False),
    )
    op.create_index("ix_conversaciones_uid_firebase", "conversaciones", ["uid_firebase"])

    op.create_table(
        "mensajes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("conversacion_id", sa.String(64), sa.ForeignKey("conversaciones.id"), nullable=False),
        sa.Column("rol", sa.String(20), nullable=False),
        sa.Column("contenido", sa.Text(), nullable=False),
        sa.Column("tipo", sa.String(30)),
        sa.Column("desde_cache", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("latencia_ms", sa.Float()),
        sa.Column("tema_detectado", sa.String(20)),
        sa.Column("unidad_detectada", sa.Integer()),
        sa.Column("fecha", sa.String(40), nullable=False),
    )
    op.create_index("ix_mensajes_conversacion_id", "mensajes", ["conversacion_id"])
    op.create_index("ix_mensajes_fecha", "mensajes", ["fecha"])

    op.create_table(
        "eventos_perfil",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("uid_firebase", sa.String(128), sa.ForeignKey("usuarios.uid_firebase"), nullable=False),
        sa.Column("unidad", sa.Integer(), nullable=False),
        sa.Column("nivel", sa.Float(), nullable=False),
        sa.Column("motivo", sa.String(30), nullable=False),
        sa.Column("tema_id", sa.String(20)),
        sa.Column("fecha", sa.String(40), nullable=False),
    )
    op.create_index("ix_eventos_perfil_uid_firebase", "eventos_perfil", ["uid_firebase"])


def downgrade() -> None:
    op.drop_table("eventos_perfil")
    op.drop_table("mensajes")
    op.drop_table("conversaciones")
    op.drop_table("perfiles")
    op.drop_table("usuarios")
