import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:image_picker/image_picker.dart';
import 'dart:io';
import '../utils/app_colors.dart';
import '../services/post_service.dart';
import '../services/social_service.dart';
import '../models/post_model.dart';
import '../widgets/post_card.dart';
import 'auth_screen.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final FirebaseAuth _auth = FirebaseAuth.instance;
  final GoogleSignIn _googleSignIn = GoogleSignIn();
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;
  final ImagePicker _imagePicker = ImagePicker();
  final PostService _postService = PostService();
  final SocialService _socialService = SocialService();
  
  Map<String, int> _userStats = {
    'repairCount': 0,
    'totalLikes': 0,
    'followersCount': 0,
  };

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _loadUserStats();
  }

  bool _isLoadingStats = false;
  
  Future<void> _loadUserStats() async {
    if (_isLoadingStats) return; // Prevent multiple simultaneous loads
    
    final userId = _auth.currentUser?.uid;
    if (userId != null) {
      setState(() {
        _isLoadingStats = true;
      });
      
      try {
        final stats = await _socialService.getUserStats(userId);
        if (mounted) {
          setState(() {
            _userStats = stats;
            _isLoadingStats = false;
          });
        }
      } catch (e) {
        if (mounted) {
          setState(() {
            _isLoadingStats = false;
          });
        }
      }
    }
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Profile Header
        Container(
          padding: const EdgeInsets.all(24),
          child: StreamBuilder<DocumentSnapshot>(
            stream: _firestore
                .collection('users')
                .doc(_auth.currentUser?.uid)
                .snapshots(),
            builder: (context, snapshot) {
              if (snapshot.hasData && snapshot.data!.exists) {
                final userData = snapshot.data!.data() as Map<String, dynamic>?;
                final name = userData?['name'] ?? 'User';
                final profileImagePath = userData?['profileImagePath'];
                final interests = List<String>.from(userData?['interests'] ?? []);
                final profileCompletion = userData?['profileCompletion'] ?? 0;
                final phone = userData?['phone'] ?? '';
                final countryCode = userData?['countryCode'] ?? '';
                final gender = userData?['gender'] ?? '';
                
                return Column(
                  children: [
                    // Profile Picture
                    GestureDetector(
                      onTap: _showImageOptions,
                      child: Stack(
                        children: [
                          CircleAvatar(
                            radius: 50,
                            backgroundColor: AppColors.primary,
                            child: profileImagePath != null && profileImagePath.isNotEmpty
                                ? ClipOval(
                                    child: Image.file(
                                      File(profileImagePath),
                                      width: 100,
                                      height: 100,
                                      fit: BoxFit.cover,
                                      errorBuilder: (context, error, stackTrace) {
                                        return const Icon(
                                          Icons.person,
                                          size: 50,
                                          color: Colors.white,
                                        );
                                      },
                                    ),
                                  )
                                : const Icon(
                                    Icons.person,
                                    size: 50,
                                    color: Colors.white,
                                  ),
                          ),
                          // Edit icon overlay
                          Positioned(
                            bottom: 0,
                            right: 0,
                            child: Container(
                              padding: const EdgeInsets.all(4),
                              decoration: BoxDecoration(
                                color: AppColors.primary,
                                shape: BoxShape.circle,
                                border: Border.all(color: Colors.white, width: 2),
                              ),
                              child: const Icon(
                                Icons.camera_alt,
                                size: 16,
                                color: Colors.white,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 16),
                    
                    // User Name and Refresh Button
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          name,
                          style: const TextStyle(
                            fontSize: 24,
                            fontWeight: FontWeight.bold,
                            color: AppColors.text,
                          ),
                        ),
                        const SizedBox(width: 8),
                        IconButton(
                          onPressed: _isLoadingStats ? null : _loadUserStats,
                          icon: _isLoadingStats 
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                )
                              : const Icon(Icons.refresh, size: 20),
                          tooltip: 'Refresh Stats',
                          padding: EdgeInsets.zero,
                          constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    
                    // User Info
                    if (phone.isNotEmpty || gender.isNotEmpty) ...[
                      Text(
                        [
                          if (phone.isNotEmpty) '$countryCode $phone',
                          if (gender.isNotEmpty) gender,
                        ].join(' • '),
                        style: const TextStyle(
                          color: AppColors.textSecondary,
                          fontSize: 14,
                        ),
                      ),
                      const SizedBox(height: 8),
                    ],
                    
                    // Interests or completion status
                    Text(
                      interests.isNotEmpty 
                          ? 'Interested in ${interests.take(2).join(', ')}'
                          : 'Complete your profile to get started',
                      style: const TextStyle(
                        color: AppColors.textSecondary,
                      ),
                    ),
                    
                    // Profile completion indicator
                    if (profileCompletion < 100) ...[
                      const SizedBox(height: 8),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(
                            'Profile: $profileCompletion% complete',
                            style: const TextStyle(
                              color: AppColors.textSecondary,
                              fontSize: 12,
                            ),
                          ),
                        ],
                      ),
                    ],
                    const SizedBox(height: 24),
                    
                    // Stats Row
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                      children: [
                        _buildStatItem('Fixes', '${_userStats['repairCount']}'),
                        _buildStatItem('Likes', '${_userStats['totalLikes']}'),
                        _buildStatItem('Followers', '${_userStats['followersCount']}'),
                      ],
                    ),
                  ],
                );
              } else if (snapshot.hasError) {
                // Error state
                return Column(
                  children: [
                    const CircleAvatar(
                      radius: 50,
                      backgroundColor: AppColors.primary,
                      child: Icon(
                        Icons.person,
                        size: 50,
                        color: Colors.white,
                      ),
                    ),
                    const SizedBox(height: 16),
                    const Text(
                      'Error loading profile',
                      style: TextStyle(
                        fontSize: 24,
                        fontWeight: FontWeight.bold,
                        color: AppColors.text,
                      ),
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'Please try again later',
                      style: TextStyle(
                        color: AppColors.textSecondary,
                      ),
                    ),
                    const SizedBox(height: 24),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                      children: [
                        _buildStatItem('Fixes', '0'),
                        _buildStatItem('Likes', '0'),
                        _buildStatItem('Followers', '0'),
                      ],
                    ),
                  ],
                );
              } else {
                // Loading state
                return Column(
                  children: [
                    const CircleAvatar(
                      radius: 50,
                      backgroundColor: AppColors.primary,
                      child: Icon(
                        Icons.person,
                        size: 50,
                        color: Colors.white,
                      ),
                    ),
                    const SizedBox(height: 16),
                    const Text(
                      'Loading...',
                      style: TextStyle(
                        fontSize: 24,
                        fontWeight: FontWeight.bold,
                        color: AppColors.text,
                      ),
                    ),
                    const SizedBox(height: 24),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                      children: [
                        _buildStatItem('Fixes', '0'),
                        _buildStatItem('Likes', '0'),
                        _buildStatItem('Followers', '0'),
                      ],
                    ),
                  ],
                );
              }
            },
          ),
        ),
        // Tab Bar
        Container(
          decoration: BoxDecoration(
            color: Colors.grey[100],
            borderRadius: BorderRadius.circular(12),
          ),
          margin: const EdgeInsets.symmetric(horizontal: 16),
          child: TabBar(
            controller: _tabController,
            indicator: BoxDecoration(
              color: AppColors.primary,
              borderRadius: BorderRadius.circular(12),
            ),
            indicatorSize: TabBarIndicatorSize.tab,
            dividerColor: Colors.transparent,
            labelColor: Colors.white,
            unselectedLabelColor: AppColors.textSecondary,
            labelStyle: const TextStyle(fontWeight: FontWeight.bold),
            tabs: const [
              Tab(text: 'My Fixes'),
              Tab(text: 'Saved'),
              Tab(text: 'Settings'),
            ],
          ),
        ),
        const SizedBox(height: 16),
        // Tab Content
        Expanded(
          child: TabBarView(
            controller: _tabController,
            children: [
              _buildMyFixesTab(),
              _buildSavedTab(),
              _buildSettingsTab(),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildStatItem(String label, String value) {
    return Column(
      children: [
        Text(
          value,
          style: const TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.bold,
            color: AppColors.text,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          label,
          style: const TextStyle(
            color: AppColors.textSecondary,
          ),
        ),
      ],
    );
  }

  Widget _buildMyFixesTab() {
    final userId = _auth.currentUser?.uid;
    if (userId == null) {
      return const Center(
        child: Text(
          'Please log in to view your posts',
          style: TextStyle(color: AppColors.textSecondary),
        ),
      );
    }

    return StreamBuilder<List<PostModel>>(
      key: ValueKey('my-fixes-$userId'),
      stream: _postService.getUserPosts(userId),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(
            child: CircularProgressIndicator(),
          );
        }

        if (snapshot.hasError) {
          return Center(
            child: Text(
              'Error loading posts: ${snapshot.error}',
              style: const TextStyle(color: Colors.red),
            ),
          );
        }

        final userPosts = snapshot.data ?? [];

        if (userPosts.isEmpty) {
          return const Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  Icons.build_circle_outlined,
                  size: 64,
                  color: AppColors.textSecondary,
                ),
                SizedBox(height: 16),
                Text(
                  'No posts yet',
                  style: TextStyle(
                    fontSize: 18,
                    color: AppColors.textSecondary,
                  ),
                ),
                SizedBox(height: 8),
                Text(
                  'Create your first repair post',
                  style: TextStyle(
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          );
        }

        return ListView.builder(
          padding: const EdgeInsets.all(16),
          itemCount: userPosts.length,
          itemBuilder: (context, index) {
            final post = userPosts[index];
            return PostCard(
              post: post,
              isSaved: post.savedBy.contains(userId),
              canDelete: true, // User can delete their own posts
              onTap: () {
                // TODO: Navigate to post detail
              },
              onLike: () {
                // TODO: Handle like
              },
              onComment: () {
                // TODO: Handle comment
              },
              onShare: () {
                // TODO: Handle share
              },
              onSave: () async {
                try {
                  if (post.savedBy.contains(userId)) {
                    await _postService.unsavePost(post.id);
                    if (mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('Post removed from saved'),
                          backgroundColor: Colors.orange,
                        ),
                      );
                    }
                  } else {
                    await _postService.savePost(post.id);
                    if (mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('Post saved'),
                          backgroundColor: Colors.green,
                        ),
                      );
                    }
                  }
                } catch (e) {
                  if (mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text('Error: $e'),
                        backgroundColor: Colors.red,
                      ),
                    );
                  }
                }
              },
              onDelete: () => _handleDeletePost(post),
            );
          },
        );
      },
    );
  }

  Widget _buildSavedTab() {
    final userId = _auth.currentUser?.uid;
    return StreamBuilder<List<PostModel>>(
      key: ValueKey('saved-posts-$userId'),
      stream: _postService.getSavedPosts(),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(
            child: CircularProgressIndicator(),
          );
        }

        if (snapshot.hasError) {
          return Center(
            child: Text(
              'Error loading saved posts: ${snapshot.error}',
              style: const TextStyle(color: Colors.red),
            ),
          );
        }

        final savedPosts = snapshot.data ?? [];

        if (savedPosts.isEmpty) {
          return const Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  Icons.bookmark_border,
                  size: 64,
                  color: AppColors.textSecondary,
                ),
                SizedBox(height: 16),
                Text(
                  'No saved posts yet',
                  style: TextStyle(
                    fontSize: 18,
                    color: AppColors.textSecondary,
                  ),
                ),
                SizedBox(height: 8),
                Text(
                  'Posts you save will appear here',
                  style: TextStyle(
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          );
        }

        return ListView.builder(
          padding: const EdgeInsets.all(16),
          itemCount: savedPosts.length,
          itemBuilder: (context, index) {
            final post = savedPosts[index];
            return PostCard(
              post: post,
              isSaved: true,
              onTap: () {
                // TODO: Navigate to post detail
              },
              onLike: () {
                // TODO: Handle like
              },
              onComment: () {
                // TODO: Handle comment
              },
              onShare: () {
                // TODO: Handle share
              },
              onSave: () async {
                try {
                  await _postService.unsavePost(post.id);
                  if (mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text('Post removed from saved'),
                        backgroundColor: Colors.orange,
                      ),
                    );
                  }
                } catch (e) {
                  if (mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text('Error: $e'),
                        backgroundColor: Colors.red,
                      ),
                    );
                  }
                }
              },
            );
          },
        );
      },
    );
  }

  Widget _buildSettingsTab() {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _buildSettingsItem(Icons.notifications, 'Notifications'),
        _buildSettingsItem(Icons.privacy_tip, 'Privacy'),
        _buildSettingsItem(Icons.help, 'Help & Support'),
        _buildSettingsItem(Icons.info, 'About'),
        const SizedBox(height: 24),
        ElevatedButton(
          onPressed: _signOut,
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.red,
            foregroundColor: Colors.white,
          ),
          child: const Text('Sign Out'),
        ),
      ],
    );
  }

  Widget _buildSettingsItem(IconData icon, String title) {
    return ListTile(
      leading: Icon(icon, color: AppColors.primary),
      title: Text(title),
      trailing: const Icon(Icons.chevron_right),
      onTap: () {},
    );
  }

  Future<void> _signOut() async {
    try {
      // Sign out from Google first (important for truly clearing the Google session)
      await _googleSignIn.signOut();
      
      // Then sign out from Firebase
      await _auth.signOut();
      
      if (mounted) {
        Navigator.of(context).pushAndRemoveUntil(
          MaterialPageRoute(builder: (context) => const AuthScreen()),
          (route) => false,
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error signing out: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _showImageOptions() async {
    showModalBottomSheet(
      context: context,
      builder: (BuildContext context) {
        return Container(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text(
                'Update Profile Picture',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 20),
              ListTile(
                leading: const Icon(Icons.camera_alt, color: Colors.blue),
                title: const Text('Take Photo'),
                onTap: () async {
                  Navigator.pop(context);
                  await _takePhoto();
                },
              ),
              ListTile(
                leading: const Icon(Icons.photo_library, color: Colors.green),
                title: const Text('Choose from Gallery'),
                onTap: () async {
                  Navigator.pop(context);
                  await _pickImage();
                },
              ),
            ],
          ),
        );
      },
    );
  }

  Future<void> _takePhoto() async {
    try {
      final XFile? photo = await _imagePicker.pickImage(
        source: ImageSource.camera,
        imageQuality: 80,
      );
      
      if (photo != null) {
        await _updateProfileImage(photo.path);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to take photo: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _pickImage() async {
    try {
      final XFile? image = await _imagePicker.pickImage(
        source: ImageSource.gallery,
        imageQuality: 80,
      );
      
      if (image != null) {
        await _updateProfileImage(image.path);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to pick image: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _updateProfileImage(String imagePath) async {
    try {
      final userId = _auth.currentUser?.uid;
      if (userId == null) return;

      // Update the profile image path in Firestore
      await _firestore.collection('users').doc(userId).update({
        'profileImagePath': imagePath,
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Profile picture updated successfully!'),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to update profile picture: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _handleDeletePost(PostModel post) async {
    // Show confirmation dialog
    final shouldDelete = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Post'),
        content: const Text('Are you sure you want to delete this post? This action cannot be undone.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (shouldDelete != true) return;

    try {
      final userId = _auth.currentUser?.uid;
      if (userId == null) throw Exception('User not authenticated');
      
      await _socialService.deletePost(post.id, userId);
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Post deleted successfully'),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to delete post: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }
}
