import 'package:flutter/material.dart';

/// Paleta de colores inspirada en Duolingo, con un giro "tech"
/// (verde brillante + morado/azul eléctrico para la temática de software).
class AppColors {
  AppColors._();

  // Verde principal (acción / avanzar)
  static const Color primaryGreen = Color(0xFF58CC02);
  static const Color primaryGreenDark = Color(0xFF48A302); // sombra 3D

  // Azul eléctrico (IA / tecnología)
  static const Color electricBlue = Color(0xFF1CB0F6);
  static const Color electricBlueDark = Color(0xFF1899D6);

  // Morado oscuro (normativas / branding secundario)
  static const Color deepPurple = Color(0xFF7C4DFF);
  static const Color deepPurpleDark = Color(0xFF5E35D6);

  // Amarillo (gamificación: XP, rachas)
  static const Color gold = Color(0xFFFFC800);

  // Rojo (alertas / vidas)
  static const Color red = Color(0xFFFF4B4B);

  // Neutros
  static const Color background = Color(0xFFF7F9FC);
  static const Color surface = Colors.white;
  static const Color textDark = Color(0xFF3C3C4E);
  static const Color textGrey = Color(0xFF9A9AAE);
  static const Color border = Color(0xFFE5E5EF);
}

class AppRadius {
  AppRadius._();
  static const double button = 20.0;
  static const double field = 24.0;
  static const double chip = 16.0;
  static const double bubble = 22.0;
}

class AppTheme {
  AppTheme._();

  static ThemeData get light {
    return ThemeData(
      useMaterial3: true,
      scaffoldBackgroundColor: AppColors.background,
      fontFamily: 'Baloo2', // fuente redondeada estilo Duolingo (fallback a system si no está embebida)
      colorScheme: ColorScheme.fromSeed(
        seedColor: AppColors.primaryGreen,
        primary: AppColors.primaryGreen,
        secondary: AppColors.electricBlue,
        tertiary: AppColors.deepPurple,
        surface: AppColors.surface,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: AppColors.background,
        elevation: 0,
        centerTitle: true,
        foregroundColor: AppColors.textDark,
        titleTextStyle: TextStyle(
          color: AppColors.textDark,
          fontSize: 20,
          fontWeight: FontWeight.w800,
        ),
      ),
      textTheme: const TextTheme(
        headlineMedium: TextStyle(
          fontWeight: FontWeight.w800,
          color: AppColors.textDark,
        ),
        titleLarge: TextStyle(
          fontWeight: FontWeight.w800,
          color: AppColors.textDark,
        ),
        bodyMedium: TextStyle(
          color: AppColors.textDark,
          fontWeight: FontWeight.w500,
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.surface,
        contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.field),
          borderSide: const BorderSide(color: AppColors.border, width: 2),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.field),
          borderSide: const BorderSide(color: AppColors.border, width: 2),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.field),
          borderSide: const BorderSide(color: AppColors.electricBlue, width: 2),
        ),
      ),
    );
  }
}