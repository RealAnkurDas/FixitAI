import 'package:firebase_auth/firebase_auth.dart';
import 'package:google_sign_in/google_sign_in.dart';
import '../models/user_model.dart';
import 'social_service.dart';

class AuthService {
  final FirebaseAuth _auth = FirebaseAuth.instance;
  final GoogleSignIn _googleSignIn = GoogleSignIn();
  final SocialService _socialService = SocialService();

  // Get current user
  User? get currentUser => _auth.currentUser;

  // Auth state changes stream
  Stream<User?> get authStateChanges => _auth.authStateChanges();

  // Sign in with email and password
  Future<UserCredential> signInWithEmailAndPassword(
    String email,
    String password,
  ) async {
    try {
      final credential = await _auth.signInWithEmailAndPassword(
        email: email,
        password: password,
      );
      
      // Create user profile if it doesn't exist
      await _createUserProfileIfNeeded(credential.user!);
      
      return credential;
    } catch (e) {
      throw Exception('Failed to sign in: $e');
    }
  }

  // Sign up with email and password
  Future<UserCredential> createUserWithEmailAndPassword(
    String email,
    String password,
    String displayName,
  ) async {
    try {
      final credential = await _auth.createUserWithEmailAndPassword(
        email: email,
        password: password,
      );
      
      // Update display name
      await credential.user!.updateDisplayName(displayName);
      
      // Create user profile
      await _createUserProfile(credential.user!, displayName);
      
      return credential;
    } catch (e) {
      throw Exception('Failed to create account: $e');
    }
  }

  // Sign in with Google
  Future<UserCredential> signInWithGoogle() async {
    try {
      final GoogleSignInAccount? googleUser = await _googleSignIn.signIn();
      if (googleUser == null) throw Exception('Google sign in cancelled');

      final GoogleSignInAuthentication googleAuth = await googleUser.authentication;
      final credential = GoogleAuthProvider.credential(
        accessToken: googleAuth.accessToken,
        idToken: googleAuth.idToken,
      );

      final userCredential = await _auth.signInWithCredential(credential);
      
      // Create user profile if it doesn't exist
      await _createUserProfileIfNeeded(userCredential.user!);
      
      return userCredential;
    } catch (e) {
      throw Exception('Failed to sign in with Google: $e');
    }
  }

  // Sign out
  Future<void> signOut() async {
    try {
      await Future.wait([
        _auth.signOut(),
        _googleSignIn.signOut(),
      ]);
    } catch (e) {
      throw Exception('Failed to sign out: $e');
    }
  }

  // Reset password
  Future<void> resetPassword(String email) async {
    try {
      await _auth.sendPasswordResetEmail(email: email);
    } catch (e) {
      throw Exception('Failed to send password reset email: $e');
    }
  }

  // Create user profile
  Future<void> _createUserProfile(User user, [String? displayName]) async {
    final userModel = UserModel(
      id: user.uid,
      email: user.email ?? '',
      displayName: displayName ?? user.displayName ?? 'User',
      photoURL: user.photoURL,
      createdAt: DateTime.now(),
      lastActive: DateTime.now(),
    );

    await _socialService.createUserProfile(userModel);
  }

  // Create user profile if it doesn't exist
  Future<void> _createUserProfileIfNeeded(User user) async {
    final existingProfile = await _socialService.getUserProfile(user.uid);
    
    if (existingProfile == null) {
      await _createUserProfile(user);
    } else {
      // Update last active
      await _socialService.updateUserProfile(user.uid, {
        'lastActive': DateTime.now(),
      });
    }
  }

  // Update user profile
  Future<void> updateUserProfile({
    String? displayName,
    String? bio,
    String? photoURL,
  }) async {
    try {
      final user = _auth.currentUser;
      if (user == null) throw Exception('No user signed in');

      final updates = <String, dynamic>{};
      
      if (displayName != null) {
        await user.updateDisplayName(displayName);
        updates['displayName'] = displayName;
      }
      
      if (photoURL != null) {
        await user.updatePhotoURL(photoURL);
        updates['photoURL'] = photoURL;
      }
      
      if (bio != null) {
        updates['bio'] = bio;
      }

      if (updates.isNotEmpty) {
        await _socialService.updateUserProfile(user.uid, updates);
      }
    } catch (e) {
      throw Exception('Failed to update profile: $e');
    }
  }

  // Delete account
  Future<void> deleteAccount() async {
    try {
      final user = _auth.currentUser;
      if (user == null) throw Exception('No user signed in');

      // Delete user profile from Firestore
      await _socialService.deleteUserProfile(user.uid);
      
      // Delete Firebase Auth account
      await user.delete();
    } catch (e) {
      throw Exception('Failed to delete account: $e');
    }
  }
}
