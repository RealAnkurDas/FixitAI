import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'screens/auth_screen.dart';
import 'utils/app_colors.dart';

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
