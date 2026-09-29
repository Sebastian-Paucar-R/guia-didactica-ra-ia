"""Compatibilidad: permite importar chromadb aunque el binario nativo de grpc no cargue.

chromadb importa, sin condición y solo por importarlo, un exportador de trazas OTLP/gRPC
(chromadb.auth.token_authn -> chromadb.telemetry.opentelemetry -> grpc), aunque este proyecto nunca
envía telemetría ni configura un endpoint OTLP. En Windows, si una directiva de Control de
aplicaciones (Smart App Control / WDAC) bloquea el .pyd nativo de grpc (`cygrpc`) — visto en este
proyecto como `ImportError: DLL load failed while importing cygrpc: Una directiva de Control de
aplicaciones bloqueó este archivo — chromadb deja de poder importarse por completo, aunque el resto
(el índice vectorial, los embeddings, Ollama) no necesita grpc para nada.

`permitir_chromadb_sin_grpc()` intenta la importación normal de `grpc`; si funciona, no hace nada
(cero cambio de comportamiento en una máquina sin este bloqueo). Si falla por un ImportError, deja en
`sys.modules` un módulo vacío en su lugar (y el exportador OTLP/gRPC que lo usa), antes de que
chromadb los pida: como nunca se llama a nada de ese módulo, sirve para importar sin romper nada.
Debe llamarse antes de `import chromadb` / `from langchain_chroma import ...`.
"""
import importlib
import sys
import types

_MODULOS_GRPC_SIMULADOS = ("grpc", "opentelemetry.exporter.otlp.proto.grpc.trace_exporter")


def permitir_chromadb_sin_grpc() -> None:
    try:
        importlib.import_module("grpc")
        return   # grpc funciona de verdad: nada que sustituir
    except ImportError as e:
        print(f"[RAG] grpc no se pudo importar ({e}); se usa un módulo vacío (chromadb no lo necesita en este proyecto).")

    falso_grpc = types.ModuleType("grpc")
    for nombre in ("ChannelCredentials", "Compression", "StatusCode"):
        setattr(falso_grpc, nombre, type(nombre, (), {}))
    sys.modules.setdefault("grpc", falso_grpc)

    falso_exportador = types.ModuleType("opentelemetry.exporter.otlp.proto.grpc.trace_exporter")
    falso_exportador.OTLPSpanExporter = type("OTLPSpanExporter", (), {})
    sys.modules.setdefault("opentelemetry.exporter.otlp.proto.grpc.trace_exporter", falso_exportador)
