import 'dart:io';
import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:image_picker/image_picker.dart';
import '../../utils/app_colors.dart';
import '../../services/social_service.dart';
import '../../services/firebase_test.dart';
import '../../models/post_model.dart';
import '../../models/user_model.dart';

class CreatePostScreen extends StatefulWidget {
  const CreatePostScreen({super.key});

  @override
  State<CreatePostScreen> createState() => _CreatePostScreenState();
}

class _CreatePostScreenState extends State<CreatePostScreen> {
  final SocialService _socialService = SocialService();
  final FirebaseAuth _auth = FirebaseAuth.instance;
  final ImagePicker _imagePicker = ImagePicker();
  
  final TextEditingController _titleController = TextEditingController();
  final TextEditingController _descriptionController = TextEditingController();
  final TextEditingController _deviceTypeController = TextEditingController();
  final TextEditingController _toolsController = TextEditingController();
  
  File? _selectedImage;
  String _selectedDifficulty = 'Easy';
  int _timeRequired = 30;
  bool _isLoading = false;
  UserModel? _currentUser;

  final List<String> _difficultyOptions = ['Easy', 'Medium', 'Hard'];

  @override
  void initState() {
    super.initState();
    _loadCurrentUser();
  }

  @override
  void dispose() {
    _titleController.dispose();
    _descriptionController.dispose();
    _deviceTypeController.dispose();
    _toolsController.dispose();
    super.dispose();
  }

  Future<void> _loadCurrentUser() async {
    final userId = _auth.currentUser?.uid;
    if (userId != null) {
      final user = await _socialService.getUserProfile(userId);
      setState(() {
        _currentUser = user;
      });
    }
  }

  Future<void> _pickImage() async {
    try {
      final XFile? image = await _imagePicker.pickImage(
        source: ImageSource.gallery,
        maxWidth: 1024,
        maxHeight: 1024,
        imageQuality: 85,
      );
      
      if (image != null) {
        setState(() {
          _selectedImage = File(image.path);
        });
      }
    } catch (e) {
      _showErrorSnackBar('Failed to pick image: $e');
    }
  }

  Future<void> _takePhoto() async {
    try {
      final XFile? image = await _imagePicker.pickImage(
        source: ImageSource.camera,
        maxWidth: 1024,
        maxHeight: 1024,
        imageQuality: 85,
      );
      
      if (image != null) {
        setState(() {
          _selectedImage = File(image.path);
        });
      }
    } catch (e) {
      _showErrorSnackBar('Failed to take photo: $e');
    }
  }

  void _showImageSourceDialog() {
    showModalBottomSheet(
      context: context,
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.camera_alt),
              title: const Text('Take Photo'),
              onTap: () {
                Navigator.pop(context);
                _takePhoto();
              },
            ),
            ListTile(
              leading: const Icon(Icons.photo_library),
              title: const Text('Choose from Gallery'),
              onTap: () {
                Navigator.pop(context);
                _pickImage();
              },
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _createPost() async {
    if (!_validateForm()) return;

    setState(() {
      _isLoading = true;
    });

    try {
      final userId = _auth.currentUser?.uid;
      if (userId == null) throw Exception('User not authenticated');

      // Ensure user profile exists
      if (_currentUser == null) {
        final user = _auth.currentUser;
        if (user != null) {
          final userProfile = UserModel(
            id: user.uid,
            email: user.email ?? '',
            displayName: user.displayName ?? 'User',
            photoURL: user.photoURL,
            createdAt: DateTime.now(),
            lastActive: DateTime.now(),
          );
          await _socialService.createUserProfile(userProfile);
          setState(() {
            _currentUser = userProfile;
          });
        }
      }

      final post = PostModel(
        id: _socialService.generateId(),
        userId: userId,
        title: _titleController.text.trim(),
        description: _descriptionController.text.trim(),
        deviceType: _deviceTypeController.text.trim(),
        difficulty: _selectedDifficulty,
        timeRequired: _timeRequired,
        toolsUsed: _toolsController.text.trim().split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList(),
        tags: _generateTags(),
        createdAt: DateTime.now(),
      );

      await _socialService.createPost(post, _selectedImage);
      
      if (mounted) {
        Navigator.pop(context);
        _showSuccessSnackBar('Post created successfully!');
      }
    } catch (e) {
      _showErrorSnackBar('Failed to create post: $e');
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  bool _validateForm() {
    if (_titleController.text.trim().isEmpty) {
      _showErrorSnackBar('Please enter a title');
      return false;
    }
    
    if (_descriptionController.text.trim().isEmpty) {
      _showErrorSnackBar('Please enter a description');
      return false;
    }
    
    if (_deviceTypeController.text.trim().isEmpty) {
      _showErrorSnackBar('Please enter the device type');
      return false;
    }
    
    return true;
  }

  List<String> _generateTags() {
    final tags = <String>[];
    
    // Add device type as tag
    tags.add(_deviceTypeController.text.trim().toLowerCase());
    
    // Add difficulty as tag
    tags.add(_selectedDifficulty.toLowerCase());
    
    // Add tools as tags
    tags.addAll(_toolsController.text.trim().split(',').map((e) => e.trim().toLowerCase()).where((e) => e.isNotEmpty));
    
    return tags;
  }

  void _showErrorSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.red,
      ),
    );
  }

  void _showSuccessSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.green,
      ),
    );
  }

  Future<void> _testFirebaseConnection() async {
    try {
      final results = await FirebaseTest.runAllTests();
      
      String message = 'Firebase Test Results:\n';
      results.forEach((test, result) {
        message += '${test.toUpperCase()}: ${result ? 'PASS' : 'FAIL'}\n';
      });
      
      _showErrorSnackBar(message);
    } catch (e) {
      _showErrorSnackBar('Test failed: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
             appBar: AppBar(
         title: const Text('Create Post'),
         backgroundColor: AppColors.background,
         elevation: 0,
         actions: [
           IconButton(
             onPressed: _testFirebaseConnection,
             icon: const Icon(Icons.bug_report),
             tooltip: 'Test Firebase Connection',
           ),
           TextButton(
             onPressed: _isLoading ? null : _createPost,
             child: _isLoading
                 ? const SizedBox(
                     width: 16,
                     height: 16,
                     child: CircularProgressIndicator(strokeWidth: 2),
                   )
                 : const Text(
                     'Post',
                     style: TextStyle(
                       color: AppColors.primary,
                       fontWeight: FontWeight.bold,
                     ),
                   ),
           ),
         ],
       ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Image picker
            _buildImagePicker(),
            
            const SizedBox(height: 24),
            
            // Title
            _buildTextField(
              controller: _titleController,
              label: 'Title',
              hint: 'What did you fix?',
              maxLines: 1,
            ),
            
            const SizedBox(height: 16),
            
            // Description
            _buildTextField(
              controller: _descriptionController,
              label: 'Description',
              hint: 'Tell us about your repair experience...',
              maxLines: 4,
            ),
            
            const SizedBox(height: 16),
            
            // Device type
            _buildTextField(
              controller: _deviceTypeController,
              label: 'Device Type',
              hint: 'e.g., iPhone 12, Samsung TV, MacBook Pro',
              maxLines: 1,
            ),
            
            const SizedBox(height: 16),
            
            // Difficulty
            _buildDifficultySelector(),
            
            const SizedBox(height: 16),
            
            // Time required
            _buildTimeSelector(),
            
            const SizedBox(height: 16),
            
            // Tools used
            _buildTextField(
              controller: _toolsController,
              label: 'Tools Used',
              hint: 'e.g., screwdriver, pliers, soldering iron (separate with commas)',
              maxLines: 2,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildImagePicker() {
    return Container(
      width: double.infinity,
      height: 200,
      decoration: BoxDecoration(
        color: Colors.grey[100],
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.grey[300]!),
      ),
      child: _selectedImage != null
          ? Stack(
              children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: Image.file(
                    _selectedImage!,
                    width: double.infinity,
                    height: 200,
                    fit: BoxFit.cover,
                  ),
                ),
                Positioned(
                  top: 8,
                  right: 8,
                  child: IconButton(
                    onPressed: () {
                      setState(() {
                        _selectedImage = null;
                      });
                    },
                    icon: const Icon(Icons.close),
                    style: IconButton.styleFrom(
                      backgroundColor: Colors.black54,
                      foregroundColor: Colors.white,
                    ),
                  ),
                ),
              ],
            )
          : InkWell(
              onTap: _showImageSourceDialog,
              borderRadius: BorderRadius.circular(12),
              child: const Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      Icons.add_a_photo,
                      size: 48,
                      color: AppColors.primary,
                    ),
                    SizedBox(height: 8),
                    Text(
                      'Add Photo',
                      style: TextStyle(
                        color: AppColors.primary,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              ),
            ),
    );
  }

  Widget _buildTextField({
    required TextEditingController controller,
    required String label,
    required String hint,
    int maxLines = 1,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(
            fontWeight: FontWeight.bold,
            fontSize: 16,
          ),
        ),
        const SizedBox(height: 8),
        TextField(
          controller: controller,
          maxLines: maxLines,
          decoration: InputDecoration(
            hintText: hint,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: const BorderSide(color: AppColors.primary),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildDifficultySelector() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Difficulty',
          style: TextStyle(
            fontWeight: FontWeight.bold,
            fontSize: 16,
          ),
        ),
        const SizedBox(height: 8),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12),
          decoration: BoxDecoration(
            border: Border.all(color: Colors.grey[300]!),
            borderRadius: BorderRadius.circular(12),
          ),
          child: DropdownButtonHideUnderline(
            child: DropdownButton<String>(
              value: _selectedDifficulty,
              isExpanded: true,
              items: _difficultyOptions.map((String difficulty) {
                return DropdownMenuItem<String>(
                  value: difficulty,
                  child: Text(difficulty),
                );
              }).toList(),
              onChanged: (String? newValue) {
                if (newValue != null) {
                  setState(() {
                    _selectedDifficulty = newValue;
                  });
                }
              },
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildTimeSelector() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Time Required (minutes)',
          style: TextStyle(
            fontWeight: FontWeight.bold,
            fontSize: 16,
          ),
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: Slider(
                value: _timeRequired.toDouble(),
                min: 5,
                max: 300,
                divisions: 59,
                label: '$_timeRequired min',
                onChanged: (value) {
                  setState(() {
                    _timeRequired = value.round();
                  });
                },
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: AppColors.primary.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                '$_timeRequired min',
                style: const TextStyle(
                  fontWeight: FontWeight.bold,
                  color: AppColors.primary,
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }
}
