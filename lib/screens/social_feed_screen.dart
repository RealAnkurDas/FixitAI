import 'package:flutter/material.dart';
import '../utils/app_colors.dart';
import '../widgets/post_card.dart';

class SocialFeedScreen extends StatelessWidget {
  const SocialFeedScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: RefreshIndicator(
        onRefresh: () async {
          // Simulate refresh
          await Future.delayed(const Duration(seconds: 1));
        },
        child: ListView.builder(
          padding: const EdgeInsets.all(16),
          itemCount: 10,
          itemBuilder: (context, index) {
            return PostCard(
              userAvatar: 'https://placeholder.svg?height=40&width=40&query=user+avatar',
              userName: 'User ${index + 1}',
              postImage: 'https://placeholder.svg?height=200&width=300&query=repair+project',
              title: 'Fixed my ${_getRandomItem()} today!',
              description: 'Here\'s how I managed to repair it step by step...',
              likes: (index + 1) * 12,
              comments: (index + 1) * 3,
            );
          },
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {},
        backgroundColor: AppColors.primary,
        child: const Icon(Icons.add, color: Colors.white),
      ),
    );
  }

  String _getRandomItem() {
    final items = ['washing machine', 'bike', 'laptop', 'car', 'phone', 'TV', 'faucet'];
    return items[DateTime.now().millisecond % items.length];
  }
}
