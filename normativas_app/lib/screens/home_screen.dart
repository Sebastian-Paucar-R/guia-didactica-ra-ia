import 'package:flutter/material.dart';
import '../models/normativa.dart';
import '../theme/app_theme.dart';
import '../widgets/duo_button.dart';
import '../widgets/stat_chip.dart';
import 'chat_screen.dart';

/// Pantalla de inicio ("el enganche"): banner motivacional + CTA gigante
/// + catálogo de normas ISO en tarjetas horizontales. Totalmente
/// responsive: usa LayoutBuilder/MediaQuery para adaptar paddings,
/// tamaños de tarjeta y tipografía a cualquier ancho de pantalla.
class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  static const String _nombreEstudiante = 'futuro Ingeniero';
  static const int _rachaDias = 12;

  // Catálogo de normas ISO más utilizadas en la industria del software.
  static final List<Normativa> _normativas = [
    Normativa(
      codigo: 'ISO/IEC 25010',
      titulo: 'Calidad del Producto de Software',
      icono: Icons.verified_rounded,
      color: AppColors.primaryGreen,
      progreso: 80,
      nivel: 'Avanzado',
    ),
    Normativa(
      codigo: 'ISO/IEC 12207',
      titulo: 'Procesos del Ciclo de Vida del Software',
      icono: Icons.autorenew_rounded,
      color: AppColors.electricBlue,
      progreso: 45,
      nivel: 'Intermedio',
    ),
    Normativa(
      codigo: 'ISO/IEC 27001',
      titulo: 'Seguridad de la Información',
      icono: Icons.shield_rounded,
      color: AppColors.red,
      progreso: 10,
      nivel: 'Inicial',
    ),
    Normativa(
      codigo: 'ISO/IEC 33001',
      titulo: 'Evaluación de Procesos de Software',
      icono: Icons.fact_check_rounded,
      color: AppColors.deepPurple,
      progreso: 0,
      nivel: 'Nuevo',
    ),
  ];

  Normativa get _rutaActual => _normativas.first; // ISO/IEC 25010

  void _abrirNormativa(BuildContext context, Normativa normativa) {
    Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => const ChatScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) {
            final anchoPantalla = constraints.maxWidth;
            final paddingHorizontal = anchoPantalla < 360 ? 14.0 : 20.0;

            return SingleChildScrollView(
              padding: EdgeInsets.fromLTRB(
                  paddingHorizontal, 16, paddingHorizontal, 24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _WelcomeBanner(
                    nombre: _nombreEstudiante,
                    rachaDias: _rachaDias,
                  ),
                  const SizedBox(height: 20),
                  DuoButton(
                    label: 'Continuar Ruta: ${_rutaActual.codigo}',
                    icon: Icons.play_arrow_rounded,
                    color: AppColors.primaryGreen,
                    shadowColor: AppColors.primaryGreenDark,
                    height: 62,
                    width: double.infinity,
                    onPressed: () => _abrirNormativa(context, _rutaActual),
                  ),
                  const SizedBox(height: 32),
                  Text(
                    'Explora las normas ISO',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 4),
                  const Text(
                    'Las más utilizadas en la industria del software',
                    style: TextStyle(color: AppColors.textGrey, fontSize: 13),
                  ),
                  const SizedBox(height: 16),
                  _NormativasCarousel(
                    normativas: _normativas,
                    anchoPantalla: anchoPantalla,
                    onSelect: (n) => _abrirNormativa(context, n),
                  ),
                ],
              ),
            );
          },
        ),
      ),
    );
  }
}

/// Banner de bienvenida motivacional con racha en llamas.
class _WelcomeBanner extends StatelessWidget {
  final String nombre;
  final int rachaDias;

  const _WelcomeBanner({required this.nombre, required this.rachaDias});

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final compacto = constraints.maxWidth < 340;

        return Container(
          width: double.infinity,
          padding: EdgeInsets.all(compacto ? 16 : 22),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [AppColors.primaryGreen, AppColors.electricBlue],
            ),
            borderRadius: BorderRadius.circular(28),
            boxShadow: [
              BoxShadow(
                color: AppColors.primaryGreenDark.withValues(alpha: 0.5),
                blurRadius: 16,
                offset: const Offset(0, 8),
              ),
            ],
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      '¡Hola de nuevo, $nombre!',
                      style: TextStyle(
                        fontSize: compacto ? 18 : 21,
                        fontWeight: FontWeight.w800,
                        color: Colors.white,
                        height: 1.15,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'Tu racha está en fuego 🔥 ¡Sigue así!',
                      style: TextStyle(
                        fontSize: compacto ? 13 : 14.5,
                        color: Colors.white.withValues(alpha: 0.5),
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 14),
                    Wrap(
                      spacing: 10,
                      runSpacing: 8,
                      children: [
                        StatChip(
                          icon: Icons.local_fire_department_rounded,
                          value: '$rachaDias días',
                          color: AppColors.red,
                        ),
                        const StatChip(
                          icon: Icons.bolt_rounded,
                          value: '340 XP',
                          color: AppColors.gold,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.5),
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  Icons.local_fire_department_rounded,
                  color: Colors.white,
                  size: compacto ? 30 : 38,
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

/// Carrusel horizontal de tarjetas de normas ISO. El ancho de cada
/// tarjeta se calcula en función del ancho de pantalla disponible
/// para que se vea bien tanto en celulares pequeños como en tablets.
class _NormativasCarousel extends StatelessWidget {
  final List<Normativa> normativas;
  final double anchoPantalla;
  final ValueChanged<Normativa> onSelect;

  const _NormativasCarousel({
    required this.normativas,
    required this.anchoPantalla,
    required this.onSelect,
  });

  @override
  Widget build(BuildContext context) {
    final anchoTarjeta = (anchoPantalla * 0.62).clamp(200.0, 260.0);

    return SizedBox(
      height: 196,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        clipBehavior: Clip.none,
        itemCount: normativas.length,
        separatorBuilder: (_, _) => const SizedBox(width: 14),
        itemBuilder: (context, index) {
          final normativa = normativas[index];
          return SizedBox(
            width: anchoTarjeta,
            child: _NormativaCard(
              normativa: normativa,
              onTap: () => onSelect(normativa),
            ),
          );
        },
      ),
    );
  }
}

class _NormativaCard extends StatelessWidget {
  final Normativa normativa;
  final VoidCallback onTap;

  const _NormativaCard({required this.normativa, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppColors.surface,
      borderRadius: BorderRadius.circular(22),
      child: InkWell(
        borderRadius: BorderRadius.circular(22),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(22),
            border: Border.all(color: AppColors.border, width: 1.5),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.5),
                blurRadius: 10,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: normativa.color.withValues(alpha: 0.5),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Icon(normativa.icono, color: normativa.color, size: 22),
              ),
              const SizedBox(height: 12),
              Text(
                normativa.codigo,
                style: const TextStyle(
                  fontWeight: FontWeight.w800,
                  fontSize: 14,
                  color: AppColors.textDark,
                ),
              ),
              const SizedBox(height: 4),
              Expanded(
                child: Text(
                  normativa.titulo,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 11.5, color: AppColors.textGrey),
                ),
              ),
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: LinearProgressIndicator(
                  value: normativa.progreso / 100,
                  minHeight: 7,
                  backgroundColor: AppColors.border,
                  valueColor: AlwaysStoppedAnimation(normativa.color),
                ),
              ),
              const SizedBox(height: 4),
              Text(
                '${normativa.progreso}% · ${normativa.nivel}',
                style: const TextStyle(fontSize: 10.5, color: AppColors.textGrey),
              ),
            ],
          ),
        ),
      ),
    );
  }
}