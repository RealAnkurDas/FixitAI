import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cached_network_image/cached_network_image.dart';
import '../utils/app_colors.dart';
import '../widgets/post_card.dart';
import '../services/social_service.dart';
import '../models/post_model.dart';
import '../models/user_model.dart';
import 'social/create_post_screen.dart';
import 'social/post_detail_screen.dart';

class SocialFeedScreen extends StatefulWidget {
  const SocialFeedScreen({super.key});

  @override
  State<SocialFeedScreen> createState() => _SocialFeedScreenState();
}

class _SocialFeedScreenState extends State<SocialFeedScreen> {
  final SocialService _socialService = SocialService();
  final FirebaseAuth _auth = FirebaseAuth.instance;
  final ScrollController _scrollController = ScrollController();
  
  bool _isLoading = false;
  List<PostModel> _posts = [];
  Map<String, UserModel> _userProfiles = {};

  @override
  void initState() {
    super.initState();
    _loadPosts();
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _loadPosts() async {
    if (_isLoading) return;
    
    setState(() {
      _isLoading = true;
    });

    try {
      final userId = _auth.currentUser?.uid;
      if (userId != null) {
        _socialService.getFeedStream(userId, limit: 20).listen((posts) {
          setState(() {
            _posts = posts;
            _isLoading = false;
          });
          _loadUserProfiles(posts);
        }, onError: (error) {
          setState(() {
            _isLoading = false;
          });
          _showErrorSnackBar('Failed to load posts: $error');
        });
      } else {
        setState(() {
          _isLoading = false;
        });
      }
    } catch (e) {
      setState(() {
        _isLoading = false;
      });
      _showErrorSnackBar('Failed to load posts: $e');
    }
  }

  Future<void> _loadUserProfiles(List<PostModel> posts) async {
    final userIds = posts.map((post) => post.userId).toSet();
    
    for (final userId in userIds) {
      if (!_userProfiles.containsKey(userId)) {
        final userProfile = await _socialService.getUserProfile(userId);
        if (userProfile != null) {
          setState(() {
            _userProfiles[userId] = userProfile;
          });
        }
      }
    }
  }

  Future<void> _refreshFeed() async {
    await _loadPosts();
  }

  void _showErrorSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.red,
      ),
    );
  }

  void _navigateToCreatePost() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => const CreatePostScreen(),
      ),
    ).then((_) => _refreshFeed());
  }

  void _navigateToPostDetail(PostModel post) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => PostDetailScreen(post: post),
      ),
    ).then((_) => _refreshFeed());
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: RefreshIndicator(
        onRefresh: _refreshFeed,
        child: _isLoading && _posts.isEmpty
            ? const Center(child: CircularProgressIndicator())
            : _posts.isEmpty
                ? _buildEmptyState()
                : ListView.builder(
                    controller: _scrollController,
                    padding: const EdgeInsets.all(16),
                    itemCount: _posts.length,
                    itemBuilder: (context, index) {
                      final post = _posts[index];
                      final userProfile = _userProfiles[post.userId];
                      
                      return PostCard(
                        post: post,
                        userProfile: userProfile,
                        onTap: () => _navigateToPostDetail(post),
                        onLike: () => _handleLike(post),
                        onComment: () => _navigateToPostDetail(post),
                        onShare: () => _handleShare(post),
                      );
                    },
                  ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _navigateToCreatePost,
        backgroundColor: AppColors.primary,
        child: const Icon(Icons.add, color: Colors.white),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.people_outline,
            size: 64,
            color: Colors.grey[400],
          ),
          const SizedBox(height: 16),
          Text(
            'No posts yet',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: Colors.grey[600],
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Follow other users or create your first post!',
            style: TextStyle(
              color: Colors.grey[500],
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 24),
          ElevatedButton(
            onPressed: _navigateToCreatePost,
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.primary,
              foregroundColor: Colors.white,
            ),
            child: const Text('Create Post'),
          ),
        ],
      ),
    );
  }

  Future<void> _handleLike(PostModel post) async {
    try {
      final userId = _auth.currentUser?.uid;
      if (userId == null) return;

      final isLiked = _socialService.isPostLikedByUser(post, userId);
      
      if (isLiked) {
        await _socialService.unlikePost(post.id, userId);
      } else {
        await _socialService.likePost(post.id, userId);
      }
    } catch (e) {
      _showErrorSnackBar('Failed to like post: $e');
    }
  }

  void _handleShare(PostModel post) {
    // TODO: Implement share functionality
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Share functionality coming soon!'),
      ),
    );
  }
}
