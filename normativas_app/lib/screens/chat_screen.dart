import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

// Modelo básico para los mensajes
class ChatMessage {
  final String text;
  final bool isUser;
  ChatMessage({required this.text, required this.isUser});
}

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final TextEditingController _controller = TextEditingController();
  final List<ChatMessage> _messages = [];
  bool _isLoading = false;

  Future<void> sendMessage(String text) async {
    if (text.trim().isEmpty) return;

    // 1. Mostrar el mensaje del usuario en pantalla
    setState(() {
      _messages.add(ChatMessage(text: text, isUser: true));
      _isLoading = true;
    });
    _controller.clear();

    // 2. Definir la URL (Usa 127.0.0.1 si pruebas en navegador Chrome web, o 10.0.2.2 si usas emulador Android)
    final url = Uri.parse('http://127.0.0.1:8000/api/v1/chat');

    try {
      // 3. Enviar la petición POST con la etiqueta "message"
      final response = await http.post(
        url,
        headers: {"Content-Type": "application/json"},
        body: json.encode({"message": text}),
      );

      // 4. Recibir y mostrar la respuesta
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        setState(() {
          _messages.add(ChatMessage(text: data["response"], isUser: false));
        });
      } else {
        setState(() {
          _messages.add(ChatMessage(text: "Error de servidor: ${response.statusCode}", isUser: false));
        });
      }
    } catch (e) {
      setState(() {
        _messages.add(ChatMessage(text: "Error de conexión. ¿Está encendido el servidor?", isUser: false));
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Tutor IA", style: TextStyle(fontWeight: FontWeight.bold)),
        backgroundColor: Colors.white,
        elevation: 0,
        centerTitle: true,
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: _messages.length,
              itemBuilder: (context, index) {
                final msg = _messages[index];
                return Align(
                  alignment: msg.isUser ? Alignment.centerRight : Alignment.centerLeft,
                  child: Container(
                    margin: const EdgeInsets.only(bottom: 12),
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    decoration: BoxDecoration(
                      color: msg.isUser ? Colors.green.shade500 : Colors.grey.shade200,
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      msg.text,
                      style: TextStyle(
                        color: msg.isUser ? Colors.white : Colors.black87,
                        fontSize: 16,
                      ),
                    ),
                  ),
                );
              },
            ),
          ),
          if (_isLoading)
            const Padding(
              padding: EdgeInsets.all(8.0),
              child: CircularProgressIndicator(color: Colors.green),
            ),
          _buildInputArea(),
        ],
      ),
    );
  }

  Widget _buildInputArea() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: Colors.white,
        boxShadow: [
          BoxShadow(
            color: Colors.grey.shade200,
            blurRadius: 10,
            offset: const Offset(0, -2),
          )
        ],
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _controller,
              decoration: InputDecoration(
                hintText: "Pregúntale al tutor IA...",
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(30),
                  borderSide: BorderSide.none,
                ),
                filled: true,
                fillColor: Colors.grey.shade100,
                contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                // Ícono del Escáner AR
                suffixIcon: IconButton(
                  icon: const Icon(Icons.view_in_ar_rounded, color: Colors.deepPurpleAccent),
                  onPressed: () {
                    // Aquí irá la lógica de la cámara AR más adelante
                  },
                ),
              ),
              onSubmitted: (value) => sendMessage(value),
            ),
          ),
          const SizedBox(width: 8),
          CircleAvatar(
            backgroundColor: Colors.green,
            radius: 24,
            child: IconButton(
              icon: const Icon(Icons.send_rounded, color: Colors.white),
              onPressed: () => sendMessage(_controller.text),
            ),
          ),
        ],
      ),
    );
  }
}