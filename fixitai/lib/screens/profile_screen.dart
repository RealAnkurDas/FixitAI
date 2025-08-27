import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'dart:io';
import '../utils/app_colors.dart';
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

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
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
                    const SizedBox(height: 16),
                    
                    // User Name
                    Text(
                      name,
                      style: const TextStyle(
                        fontSize: 24,
                        fontWeight: FontWeight.bold,
                        color: AppColors.text,
                      ),
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
                        _buildStatItem('Fixes', '47'),
                        _buildStatItem('Likes', '234'),
                        _buildStatItem('Followers', '89'),
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
    return GridView.builder(
      padding: const EdgeInsets.all(16),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        crossAxisSpacing: 12,
        mainAxisSpacing: 12,
        childAspectRatio: 1,
      ),
      itemCount: 6,
      itemBuilder: (context, index) {
        return Container(
          decoration: BoxDecoration(
            color: Colors.grey[200],
            borderRadius: BorderRadius.circular(12),
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(
                Icons.build_circle,
                size: 40,
                color: AppColors.primary,
              ),
              const SizedBox(height: 8),
              Text(
                'Fix ${index + 1}',
                style: const TextStyle(
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildSavedTab() {
    return const Center(
      child: Text(
        'No saved posts yet',
        style: TextStyle(
          color: AppColors.textSecondary,
        ),
      ),
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
}
