import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../widgets/duo_button.dart';

class ArScannerScreen extends StatelessWidget {
  const ArScannerScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Escáner AR')),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 32),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                width: 140,
                height: 140,
                decoration: BoxDecoration(
                  color: AppColors.deepPurple.withValues(alpha: 0.5),
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.view_in_ar_rounded,
                  color: AppColors.deepPurple,
                  size: 64,
                ),
              ),
              const SizedBox(height: 28),
              const Text(
                'Visualiza modelos 3D en tu entorno',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.w800,
                  color: AppColors.textDark,
                ),
              ),
              const SizedBox(height: 10),
              const Text(
                'Apunta tu cámara hacia una superficie plana para explorar '
                'diagramas y componentes de las normas ISO en realidad '
                'aumentada.',
                textAlign: TextAlign.center,
                style: TextStyle(color: AppColors.textGrey, fontSize: 14, height: 1.4),
              ),
              const SizedBox(height: 32),
              DuoButton(
                label: 'Activar cámara',
                icon: Icons.camera_alt_rounded,
                color: AppColors.deepPurple,
                shadowColor: AppColors.deepPurpleDark,
                width: double.infinity,
                onPressed: () {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('Función de cámara AR próximamente'),
                      behavior: SnackBarBehavior.floating,
                      backgroundColor: AppColors.deepPurple,
                    ),
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}