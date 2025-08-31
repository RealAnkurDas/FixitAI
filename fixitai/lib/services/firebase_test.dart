import 'dart:io';
import 'package:firebase_storage/firebase_storage.dart';
import 'package:cloud_firestore/cloud_firestore.dart';

class FirebaseTest {
  static final FirebaseStorage _storage = FirebaseStorage.instance;
  static final FirebaseFirestore _firestore = FirebaseFirestore.instance;

  // Test Firebase Storage connectivity
  static Future<bool> testStorageConnection() async {
    try {
      print('Testing Firebase Storage connection...');
      
      // Try to list files in root (this should work even if empty)
      final result = await _storage.ref().listAll();
      print('Storage connection successful. Found ${result.items.length} items in root.');
      return true;
    } catch (e) {
      print('Storage connection failed: $e');
      return false;
    }
  }

  // Test Firestore connectivity
  static Future<bool> testFirestoreConnection() async {
    try {
      print('Testing Firestore connection...');
      
      // Try to get a document that doesn't exist (should not throw)
      final doc = await _firestore.collection('test').doc('test').get();
      print('Firestore connection successful.');
      return true;
    } catch (e) {
      print('Firestore connection failed: $e');
      return false;
    }
  }

  // Test network connectivity
  static Future<bool> testNetworkConnection() async {
    try {
      print('Testing network connection...');
      
      final result = await InternetAddress.lookup('google.com');
      final isConnected = result.isNotEmpty && result[0].rawAddress.isNotEmpty;
      print('Network connection: ${isConnected ? 'OK' : 'Failed'}');
      return isConnected;
    } on SocketException catch (e) {
      print('Network connection failed: $e');
      return false;
    }
  }

  // Run all tests
  static Future<Map<String, bool>> runAllTests() async {
    print('=== Firebase Connection Tests ===');
    
    final results = <String, bool>{};
    
    results['network'] = await testNetworkConnection();
    results['firestore'] = await testFirestoreConnection();
    results['storage'] = await testStorageConnection();
    
    print('=== Test Results ===');
    results.forEach((test, result) {
      print('$test: ${result ? 'PASS' : 'FAIL'}');
    });
    
    return results;
  }
}
