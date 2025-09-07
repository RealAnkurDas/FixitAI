/**
 * FixitAI Flutter Application
 * 
 * Main entry point for the FixitAI mobile application.
 * 
 * Architecture:
 * - Firebase Authentication for user management
 * - Material Design UI with custom color scheme
 * - Multi-screen navigation for repair assistance workflow
 * 
 * Key Features:
 * - User authentication and profile management
 * - Image capture and upload for repair analysis
 * - Multi-agent conversation interface
 * - Local repair shop discovery
 * - Social features for sharing repair experiences
 * - Creative upcycling suggestions
 */

import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'screens/auth_screen.dart';
import 'utils/app_colors.dart';
import 'widgets/fixitai_logo.dart';

Future<void> main() async {

  WidgetsFlutterBinding.ensureInitialized();

  await Firebase.initializeApp();

  runApp(const FixitAIApp());
}

class FixitAIApp extends StatelessWidget {
  const FixitAIApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'FixitAI',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        primarySwatch: Colors.blue,
        primaryColor: AppColors.primary,
        scaffoldBackgroundColor: AppColors.background,
        fontFamily: 'Inter',
        textTheme: const TextTheme(
          headlineLarge: TextStyle(
            fontWeight: FontWeight.bold,
            color: AppColors.text,
          ),
          headlineMedium: TextStyle(
            fontWeight: FontWeight.bold,
            color: AppColors.text,
          ),
          bodyLarge: TextStyle(
            fontWeight: FontWeight.w500,
            color: AppColors.text,
          ),
          bodyMedium: TextStyle(
            fontWeight: FontWeight.w500,
            color: AppColors.text,
          ),
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: AppColors.primary,
            foregroundColor: Colors.white,
            textStyle: const TextStyle(
              fontWeight: FontWeight.bold,
            ),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
            padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 24),
          ),
        ),
      ),
      home: const AuthScreen(),
    );
  }
}
