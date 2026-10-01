"""Modelos ORM (SQLAlchemy) para identidad y persistencia por estudiante.

Siete tablas:
- `usuarios`: identidad (viene de Firebase Authentication; aquí nunca se guarda una contraseña, solo lo que
  Firebase ya verificó: uid, correo, nombre, foto, proveedor) y rol dentro de la app.
- `perfiles`: el perfil adaptativo (`app.models.perfil.PerfilEstudiante`) de cada estudiante, con clave foránea a
  `usuarios`. Se guarda como JSON (columna `datos`): sus campos son naturalmente un documento (niveles por unidad,
  temas consultados, historial resumido...) y ya se serializaba así en SQLite; normalizarlo en columnas no
  aportaría nada que este proyecto consulte por SQL.
- `conversaciones` / `mensajes`: historial persistente del chat (antes solo vivía en RAM, `memoria_service.py`,
  y se perdía al reiniciar). `mensajes` es lo que alimenta las estadísticas docentes (preguntas por unidad, etc.).
- `eventos_perfil`: cada ajuste del nivel estimado de una unidad, con la señal que lo disparó (`motivo`) y el
  tema, para reconstruir la evolución de un estudiante. Reemplaza la tabla `progreso` del `perfiles.db` anterior.
- `progreso_estudiante` / `eventos_progreso`: progreso de la app (lecciones completadas, ejercicios resueltos, XP,
  racha) — distinto de `perfiles`/`eventos_perfil`, que es el nivel ESTIMADO por el tutor a partir del
  comportamiento en el chat. `progreso_estudiante` es un acumulado (una fila por estudiante, para leerlo rápido);
  `eventos_progreso` es el registro de cada evento (para el detalle y las estadísticas docentes). Ver
  `services/progreso_service.py`.

Cada tabla usa cadenas ISO 8601 para fechas (`ahora()` de `app.models.perfil`), igual que el resto del proyecto
(cache_service.py, la versión anterior de perfil_service.py): son ordenables como texto, legibles en un volcado
y no atan el código a la zona horaria de la columna de un motor de base de datos en particular.
"""
from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

UID_LEN = 128


class Usuario(Base):
    __tablename__ = "usuarios"

    uid_firebase: Mapped[str] = mapped_column(String(UID_LEN), primary_key=True)
    correo: Mapped[str] = mapped_column(String(255), nullable=False)
    nombre: Mapped[str | None] = mapped_column(String(255))
    foto_url: Mapped[str | None] = mapped_column(String(1000))
    proveedor: Mapped[str] = mapped_column(String(30), nullable=False)   # google | password
    rol: Mapped[str] = mapped_column(String(20), nullable=False, default="estudiante")  # estudiante|docente|admin
    fecha_registro: Mapped[str] = mapped_column(String(40), nullable=False)
    ultimo_acceso: Mapped[str] = mapped_column(String(40), nullable=False)
    consentimiento_aceptado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    consentimiento_fecha: Mapped[str | None] = mapped_column(String(40))

    perfil: Mapped["Perfil"] = relationship(back_populates="usuario", uselist=False, cascade="all, delete-orphan")
    conversaciones: Mapped[list["Conversacion"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")
    eventos: Mapped[list["EventoPerfil"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")
    progreso: Mapped["ProgresoEstudiante"] = relationship(back_populates="usuario", uselist=False,
                                                          cascade="all, delete-orphan")
    eventos_progreso: Mapped[list["EventoProgreso"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")


class Perfil(Base):
    __tablename__ = "perfiles"

    uid_firebase: Mapped[str] = mapped_column(ForeignKey("usuarios.uid_firebase"), primary_key=True)
    # PerfilEstudiante.model_dump(mode="json"): nivel_por_unidad, temas_consultados, temas_con_dificultad,
    # profundidad/estilo preferidos, ritmo, historial_resumido, aclaraciones_por_tema, senales_recientes.
    datos: Mapped[dict] = mapped_column(JSON, nullable=False)
    creado_en: Mapped[str] = mapped_column(String(40), nullable=False)
    actualizado_en: Mapped[str] = mapped_column(String(40), nullable=False)

    usuario: Mapped[Usuario] = relationship(back_populates="perfil")


class Conversacion(Base):
    __tablename__ = "conversaciones"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)   # el conversation_id de /chat
    uid_firebase: Mapped[str] = mapped_column(ForeignKey("usuarios.uid_firebase"), nullable=False, index=True)
    titulo: Mapped[str | None] = mapped_column(String(200))         # primer mensaje del estudiante, recortado
    fecha_inicio: Mapped[str] = mapped_column(String(40), nullable=False)
    fecha_ultimo_mensaje: Mapped[str] = mapped_column(String(40), nullable=False)

    usuario: Mapped[Usuario] = relationship(back_populates="conversaciones")
    mensajes: Mapped[list["Mensaje"]] = relationship(back_populates="conversacion", cascade="all, delete-orphan")


class Mensaje(Base):
    __tablename__ = "mensajes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversacion_id: Mapped[str] = mapped_column(ForeignKey("conversaciones.id"), nullable=False, index=True)
    rol: Mapped[str] = mapped_column(String(20), nullable=False)     # estudiante | tutor
    contenido: Mapped[str] = mapped_column(Text, nullable=False)
    tipo: Mapped[str | None] = mapped_column(String(30))             # saludo|funcionamiento|respuesta|...
    desde_cache: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    latencia_ms: Mapped[float | None] = mapped_column(Float)
    tema_detectado: Mapped[str | None] = mapped_column(String(20))
    unidad_detectada: Mapped[int | None] = mapped_column(Integer)
    fecha: Mapped[str] = mapped_column(String(40), nullable=False, index=True)

    conversacion: Mapped[Conversacion] = relationship(back_populates="mensajes")


class EventoPerfil(Base):
    __tablename__ = "eventos_perfil"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uid_firebase: Mapped[str] = mapped_column(ForeignKey("usuarios.uid_firebase"), nullable=False, index=True)
    unidad: Mapped[int] = mapped_column(Integer, nullable=False)
    nivel: Mapped[float] = mapped_column(Float, nullable=False)      # nivel estimado después del cambio
    motivo: Mapped[str] = mapped_column(String(30), nullable=False)  # señal disparadora: confusion|reflexion_correcta
    tema_id: Mapped[str | None] = mapped_column(String(20))
    fecha: Mapped[str] = mapped_column(String(40), nullable=False)

    usuario: Mapped[Usuario] = relationship(back_populates="eventos")


class ProgresoEstudiante(Base):
    """Acumulado de progreso de la app (una fila por estudiante): XP total, racha de días consecutivos con
    actividad y cuántas lecciones/ejercicios lleva. `services/progreso_service.py` es el único que la escribe
    (a partir de `eventos_progreso`); todo lo demás la lee."""
    __tablename__ = "progreso_estudiante"

    uid_firebase: Mapped[str] = mapped_column(ForeignKey("usuarios.uid_firebase"), primary_key=True)
    xp_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    racha_actual: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    racha_mejor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ultima_actividad_fecha: Mapped[str | None] = mapped_column(String(40))   # solo la fecha (YYYY-MM-DD), no la hora
    lecciones_completadas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ejercicios_resueltos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ejercicios_correctos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    actualizado_en: Mapped[str] = mapped_column(String(40), nullable=False)

    usuario: Mapped[Usuario] = relationship(back_populates="progreso")


class EventoProgreso(Base):
    """Cada lección completada o ejercicio resuelto, con el XP que otorgó — el detalle que
    `progreso_estudiante` resume. `leccion_id` es el id que manda la app (ver configuracion/lecciones.json para
    su relación, si la tiene, con un tema del sílabo)."""
    __tablename__ = "eventos_progreso"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uid_firebase: Mapped[str] = mapped_column(ForeignKey("usuarios.uid_firebase"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)   # leccion_completada | ejercicio_resuelto
    leccion_id: Mapped[str | None] = mapped_column(String(50), index=True)
    ejercicio_id: Mapped[str | None] = mapped_column(String(50))
    correcto: Mapped[bool | None] = mapped_column(Boolean)          # solo para ejercicio_resuelto
    xp_otorgado: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fecha: Mapped[str] = mapped_column(String(40), nullable=False, index=True)

    usuario: Mapped[Usuario] = relationship(back_populates="eventos_progreso")
