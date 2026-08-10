import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

/// Barra de navegación inferior estilo Duolingo: esquinas superiores
/// redondeadas, sombra suave, y una pestaña central (Escáner AR)
/// destacada con un botón circular en el color primario de la app.
class AppBottomNavBar extends StatelessWidget {
  final int currentIndex;
  final ValueChanged<int> onTap;

  const AppBottomNavBar({
    super.key,
    required this.currentIndex,
    required this.onTap,
  });

  static const List<_NavItemData> _items = [
    _NavItemData(icon: Icons.home_rounded, label: 'Inicio'),
    _NavItemData(icon: Icons.smart_toy_rounded, label: 'Tutor IA'),
    _NavItemData(icon: Icons.view_in_ar_rounded, label: 'Escáner AR'),
    _NavItemData(icon: Icons.person_rounded, label: 'Perfil'),
  ];

  static const int _arIndex = 2;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(28),
          topRight: Radius.circular(28),
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha:0.08),
            blurRadius: 20,
            offset: const Offset(0, -4),
          ),
        ],
      ),
      child: SafeArea(
        top: false,
        child: SizedBox(
          height: 72,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: List.generate(_items.length, (index) {
              final data = _items[index];
              final seleccionado = index == currentIndex;

              if (index == _arIndex) {
                return _ArNavItem(
                  data: data,
                  seleccionado: seleccionado,
                  onTap: () => onTap(index),
                );
              }

              return _NavItem(
                data: data,
                seleccionado: seleccionado,
                onTap: () => onTap(index),
              );
            }),
          ),
        ),
      ),
    );
  }
}

class _NavItemData {
  final IconData icon;
  final String label;
  const _NavItemData({required this.icon, required this.label});
}

/// Ítem estándar de la barra (Inicio, Tutor IA, Perfil).
class _NavItem extends StatelessWidget {
  final _NavItemData data;
  final bool seleccionado;
  final VoidCallback onTap;

  const _NavItem({
    required this.data,
    required this.seleccionado,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final color = seleccionado ? AppColors.primaryGreen : AppColors.textGrey;

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(data.icon, color: color, size: 24),
            const SizedBox(height: 4),
            Text(
              data.label,
              style: TextStyle(
                color: color,
                fontSize: 11,
                fontWeight: seleccionado ? FontWeight.w800 : FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Ítem destacado del Escáner AR: círculo elevado en el color primario,
/// más grande que el resto para llamar la atención de inmediato.
class _ArNavItem extends StatelessWidget {
  final _NavItemData data;
  final bool seleccionado;
  final VoidCallback onTap;

  const _ArNavItem({
    required this.data,
    required this.seleccionado,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final bgColor = seleccionado ? AppColors.deepPurple : AppColors.primaryGreen;
    final shadowColor =
        seleccionado ? AppColors.deepPurpleDark : AppColors.primaryGreenDark;

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(30),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 6),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Transform.translate(
              offset: const Offset(0, -14),
              child: Container(
                width: 54,
                height: 54,
                decoration: BoxDecoration(
                  color: bgColor,
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(color: shadowColor, offset: const Offset(0, 4)),
                  ],
                ),
                child: Icon(data.icon, color: Colors.white, size: 28),
              ),
            ),
            Transform.translate(
              offset: const Offset(0, -8),
              child: Text(
                data.label,
                style: TextStyle(
                  color: bgColor,
                  fontSize: 11,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}