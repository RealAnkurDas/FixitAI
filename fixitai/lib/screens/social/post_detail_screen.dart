import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cached_network_image/cached_network_image.dart';
import '../../utils/app_colors.dart';
import '../../services/social_service.dart';
import '../../models/post_model.dart';
import '../../models/user_model.dart';
import '../../models/comment_model.dart';

class PostDetailScreen extends StatefulWidget {
  final PostModel post;

  const PostDetailScreen({
    super.key,
    required this.post,
  });

  @override
  State<PostDetailScreen> createState() => _PostDetailScreenState();
}

class _PostDetailScreenState extends State<PostDetailScreen> {
  final SocialService _socialService = SocialService();
  final FirebaseAuth _auth = FirebaseAuth.instance;
  final TextEditingController _commentController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  
  UserModel? _postUser;
  List<CommentModel> _comments = [];
  Map<String, UserModel> _commentUsers = {};
  bool _isLoading = false;
  bool _isLiked = false;

  @override
  void initState() {
    super.initState();
    _loadPostData();
    _checkIfLiked();
  }

  @override
  void dispose() {
    _commentController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _loadPostData() async {
    setState(() {
      _isLoading = true;
    });

    try {
      // Load post user
      final postUser = await _socialService.getUserProfile(widget.post.userId);
      setState(() {
        _postUser = postUser;
      });

      // Load comments with error handling
      _socialService.getPostCommentsStream(widget.post.id).listen(
        (comments) {
          setState(() {
            _comments = comments;
            _isLoading = false;
          });
          _loadCommentUsers(comments);
        },
        onError: (error) {
          print('Error loading comments: $error');
          setState(() {
            _comments = [];
            _isLoading = false;
          });
          _showErrorSnackBar('Failed to load comments. Please try again later.');
        },
      );
    } catch (e) {
      setState(() {
        _isLoading = false;
      });
      _showErrorSnackBar('Failed to load post data: $e');
    }
  }

  Future<void> _loadCommentUsers(List<CommentModel> comments) async {
    final userIds = comments.map((comment) => comment.userId).toSet();
    
    for (final userId in userIds) {
      if (!_commentUsers.containsKey(userId)) {
        final user = await _socialService.getUserProfile(userId);
        if (user != null) {
          setState(() {
            _commentUsers[userId] = user;
          });
        }
      }
    }
  }

  Future<void> _checkIfLiked() async {
    final userId = _auth.currentUser?.uid;
    if (userId != null) {
      final isLiked = _socialService.isPostLikedByUser(widget.post, userId);
      setState(() {
        _isLiked = isLiked;
      });
    }
  }

  Future<void> _handleLike() async {
    try {
      final userId = _auth.currentUser?.uid;
      if (userId == null) return;

      if (_isLiked) {
        await _socialService.unlikePost(widget.post.id, userId);
      } else {
        await _socialService.likePost(widget.post.id, userId);
      }
      
      setState(() {
        _isLiked = !_isLiked;
      });
    } catch (e) {
      _showErrorSnackBar('Failed to like post: $e');
    }
  }

  Future<void> _addComment() async {
    if (_commentController.text.trim().isEmpty) return;

    try {
      final userId = _auth.currentUser?.uid;
      if (userId == null) return;

      final comment = CommentModel(
        id: _socialService.generateId(),
        postId: widget.post.id,
        userId: userId,
        content: _commentController.text.trim(),
        createdAt: DateTime.now(),
      );

      await _socialService.addComment(comment);
      _commentController.clear();
    } catch (e) {
      _showErrorSnackBar('Failed to add comment: $e');
    }
  }

  void _showErrorSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.red,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Post'),
        backgroundColor: AppColors.background,
        elevation: 0,
        actions: [
          IconButton(
            onPressed: () {
              // TODO: Show more options
            },
            icon: const Icon(Icons.more_vert),
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : Column(
              children: [
                // Post content
                Expanded(
                  child: SingleChildScrollView(
                    controller: _scrollController,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // User header
                        _buildUserHeader(),
                        
                        // Post image
                        if (widget.post.imageURL != null) _buildPostImage(),
                        
                        // Post content
                        _buildPostContent(),
                        
                        // Action buttons
                        _buildActionButtons(),
                        
                        const Divider(),
                        
                        // Comments section
                        _buildCommentsSection(),
                      ],
                    ),
                  ),
                ),
                
                // Comment input
                _buildCommentInput(),
              ],
            ),
    );
  }

  Widget _buildUserHeader() {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Row(
        children: [
          CircleAvatar(
            radius: 24,
            backgroundColor: AppColors.primary.withOpacity(0.1),
            backgroundImage: _postUser?.photoURL != null
                ? CachedNetworkImageProvider(_postUser!.photoURL!)
                : null,
            child: _postUser?.photoURL == null
                ? Text(
                    _postUser?.displayName.isNotEmpty == true
                        ? _postUser!.displayName[0].toUpperCase()
                        : 'U',
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      color: AppColors.primary,
                      fontSize: 18,
                    ),
                  )
                : null,
          ),
          
          const SizedBox(width: 12),
          
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _postUser?.displayName ?? 'Unknown User',
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                  ),
                ),
                Text(
                  _formatTimeAgo(widget.post.createdAt),
                  style: TextStyle(
                    color: Colors.grey[600],
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
          
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: _getDifficultyColor(widget.post.difficulty),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(
              widget.post.difficulty,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 10,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPostImage() {
    return Container(
      width: double.infinity,
      height: 300,
      child: CachedNetworkImage(
        imageUrl: widget.post.imageURL!,
        fit: BoxFit.cover,
        placeholder: (context, url) => Container(
          color: Colors.grey[200],
          child: const Center(
            child: CircularProgressIndicator(),
          ),
        ),
        errorWidget: (context, url, error) => Container(
          color: Colors.grey[200],
          child: const Icon(Icons.error),
        ),
      ),
    );
  }

  Widget _buildPostContent() {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            widget.post.title,
            style: const TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 20,
            ),
          ),
          
          const SizedBox(height: 12),
          
          Text(
            widget.post.description,
            style: TextStyle(
              color: Colors.grey[700],
              fontSize: 16,
              height: 1.5,
            ),
          ),
          
          const SizedBox(height: 16),
          
          // Device info
          Row(
            children: [
              Icon(Icons.devices, size: 18, color: Colors.grey[600]),
              const SizedBox(width: 8),
              Text(
                widget.post.deviceType,
                style: TextStyle(
                  color: Colors.grey[600],
                  fontSize: 14,
                ),
              ),
              const SizedBox(width: 24),
              Icon(Icons.access_time, size: 18, color: Colors.grey[600]),
              const SizedBox(width: 8),
              Text(
                '${widget.post.timeRequired} min',
                style: TextStyle(
                  color: Colors.grey[600],
                  fontSize: 14,
                ),
              ),
            ],
          ),
          
          const SizedBox(height: 12),
          
          // Tools used
          if (widget.post.toolsUsed.isNotEmpty) ...[
            Text(
              'Tools Used:',
              style: TextStyle(
                fontWeight: FontWeight.bold,
                fontSize: 14,
                color: Colors.grey[700],
              ),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 4,
              children: widget.post.toolsUsed.map((tool) => Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.primary.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  tool,
                  style: TextStyle(
                    color: AppColors.primary,
                    fontSize: 12,
                  ),
                ),
              )).toList(),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildActionButtons() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        children: [
          _buildActionButton(
            icon: _isLiked ? Icons.favorite : Icons.favorite_border,
            label: '${widget.post.likesCount}',
            onTap: _handleLike,
            isActive: _isLiked,
          ),
          
          const SizedBox(width: 24),
          
          _buildActionButton(
            icon: Icons.comment_outlined,
            label: '${widget.post.commentsCount}',
            onTap: () {
              // Focus on comment input
              FocusScope.of(context).requestFocus(FocusNode());
              Future.delayed(const Duration(milliseconds: 100), () {
                _scrollController.animateTo(
                  _scrollController.position.maxScrollExtent,
                  duration: const Duration(milliseconds: 300),
                  curve: Curves.easeOut,
                );
              });
            },
          ),
          
          const SizedBox(width: 24),
          
          _buildActionButton(
            icon: Icons.share_outlined,
            label: 'Share',
            onTap: () {
              // TODO: Implement share
            },
          ),
        ],
      ),
    );
  }

  Widget _buildActionButton({
    required IconData icon,
    required String label,
    VoidCallback? onTap,
    bool isActive = false,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 24,
              color: isActive ? AppColors.primary : Colors.grey[600],
            ),
            const SizedBox(width: 8),
            Text(
              label,
              style: TextStyle(
                color: isActive ? AppColors.primary : Colors.grey[600],
                fontSize: 14,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCommentsSection() {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Comments (${_comments.length})',
            style: const TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 16,
            ),
          ),
          
          const SizedBox(height: 12),
          
          if (_comments.isEmpty)
            Center(
              child: Padding(
                padding: const EdgeInsets.all(32),
                child: Column(
                  children: [
                    Icon(
                      Icons.comment_outlined,
                      size: 48,
                      color: Colors.grey[400],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'No comments yet',
                      style: TextStyle(
                        color: Colors.grey[600],
                        fontSize: 16,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Be the first to comment!',
                      style: TextStyle(
                        color: Colors.grey[500],
                        fontSize: 14,
                      ),
                    ),
                  ],
                ),
              ),
            )
          else
            ListView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: _comments.length,
              itemBuilder: (context, index) {
                final comment = _comments[index];
                final commentUser = _commentUsers[comment.userId];
                
                return _buildCommentItem(comment, commentUser);
              },
            ),
        ],
      ),
    );
  }

  Widget _buildCommentItem(CommentModel comment, UserModel? user) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          CircleAvatar(
            radius: 16,
            backgroundColor: AppColors.primary.withOpacity(0.1),
            backgroundImage: user?.photoURL != null
                ? CachedNetworkImageProvider(user!.photoURL!)
                : null,
            child: user?.photoURL == null
                ? Text(
                    user?.displayName.isNotEmpty == true
                        ? user!.displayName[0].toUpperCase()
                        : 'U',
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      color: AppColors.primary,
                      fontSize: 12,
                    ),
                  )
                : null,
          ),
          
          const SizedBox(width: 12),
          
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(
                      user?.displayName ?? 'Unknown User',
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 14,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      _formatTimeAgo(comment.createdAt),
                      style: TextStyle(
                        color: Colors.grey[500],
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
                
                const SizedBox(height: 4),
                
                Text(
                  comment.content,
                  style: TextStyle(
                    color: Colors.grey[700],
                    fontSize: 14,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCommentInput() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border(
          top: BorderSide(color: Colors.grey[300]!),
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _commentController,
              decoration: InputDecoration(
                hintText: 'Add a comment...',
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(24),
                  borderSide: BorderSide(color: Colors.grey[300]!),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(24),
                  borderSide: const BorderSide(color: AppColors.primary),
                ),
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 12,
                ),
              ),
              maxLines: null,
            ),
          ),
          
          const SizedBox(width: 8),
          
          IconButton(
            onPressed: _addComment,
            icon: const Icon(Icons.send),
            style: IconButton.styleFrom(
              backgroundColor: AppColors.primary,
              foregroundColor: Colors.white,
            ),
          ),
        ],
      ),
    );
  }

  String _formatTimeAgo(DateTime dateTime) {
    final now = DateTime.now();
    final difference = now.difference(dateTime);
    
    if (difference.inDays > 0) {
      return '${difference.inDays}d ago';
    } else if (difference.inHours > 0) {
      return '${difference.inHours}h ago';
    } else if (difference.inMinutes > 0) {
      return '${difference.inMinutes}m ago';
    } else {
      return 'Just now';
    }
  }

  Color _getDifficultyColor(String difficulty) {
    switch (difficulty.toLowerCase()) {
      case 'easy':
        return Colors.green;
      case 'medium':
        return Colors.orange;
      case 'hard':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }
}
