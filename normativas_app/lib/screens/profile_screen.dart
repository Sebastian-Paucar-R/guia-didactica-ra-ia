import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  static const String _nombreCompleto = 'Erik Daniel Yuquilema Galarraga';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Perfil')),
      body: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) {
            final anchoPantalla = constraints.maxWidth;
            // Responsive: 2 columnas en celulares, 3-4 en pantallas más anchas.
            final columnas = anchoPantalla < 420
                ? 2
                : anchoPantalla < 800
                    ? 3
                    : 4;

            return ListView(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
              children: [
                _ProfileHeader(nombre: _nombreCompleto),
                const SizedBox(height: 28),
                Text('Tu progreso', style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 14),
                GridView.count(
                  crossAxisCount: columnas,
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  crossAxisSpacing: 14,
                  mainAxisSpacing: 14,
                  childAspectRatio: 1.05,
                  children: const [
                    _StatCard(
                      icon: Icons.local_fire_department_rounded,
                      label: 'Racha',
                      value: '12 días',
                      color: AppColors.red,
                    ),
                    _StatCard(
                      icon: Icons.military_tech_rounded,
                      label: 'Medallas',
                      value: '7',
                      color: AppColors.gold,
                    ),
                    _StatCard(
                      icon: Icons.trending_up_rounded,
                      label: 'Nivel',
                      value: 'Intermedio',
                      color: AppColors.electricBlue,
                    ),
                    _StatCard(
                      icon: Icons.bolt_rounded,
                      label: 'XP Total',
                      value: '340',
                      color: AppColors.deepPurple,
                    ),
                  ],
                ),
                const SizedBox(height: 28),
                Text('Configuración', style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 12),
                const _SettingsList(
                  items: [
                    _SettingItem(Icons.notifications_rounded, 'Notificaciones', 'Activadas'),
                    _SettingItem(Icons.dark_mode_rounded, 'Tema', 'Claro'),
                    _SettingItem(Icons.language_rounded, 'Idioma', 'Español'),
                  ],
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

/// Encabezado del perfil: avatar, nombre completo y rol.
class _ProfileHeader extends StatelessWidget {
  final String nombre;
  const _ProfileHeader({required this.nombre});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 26, horizontal: 20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [AppColors.deepPurple, AppColors.electricBlue],
        ),
        borderRadius: BorderRadius.circular(26),
        boxShadow: [
          BoxShadow(
            color: AppColors.deepPurpleDark.withValues(alpha:0.3),
            blurRadius: 16,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        children: [
          const CircleAvatar(
            radius: 40,
            backgroundColor: Colors.white,
            child: Icon(Icons.person_rounded, color: AppColors.deepPurple, size: 46),
          ),
          const SizedBox(height: 14),
          Text(
            nombre,
            textAlign: TextAlign.center,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w800,
              color: Colors.white,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            'Estudiante de Ingeniería de Software',
            style: TextStyle(fontSize: 12.5, color: Colors.white.withValues(alpha:0.9)),
          ),
        ],
      ),
    );
  }
}

/// Tarjeta de estadística individual (racha, medallas, nivel, XP).
class _StatCard extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final Color color;

  const _StatCard({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.border, width: 1.5),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha:0.05),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: color.withValues(alpha:0.15),
              shape: BoxShape.circle,
            ),
            child: Icon(icon, color: color, size: 22),
          ),
          const SizedBox(height: 10),
          FittedBox(
            child: Text(
              value,
              style: const TextStyle(
                fontWeight: FontWeight.w800,
                fontSize: 15,
                color: AppColors.textDark,
              ),
            ),
          ),
          const SizedBox(height: 2),
          Text(
            label,
            style: const TextStyle(fontSize: 11.5, color: AppColors.textGrey),
          ),
        ],
      ),
    );
  }
}

class _SettingItem {
  final IconData icono;
  final String etiqueta;
  final String valor;
  const _SettingItem(this.icono, this.etiqueta, this.valor);
}

class _SettingsList extends StatelessWidget {
  final List<_SettingItem> items;
  const _SettingsList({required this.items});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.border, width: 1.5),
      ),
      child: Column(
        children: [
          for (int i = 0; i < items.length; i++) ...[
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
              child: Row(
                children: [
                  Icon(items[i].icono, color: AppColors.deepPurple, size: 20),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Text(
                      items[i].etiqueta,
                      style: const TextStyle(
                        fontWeight: FontWeight.w700,
                        fontSize: 13,
                        color: AppColors.textDark,
                      ),
                    ),
                  ),
                  Text(
                    items[i].valor,
                    style: const TextStyle(fontSize: 12, color: AppColors.textGrey),
                  ),
                ],
              ),
            ),
            if (i != items.length - 1)
              const Divider(height: 1, color: AppColors.border),
          ],
        ],
      ),
    );
  }
}