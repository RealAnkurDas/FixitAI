import 'package:flutter/material.dart';
import '../utils/app_colors.dart';

class DifficultyBadge extends StatelessWidget {
  final String difficulty;

  const DifficultyBadge({
    super.key,
    required this.difficulty,
  });

  @override
  Widget build(BuildContext context) {
    Color backgroundColor;
    Color textColor = Colors.white;

    switch (difficulty.toLowerCase()) {
      case 'easy':
        backgroundColor = AppColors.secondary;
        break;
      case 'medium':
        backgroundColor = AppColors.accent;
        textColor = AppColors.text;
        break;
      case 'hard':
        backgroundColor = Colors.red;
        break;
      default:
        backgroundColor = AppColors.primary;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: backgroundColor,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Text(
        difficulty,
        style: TextStyle(
          color: textColor,
          fontSize: 12,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }
}
