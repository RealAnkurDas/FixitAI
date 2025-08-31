import 'dart:io';
import 'dart:typed_data';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:uuid/uuid.dart';
import 'package:image/image.dart' as img;
import '../models/user_model.dart';
import '../models/post_model.dart';
import '../models/comment_model.dart';
import 'cloudinary_service.dart';

// Add connectivity check
Future<bool> _checkConnectivity() async {
  try {
    final result = await InternetAddress.lookup('google.com');
    return result.isNotEmpty && result[0].rawAddress.isNotEmpty;
  } on SocketException catch (_) {
    return false;
  }
}

class SocialService {
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;
  final FirebaseAuth _auth = FirebaseAuth.instance;
  final Uuid _uuid = const Uuid();

  // User Management
  Future<void> createUserProfile(UserModel user) async {
    await _firestore.collection('users').doc(user.id).set(user.toMap());
  }

  Future<UserModel?> getUserProfile(String userId) async {
    try {
      final doc = await _firestore.collection('users').doc(userId).get();
      if (doc.exists && doc.data() != null) {
        return UserModel.fromMap(doc.data()!);
      }
      return null;
    } catch (e) {
      print('Error getting user profile: $e');
      return null;
    }
  }

  Future<void> updateUserProfile(String userId, Map<String, dynamic> updates) async {
    await _firestore.collection('users').doc(userId).update(updates);
  }

  Future<void> deleteUserProfile(String userId) async {
    await _firestore.collection('users').doc(userId).delete();
  }

  Stream<UserModel?> getUserProfileStream(String userId) {
    return _firestore
        .collection('users')
        .doc(userId)
        .snapshots()
        .map((doc) => doc.exists ? UserModel.fromMap(doc.data()!) : null);
  }

  // Image Upload and Compression
  Future<String?> uploadImage(File imageFile, String folder, String fileName) async {
    try {
      // Check connectivity first
      final isConnected = await _checkConnectivity();
      if (!isConnected) {
        throw Exception('No internet connection. Please check your network and try again.');
      }
      
      // Upload to Cloudinary
      final imageUrl = await CloudinaryService.uploadImage(imageFile, folder);
      
      if (imageUrl != null) {
        print('Image uploaded successfully to Cloudinary: $imageUrl');
        return imageUrl;
      } else {
        throw Exception('Failed to upload image to Cloudinary');
      }
    } catch (e) {
      print('Image upload error: $e');
      if (e.toString().contains('network') || e.toString().contains('connection') || e.toString().contains('internet')) {
        throw Exception('Network error: Please check your internet connection and try again.');
      } else {
        throw Exception('Failed to upload image: $e');
      }
    }
  }

  Future<Uint8List> _compressImage(File imageFile) async {
    final bytes = await imageFile.readAsBytes();
    final image = img.decodeImage(bytes);
    
    if (image == null) throw Exception('Failed to decode image');
    
    // Resize image to max 1024px width while maintaining aspect ratio
    final resized = img.copyResize(
      image,
      width: 1024,
      height: (1024 * image.height / image.width).round(),
    );
    
    // Convert to JPEG with 85% quality
    return Uint8List.fromList(img.encodeJpg(resized, quality: 85));
  }

  // Post Management
  Future<String> createPost(PostModel post, File? imageFile) async {
    String? imageURL;
    
    if (imageFile != null) {
      try {
        final fileName = '${_uuid.v4()}.jpg';
        imageURL = await uploadImage(imageFile, 'post-images/${post.id}', fileName);
      } catch (e) {
        print('Failed to upload image, creating post without image: $e');
        // Continue without image if upload fails
        imageURL = null;
      }
    }

    final postWithImage = PostModel(
      id: post.id,
      userId: post.userId,
      title: post.title,
      description: post.description,
      imageURL: imageURL,
      deviceType: post.deviceType,
      difficulty: post.difficulty,
      timeRequired: post.timeRequired,
      toolsUsed: post.toolsUsed,
      tags: post.tags,
      createdAt: post.createdAt,
    );

    await _firestore.collection('posts').doc(post.id).set(postWithImage.toMap());
    
    // Update user's repair count
    await _firestore.collection('users').doc(post.userId).update({
      'repairCount': FieldValue.increment(1),
    });

    return post.id;
  }

  Stream<List<PostModel>> getPostsStream({int limit = 20}) {
    return _firestore
        .collection('posts')
        .orderBy('createdAt', descending: true)
        .limit(limit)
        .snapshots()
        .map((snapshot) => snapshot.docs
            .map((doc) => PostModel.fromMap(doc.data()))
            .toList());
  }

  Stream<List<PostModel>> getUserPostsStream(String userId, {int limit = 20}) {
    return _firestore
        .collection('posts')
        .where('userId', isEqualTo: userId)
        .orderBy('createdAt', descending: true)
        .limit(limit)
        .snapshots()
        .map((snapshot) => snapshot.docs
            .map((doc) => PostModel.fromMap(doc.data()))
            .toList());
  }

  Future<PostModel?> getPost(String postId) async {
    final doc = await _firestore.collection('posts').doc(postId).get();
    if (doc.exists) {
      return PostModel.fromMap(doc.data()!);
    }
    return null;
  }

  Future<void> deletePost(String postId, String userId) async {
    // Delete post
    await _firestore.collection('posts').doc(postId).delete();
    
    // Delete associated comments
    final commentsSnapshot = await _firestore
        .collection('comments')
        .where('postId', isEqualTo: postId)
        .get();
    
    for (var doc in commentsSnapshot.docs) {
      await doc.reference.delete();
    }
    
    // Update user's repair count
    await _firestore.collection('users').doc(userId).update({
      'repairCount': FieldValue.increment(-1),
    });
  }

  // Like/Unlike Posts
  Future<void> likePost(String postId, String userId) async {
    final postRef = _firestore.collection('posts').doc(postId);
    
    await _firestore.runTransaction((transaction) async {
      final postDoc = await transaction.get(postRef);
      if (!postDoc.exists) return;
      
      final post = PostModel.fromMap(postDoc.data()!);
      final likedBy = List<String>.from(post.likedBy);
      
      if (!likedBy.contains(userId)) {
        likedBy.add(userId);
        transaction.update(postRef, {
          'likedBy': likedBy,
          'likesCount': post.likesCount + 1,
        });
      }
    });
  }

  Future<void> unlikePost(String postId, String userId) async {
    final postRef = _firestore.collection('posts').doc(postId);
    
    await _firestore.runTransaction((transaction) async {
      final postDoc = await transaction.get(postRef);
      if (!postDoc.exists) return;
      
      final post = PostModel.fromMap(postDoc.data()!);
      final likedBy = List<String>.from(post.likedBy);
      
      if (likedBy.contains(userId)) {
        likedBy.remove(userId);
        transaction.update(postRef, {
          'likedBy': likedBy,
          'likesCount': post.likesCount - 1,
        });
      }
    });
  }

  // Comments
  Future<void> addComment(CommentModel comment) async {
    await _firestore.collection('comments').doc(comment.id).set(comment.toMap());
    
    // Update post comment count
    await _firestore.collection('posts').doc(comment.postId).update({
      'commentsCount': FieldValue.increment(1),
    });
  }

  Stream<List<CommentModel>> getPostCommentsStream(String postId) {
    return _firestore
        .collection('comments')
        .where('postId', isEqualTo: postId)
        .orderBy('createdAt', descending: false)
        .snapshots()
        .map((snapshot) => snapshot.docs
            .map((doc) => CommentModel.fromMap(doc.data()))
            .toList())
        .handleError((error) {
          print('Firestore comments query error: $error');
          // Try fallback query without orderBy if index is not ready
          if (error.toString().contains('failed-precondition') || 
              error.toString().contains('requires an index')) {
            print('Trying fallback query without orderBy...');
            return _firestore
                .collection('comments')
                .where('postId', isEqualTo: postId)
                .snapshots()
                .map((snapshot) {
                  final comments = snapshot.docs
                      .map((doc) => CommentModel.fromMap(doc.data()))
                      .toList();
                  // Sort manually
                  comments.sort((a, b) => a.createdAt.compareTo(b.createdAt));
                  return comments;
                });
          }
          // Return empty list on other errors
          return <CommentModel>[];
        });
  }

  Future<void> deleteComment(String commentId, String postId) async {
    await _firestore.collection('comments').doc(commentId).delete();
    
    // Update post comment count
    await _firestore.collection('posts').doc(postId).update({
      'commentsCount': FieldValue.increment(-1),
    });
  }

  // Follow/Unfollow Users
  Future<void> followUser(String followerId, String followingId) async {
    final batch = _firestore.batch();
    
    // Add to follower's following list
    batch.update(
      _firestore.collection('users').doc(followerId),
      {
        'following': FieldValue.arrayUnion([followingId]),
        'followingCount': FieldValue.increment(1),
      },
    );
    
    // Add to following's followers list
    batch.update(
      _firestore.collection('users').doc(followingId),
      {
        'followers': FieldValue.arrayUnion([followerId]),
        'followersCount': FieldValue.increment(1),
      },
    );
    
    await batch.commit();
  }

  Future<void> unfollowUser(String followerId, String followingId) async {
    final batch = _firestore.batch();
    
    // Remove from follower's following list
    batch.update(
      _firestore.collection('users').doc(followerId),
      {
        'following': FieldValue.arrayRemove([followingId]),
        'followingCount': FieldValue.increment(-1),
      },
    );
    
    // Remove from following's followers list
    batch.update(
      _firestore.collection('users').doc(followingId),
      {
        'followers': FieldValue.arrayRemove([followerId]),
        'followersCount': FieldValue.increment(-1),
      },
    );
    
    await batch.commit();
  }

  // Feed Generation
  Stream<List<PostModel>> getFeedStream(String userId, {int limit = 20}) async* {
    try {
      // Get user's following list
      final userDoc = await _firestore.collection('users').doc(userId).get();
      if (!userDoc.exists) {
        // If user doesn't exist, show recent posts
        yield* getPostsStream(limit: limit);
        return;
      }
      
      final user = UserModel.fromMap(userDoc.data()!);
      final following = user.following;
      
      if (following.isEmpty) {
        // If not following anyone, show recent posts
        yield* getPostsStream(limit: limit);
      } else {
        // Show posts from followed users
        yield* _firestore
            .collection('posts')
            .where('userId', whereIn: following)
            .orderBy('createdAt', descending: true)
            .limit(limit)
            .snapshots()
            .map((snapshot) => snapshot.docs
                .map((doc) => PostModel.fromMap(doc.data()))
                .toList());
      }
    } catch (e) {
      // If there's an error, show recent posts as fallback
      yield* getPostsStream(limit: limit);
    }
  }

  // Search
  Stream<List<PostModel>> searchPosts(String query) {
    return _firestore
        .collection('posts')
        .where('tags', arrayContains: query.toLowerCase())
        .orderBy('createdAt', descending: true)
        .limit(20)
        .snapshots()
        .map((snapshot) => snapshot.docs
            .map((doc) => PostModel.fromMap(doc.data()))
            .toList());
  }

  Stream<List<UserModel>> searchUsers(String query) {
    return _firestore
        .collection('users')
        .where('displayName', isGreaterThanOrEqualTo: query)
        .where('displayName', isLessThan: query + '\uf8ff')
        .limit(20)
        .snapshots()
        .map((snapshot) => snapshot.docs
            .map((doc) => UserModel.fromMap(doc.data()))
            .toList());
  }

  // Utility Methods
  String generateId() => _uuid.v4();
  
  bool isPostLikedByUser(PostModel post, String userId) {
    return post.likedBy.contains(userId);
  }
}
