import 'package:flutter/material.dart';
import '../widgets/app_bottom_nav.dart';
import 'ar_scanner_screen.dart';
import 'chat_screen.dart';
import 'home_screen.dart';
import 'profile_screen.dart';

/// Contenedor principal de la app: mantiene las 4 pestañas vivas con
/// [IndexedStack] (para no perder el progreso del chat al navegar) y
/// muestra la barra de navegación inferior personalizada.
class MainScaffold extends StatefulWidget {
  const MainScaffold({super.key});

  @override
  State<MainScaffold> createState() => _MainScaffoldState();
}

class _MainScaffoldState extends State<MainScaffold> {
  int _index = 0;

  static const List<Widget> _tabs = [
    HomeScreen(),
    ChatScreen(),
    ArScannerScreen(),
    ProfileScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(index: _index, children: _tabs),
      bottomNavigationBar: AppBottomNavBar(
        currentIndex: _index,
        onTap: (i) => setState(() => _index = i),
      ),
    );
  }
}