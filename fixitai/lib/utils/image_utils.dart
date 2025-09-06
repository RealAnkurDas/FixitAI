import 'dart:io';
import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';

class ImageUtils {
  /// Creates an appropriate image provider for both local files and network URLs
  static ImageProvider? getImageProvider(String? imagePath) {
    if (imagePath == null || imagePath.isEmpty) {
      print('DEBUG: ImageUtils - No image path provided');
      return null;
    }
    
    print('DEBUG: ImageUtils - Processing image path: $imagePath');
    
    // Check if it's a network URL
    if (imagePath.startsWith('http://') || imagePath.startsWith('https://')) {
      print('DEBUG: ImageUtils - Using network image provider');
      return CachedNetworkImageProvider(imagePath);
    }
    
    // Check if it's a local file path
    if (imagePath.startsWith('/') || imagePath.startsWith('file://')) {
      try {
        final cleanPath = imagePath.replaceFirst('file://', '');
        final file = File(cleanPath);
        print('DEBUG: ImageUtils - Checking local file: $cleanPath');
        if (file.existsSync()) {
          print('DEBUG: ImageUtils - Local file exists, using FileImage');
          return FileImage(file);
        } else {
          print('DEBUG: ImageUtils - Local file does not exist: $cleanPath');
        }
      } catch (e) {
        print('DEBUG: ImageUtils - Error loading local image: $e');
      }
    }
    
    print('DEBUG: ImageUtils - No valid image provider found');
    return null;
  }
  
  /// Creates a CircleAvatar that can handle both local files and network URLs
  static Widget createAvatar({
    required String? imagePath,
    required String? displayName,
    double radius = 20,
    Color? backgroundColor,
    Color? textColor,
    double? fontSize,
  }) {
    final imageProvider = getImageProvider(imagePath);
    
    return CircleAvatar(
      radius: radius,
      backgroundColor: backgroundColor ?? Colors.grey[300],
      backgroundImage: imageProvider,
      child: imageProvider == null
          ? Text(
              displayName?.isNotEmpty == true
                  ? displayName![0].toUpperCase()
                  : 'U',
              style: TextStyle(
                fontWeight: FontWeight.bold,
                color: textColor ?? Colors.grey[700],
                fontSize: fontSize ?? radius * 0.6,
              ),
            )
          : null,
    );
  }
}
