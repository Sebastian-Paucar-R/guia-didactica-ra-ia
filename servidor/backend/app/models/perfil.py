"""Perfil del estudiante: lo que el tutor estima de cada persona para ajustar CÓMO explica.

Es solo el modelo de datos y sus operaciones elementales; quien lo persiste es `services/perfil_service.py` y quien
decide cuándo cambia es `services/adaptacion_service.py`. El perfil nunca modifica qué dice la norma: solo la
profundidad, el andamiaje y las referencias a lo ya trabajado.

El nivel por unidad es una estimación continua entre 1 y 5 (se mueve en pasos pequeños para que un solo mensaje no
cambie la opinión del tutor de un extremo al otro) y se agrupa en tres franjas al adaptar: bajo (< 2,5), medio y
alto (> 3,5). `UNIDADES` son las cuatro del sílabo (configuracion/silabo.yaml); un test comprueba que coinciden.
"""
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator

UNIDADES = (1, 2, 3, 4)
NIVEL_INICIAL = 3.0
NIVEL_MIN, NIVEL_MAX = 1.0, 5.0
UMBRAL_NIVEL_BAJO = 2.5   # por debajo: nivel "bajo"
UMBRAL_NIVEL_ALTO = 3.5   # por encima: nivel "alto"
MAX_HISTORIAL = 5         # últimos temas trabajados que se resumen
VENTANA_SENALES = 12      # señales recientes con las que se infiere profundidad y estilo

PROFUNDIDADES = ("breve", "media", "extensa")
ESTILOS = ("conceptual", "ejemplos", "comparativo")
Profundidad = Literal["breve", "media", "extensa"]
Estilo = Literal["conceptual", "ejemplos", "comparativo"]


def ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Ritmo(BaseModel):
    """Cuánto y cuánto tiempo conversa. Una sesión es una conversación (`conversation_id`)."""
    sesiones: int = 0
    mensajes_totales: int = 0
    mensajes_por_sesion: float = 0.0
    duracion_media_s: float = 0.0   # solo sesiones con al menos dos mensajes: con uno la duración no significa nada


class TemaReciente(BaseModel):
    tema_id: str
    tema: str
    unidad: int
    fecha: str


class CambioNivel(BaseModel):
    """Un movimiento del nivel estimado de una unidad: alimenta la evolución que muestra `/perfil/{id}/progreso`."""
    unidad: int
    nivel: float          # nivel después del cambio
    motivo: str           # confusion | reflexion_correcta
    tema_id: str | None = None


class PerfilEstudiante(BaseModel):
    user_id: str
    nivel_por_unidad: dict[int, float] = Field(default_factory=lambda: {u: NIVEL_INICIAL for u in UNIDADES})
    temas_consultados: dict[str, int] = Field(default_factory=dict)          # id de tema del YAML -> consultas
    temas_con_dificultad: list[str] = Field(default_factory=list)            # ids de tema
    profundidad_preferida: Profundidad = "media"
    estilo_preferido: Estilo = "conceptual"
    ritmo: Ritmo = Field(default_factory=Ritmo)
    historial_resumido: list[TemaReciente] = Field(default_factory=list)     # últimos 5 temas distintos, el más reciente al final
    # Estado de la inferencia (se persiste para que sobreviva a reinicios y se pueda inspeccionar)
    aclaraciones_por_tema: dict[str, int] = Field(default_factory=dict)
    senales_recientes: list[str] = Field(default_factory=list)
    creado_en: str | None = None
    actualizado_en: str | None = None

    @field_validator("nivel_por_unidad")
    @classmethod
    def _completar_y_acotar(cls, niveles: dict[int, float]) -> dict[int, float]:
        desconocidas = set(niveles) - set(UNIDADES)
        if desconocidas:
            raise ValueError(f"unidades fuera del sílabo: {sorted(desconocidas)}")
        return {u: round(min(max(float(niveles.get(u, NIVEL_INICIAL)), NIVEL_MIN), NIVEL_MAX), 2) for u in UNIDADES}

    def es_neutro(self) -> bool:
        """¿No hay nada que ajustar? Todos los niveles en la franja media, profundidad y estilo por defecto, sin temas con
        dificultad ni historial al que referirse: el prompt sale idéntico al de un estudiante anónimo."""
        return (all(UMBRAL_NIVEL_BAJO <= n <= UMBRAL_NIVEL_ALTO for n in self.nivel_por_unidad.values())
                and self.profundidad_preferida == "media" and self.estilo_preferido == "conceptual"
                and not self.temas_con_dificultad and not self.historial_resumido)

    # ------------------------------------------------------------------ nivel

    def nivel(self, unidad: int) -> float:
        return self.nivel_por_unidad.get(unidad, NIVEL_INICIAL)

    def franja(self, unidad: int | None) -> str:
        """bajo | medio | alto. Sin unidad conocida no se presume nada: medio."""
        if unidad is None:
            return "medio"
        n = self.nivel(unidad)
        return "bajo" if n < UMBRAL_NIVEL_BAJO else "alto" if n > UMBRAL_NIVEL_ALTO else "medio"

    def mover_nivel(self, unidad: int, delta: float) -> tuple[float, float]:
        """Suma `delta` al nivel de la unidad sin salir de [1, 5]. Devuelve (antes, después)."""
        antes = self.nivel(unidad)
        despues = round(min(max(antes + delta, NIVEL_MIN), NIVEL_MAX), 2)
        self.nivel_por_unidad[unidad] = despues
        return antes, despues

    # ------------------------------------------------------------------ temas

    def registrar_tema(self, tema_id: str, tema: str, unidad: int, fecha: str | None = None) -> None:
        """Cuenta la consulta y lo deja como el tema más reciente del historial (sin repetirlo: si ya estaba, sube al
        final). El historial guarda solo los últimos `MAX_HISTORIAL` temas distintos."""
        self.temas_consultados[tema_id] = self.temas_consultados.get(tema_id, 0) + 1
        self.historial_resumido = [t for t in self.historial_resumido if t.tema_id != tema_id]
        self.historial_resumido.append(TemaReciente(tema_id=tema_id, tema=tema, unidad=unidad, fecha=fecha or ahora()))
        del self.historial_resumido[:-MAX_HISTORIAL]

    def sintesis_historial(self) -> str:
        """Los últimos temas trabajados en una línea (más reciente primero); vacío si no hay ninguno."""
        return "; ".join(f"«{t.tema}» (Unidad {t.unidad})" for t in reversed(self.historial_resumido))
