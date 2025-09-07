import 'package:flutter/material.dart';

/**
 * FIXiTAI Logo Widget
 * 
 * Simple logo widget that displays the FIXiTAI logo from AppLogo.png
 */

class FixitaiLogo extends StatelessWidget {
  final double? width;
  final double? height;
  final bool showText;
  final double textSize;
  final Color? backgroundColor;
  final EdgeInsets? padding;

  const FixitaiLogo({
    super.key,
    this.width,
    this.height,
    this.showText = true,
    this.textSize = 24,
    this.backgroundColor,
    this.padding,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: width,
      height: height,
      padding: padding ?? const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: backgroundColor ?? const Color(0xFF191970), // Midnight blue
        borderRadius: BorderRadius.circular(12),
      ),
      child: Image.asset(
        'assets/AppLogo.png',
        width: width != null ? width! - 32 : 60,
        height: height != null ? height! - 32 : 60,
        fit: BoxFit.contain,
      ),
    );
  }

}