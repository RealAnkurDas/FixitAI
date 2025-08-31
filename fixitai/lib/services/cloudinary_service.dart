import 'dart:io';
import 'dart:convert';
import 'package:crypto/crypto.dart';
import 'package:http/http.dart' as http;
import 'package:cloudinary_public/cloudinary_public.dart';

class CloudinaryService {
  // Replace these with your actual Cloudinary credentials
  static const String _cloudName = 'dkvxiysme'; // Replace with your cloud name
  static const String _apiKey = '556969932191651'; // Replace with your API key
  static const String _apiSecret = 'owRuBRyid1krsY5knC6ILqRwQQQ'; // Replace with your API secret
  
  static final CloudinaryPublic _cloudinary = CloudinaryPublic(
    _cloudName,
    'fixitai', // Upload preset name
    cache: false,
  );

  // Upload image to Cloudinary
  static Future<String?> uploadImage(File imageFile, String folder) async {
    try {
      print('Uploading image to Cloudinary...');
      
      final response = await _cloudinary.uploadFile(
        CloudinaryFile.fromFile(
          imageFile.path,
          resourceType: CloudinaryResourceType.Image,
          folder: folder,
        ),
      );
      
      print('Image uploaded successfully: ${response.secureUrl}');
      return response.secureUrl;
    } catch (e) {
      print('Cloudinary upload error: $e');
      return null;
    }
  }

  // Upload image with custom transformation
  static Future<String?> uploadImageWithTransformation(
    File imageFile, 
    String folder, 
    {int? width, int? height, String? quality}
  ) async {
    try {
      print('Uploading image to Cloudinary with transformation...');
      
      final response = await _cloudinary.uploadFile(
        CloudinaryFile.fromFile(
          imageFile.path,
          resourceType: CloudinaryResourceType.Image,
          folder: folder,
        ),
      );
      
      print('Image uploaded successfully: ${response.secureUrl}');
      return response.secureUrl;
    } catch (e) {
      print('Cloudinary upload error: $e');
      return null;
    }
  }

  // Delete image from Cloudinary (if needed)
  static Future<bool> deleteImage(String publicId) async {
    try {
      final url = 'https://api.cloudinary.com/v1_1/$_cloudName/image/destroy';
      final timestamp = DateTime.now().millisecondsSinceEpoch ~/ 1000;
      
      final signature = _generateSignature(publicId, timestamp);
      
      final response = await http.post(
        Uri.parse(url),
        body: {
          'public_id': publicId,
          'api_key': _apiKey,
          'timestamp': timestamp.toString(),
          'signature': signature,
        },
      );
      
      if (response.statusCode == 200) {
        print('Image deleted successfully');
        return true;
      } else {
        print('Failed to delete image: ${response.body}');
        return false;
      }
    } catch (e) {
      print('Error deleting image: $e');
      return false;
    }
  }

  // Generate signature for API calls
  static String _generateSignature(String publicId, int timestamp) {
    final params = 'public_id=$publicId&timestamp=$timestamp$_apiSecret';
    final bytes = utf8.encode(params);
    final hash = sha256.convert(bytes);
    return hash.toString();
  }

  // Get optimized image URL
  static String getOptimizedUrl(String originalUrl, {int? width, int? height}) {
    if (!originalUrl.contains('cloudinary.com')) return originalUrl;
    
    final baseUrl = originalUrl.split('/upload/')[0] + '/upload/';
    final imagePath = originalUrl.split('/upload/')[1];
    
    var transformation = 'f_auto,q_auto';
    if (width != null) transformation += ',w_$width';
    if (height != null) transformation += ',h_$height';
    if (width != null && height != null) {
      transformation += ',c_fill';
    } else {
      transformation += ',c_scale';
    }
    
    return '$baseUrl$transformation/$imagePath';
  }
}
