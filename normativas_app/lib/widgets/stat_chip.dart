import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

/// Chip compacto tipo "pill" para mostrar racha, XP, etc.
class StatChip extends StatelessWidget {
  final IconData icon;
  final String value;
  final Color color;

  const StatChip({
    super.key,
    required this.icon,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppRadius.chip),
        border: Border.all(color: AppColors.border, width: 2),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, color: color, size: 18),
          const SizedBox(width: 6),
          Text(
            value,
            style: const TextStyle(
              fontWeight: FontWeight.w800,
              color: AppColors.textDark,
              fontSize: 14,
            ),
          ),
        ],
      ),
    );
  }
}