import 'package:flutter/material.dart';
import 'screens/main_scaffold.dart';
import 'theme/app_theme.dart';

void main() {
  runApp(const NormativasApp());
}

class NormativasApp extends StatelessWidget {
  const NormativasApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Normativas SW',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      home: const MainScaffold(),
    );
  }
}