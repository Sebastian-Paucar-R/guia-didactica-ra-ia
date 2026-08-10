import 'package:flutter/material.dart';

/// Representa un módulo/norma de Ingeniería de Software dentro del dashboard.
class Normativa {
  final String codigo; // Ej. "ISO/IEC 25010"
  final String titulo; // Ej. "Calidad de Producto de Software"
  final IconData icono;
  final Color color;
  final int progreso; // 0 - 100
  final String nivel; // Ej. "Avanzado", "Intermedio", "Nuevo"

  const Normativa({
    required this.codigo,
    required this.titulo,
    required this.icono,
    required this.color,
    required this.progreso,
    required this.nivel,
  });
}