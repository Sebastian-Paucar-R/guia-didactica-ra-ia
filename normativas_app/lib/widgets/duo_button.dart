import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

/// Botón con efecto "clickable" 3D: un bloque de color sólido debajo
/// simula elevación plana. Al presionar, el botón se desplaza hacia
/// la sombra, dando la sensación táctil característica de Duolingo.
class DuoButton extends StatefulWidget {
  final String label;
  final IconData? icon;
  final Color color;
  final Color shadowColor;
  final Color textColor;
  final VoidCallback onPressed;
  final double height;
  final double? width;

  const DuoButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.icon,
    this.color = AppColors.primaryGreen,
    this.shadowColor = AppColors.primaryGreenDark,
    this.textColor = Colors.white,
    this.height = 56,
    this.width,
  });

  @override
  State<DuoButton> createState() => _DuoButtonState();
}

class _DuoButtonState extends State<DuoButton> {
  bool _pressed = false;
  static const double _shadowDepth = 5.0;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTapDown: (_) => setState(() => _pressed = true),
      onTapUp: (_) {
        setState(() => _pressed = false);
        widget.onPressed();
      },
      onTapCancel: () => setState(() => _pressed = false),
      child: SizedBox(
        width: widget.width,
        height: widget.height + _shadowDepth,
        child: Stack(
          children: [
            // Capa de sombra sólida (base fija)
            Positioned.fill(
              top: _shadowDepth,
              child: DecoratedBox(
                decoration: BoxDecoration(
                  color: widget.shadowColor,
                  borderRadius: BorderRadius.circular(AppRadius.button),
                ),
              ),
            ),
            // Capa superior animada (se hunde al presionar)
            AnimatedPositioned(
              duration: const Duration(milliseconds: 80),
              curve: Curves.easeOut,
              top: _pressed ? _shadowDepth : 0,
              left: 0,
              right: 0,
              height: widget.height,
              child: DecoratedBox(
                decoration: BoxDecoration(
                  color: widget.color,
                  borderRadius: BorderRadius.circular(AppRadius.button),
                ),
                child: Center(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 14),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        if (widget.icon != null) ...[
                          Icon(widget.icon, color: widget.textColor, size: 20),
                          const SizedBox(width: 8),
                        ],
                        Flexible(
                          child: Text(
                            widget.label,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              color: widget.textColor,
                              fontWeight: FontWeight.w800,
                              fontSize: 16,
                              letterSpacing: 0.5,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}