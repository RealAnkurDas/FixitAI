import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import '../models/post_model.dart';

class PostService {
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;
  final FirebaseAuth _auth = FirebaseAuth.instance;

  // Save a post
  Future<void> savePost(String postId) async {
    try {
      final userId = _auth.currentUser?.uid;
      if (userId == null) throw Exception('User not authenticated');

      // Get the current post
      final postDoc = await _firestore.collection('posts').doc(postId).get();
      if (!postDoc.exists) throw Exception('Post not found');

      final postData = postDoc.data()!;
      final savedBy = List<String>.from(postData['savedBy'] ?? []);

      // Add user to savedBy if not already there
      if (!savedBy.contains(userId)) {
        savedBy.add(userId);
        await _firestore.collection('posts').doc(postId).update({
          'savedBy': savedBy,
        });
      }
    } catch (e) {
      throw Exception('Failed to save post: $e');
    }
  }

  // Unsave a post
  Future<void> unsavePost(String postId) async {
    try {
      final userId = _auth.currentUser?.uid;
      if (userId == null) throw Exception('User not authenticated');

      // Get the current post
      final postDoc = await _firestore.collection('posts').doc(postId).get();
      if (!postDoc.exists) throw Exception('Post not found');

      final postData = postDoc.data()!;
      final savedBy = List<String>.from(postData['savedBy'] ?? []);

      // Remove user from savedBy if present
      if (savedBy.contains(userId)) {
        savedBy.remove(userId);
        await _firestore.collection('posts').doc(postId).update({
          'savedBy': savedBy,
        });
      }
    } catch (e) {
      throw Exception('Failed to unsave post: $e');
    }
  }

  // Check if a post is saved by current user
  Future<bool> isPostSaved(String postId) async {
    try {
      final userId = _auth.currentUser?.uid;
      if (userId == null) return false;

      final postDoc = await _firestore.collection('posts').doc(postId).get();
      if (!postDoc.exists) return false;

      final postData = postDoc.data()!;
      final savedBy = List<String>.from(postData['savedBy'] ?? []);
      return savedBy.contains(userId);
    } catch (e) {
      return false;
    }
  }

  // Get saved posts for current user
  Stream<List<PostModel>> getSavedPosts() {
    final userId = _auth.currentUser?.uid;
    if (userId == null) return Stream.value([]);

    return _firestore
        .collection('posts')
        .where('savedBy', arrayContains: userId)
        .snapshots()
        .map((snapshot) {
          final docs = snapshot.docs
              .map((doc) => PostModel.fromMap({...doc.data(), 'id': doc.id}))
              .toList();
          // Sort by createdAt descending locally to avoid index requirement
          docs.sort((a, b) => b.createdAt.compareTo(a.createdAt));
          return docs;
        });
  }

  // Get posts by user
  Stream<List<PostModel>> getUserPosts(String userId) {
    return _firestore
        .collection('posts')
        .where('userId', isEqualTo: userId)
        .snapshots()
        .map((snapshot) {
          final docs = snapshot.docs
              .map((doc) => PostModel.fromMap({...doc.data(), 'id': doc.id}))
              .toList();
          // Sort by createdAt descending locally to avoid index requirement
          docs.sort((a, b) => b.createdAt.compareTo(a.createdAt));
          return docs;
        });
  }

  // Get all posts
  Stream<List<PostModel>> getAllPosts() {
    return _firestore
        .collection('posts')
        .snapshots()
        .map((snapshot) {
          final docs = snapshot.docs
              .map((doc) => PostModel.fromMap({...doc.data(), 'id': doc.id}))
              .toList();
          // Sort by createdAt descending locally to avoid index requirement
          docs.sort((a, b) => b.createdAt.compareTo(a.createdAt));
          return docs;
        });
  }
}
