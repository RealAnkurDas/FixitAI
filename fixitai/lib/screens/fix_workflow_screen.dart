import 'dart:io';
import 'package:flutter/material.dart';
import '../utils/app_colors.dart';
import '../widgets/custom_button.dart';
import '../widgets/difficulty_badge.dart';
import 'camera_screen.dart';

class FixWorkflowScreen extends StatefulWidget {
  const FixWorkflowScreen({super.key});

  @override
  State<FixWorkflowScreen> createState() => _FixWorkflowScreenState();
}

class _FixWorkflowScreenState extends State<FixWorkflowScreen> {
  int _currentStep = 0;
  final _problemController = TextEditingController();
  File? _capturedImage;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        children: [
          // Progress indicator
          LinearProgressIndicator(
            value: (_currentStep + 1) / 4,
            backgroundColor: Colors.grey[200],
            valueColor: const AlwaysStoppedAnimation<Color>(AppColors.primary),
          ),
          const SizedBox(height: 24),
          Expanded(
            child: _buildCurrentStep(),
          ),
        ],
      ),
    );
  }

  Widget _buildCurrentStep() {
    switch (_currentStep) {
      case 0:
        return _buildCameraStep();
      case 1:
        return _buildProcessingStep();
      case 2:
        return _buildSolutionStep();
      case 3:
        return _buildHumanHelpStep();
      default:
        return _buildCameraStep();
    }
  }

  void _openCamera() {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => CameraScreen(
          onImageCaptured: (File imageFile) {
            setState(() {
              _capturedImage = imageFile;
            });
          },
        ),
      ),
    );
  }

  Widget _buildCameraStep() {
    return Column(
      children: [
        Text(
          'Capture the Problem',
          style: Theme.of(context).textTheme.headlineMedium,
        ),
        const SizedBox(height: 24),
        Expanded(
          child: Container(
            width: double.infinity,
            decoration: BoxDecoration(
              color: Colors.grey[100],
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: Colors.grey[300]!),
            ),
            child: _capturedImage != null
                ? ClipRRect(
                    borderRadius: BorderRadius.circular(16),
                    child: Image.file(
                      _capturedImage!,
                      width: double.infinity,
                      height: double.infinity,
                      fit: BoxFit.cover,
                    ),
                  )
                : const Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        Icons.camera_alt,
                        size: 80,
                        color: AppColors.textSecondary,
                      ),
                      SizedBox(height: 16),
                      Text(
                        'Camera Preview',
                        style: TextStyle(
                          color: AppColors.textSecondary,
                          fontSize: 16,
                        ),
                      ),
                    ],
                  ),
          ),
        ),
        const SizedBox(height: 24),
        CustomButton(
          text: _capturedImage != null ? 'Retake Photo' : 'Capture Photo',
          onPressed: () => _openCamera(),
          icon: Icons.camera_alt,
        ),
        const SizedBox(height: 16),
        TextField(
          controller: _problemController,
          decoration: InputDecoration(
            hintText: 'Describe the problem...',
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
            ),
            suffixIcon: IconButton(
              icon: const Icon(Icons.mic, color: AppColors.primary),
              onPressed: () {},
            ),
          ),
          maxLines: 3,
        ),
        const SizedBox(height: 24),
        CustomButton(
          text: 'Analyze Problem',
          onPressed: _capturedImage != null 
            ? () => setState(() => _currentStep = 1) 
            : () {},
          backgroundColor: _capturedImage != null ? AppColors.primary : Colors.grey,
        ),
      ],
    );
  }

  Widget _buildProcessingStep() {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const CircularProgressIndicator(
          valueColor: AlwaysStoppedAnimation<Color>(AppColors.primary),
          strokeWidth: 3,
        ),
        const SizedBox(height: 32),
        Text(
          'Analyzing your problem...',
          style: Theme.of(context).textTheme.headlineMedium,
        ),
        const SizedBox(height: 16),
        const Text(
          'Our AI is processing your image and description',
          style: TextStyle(color: AppColors.textSecondary),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 48),
        // Simulate processing delay
        FutureBuilder(
          future: Future.delayed(const Duration(seconds: 3)),
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.done) {
              WidgetsBinding.instance.addPostFrameCallback((_) {
                setState(() => _currentStep = 2);
              });
            }
            return const SizedBox();
          },
        ),
      ],
    );
  }

  Widget _buildSolutionStep() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text(
              'Solution Found!',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const Spacer(),
            const DifficultyBadge(difficulty: 'Easy'),
          ],
        ),
        const SizedBox(height: 24),
        Expanded(
          child: Card(
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Step-by-step Instructions:',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 16,
                    ),
                  ),
                  const SizedBox(height: 16),
                  Expanded(
                    child: ListView(
                      children: const [
                        _StepTile(
                          stepNumber: 1,
                          title: 'Turn off the power',
                          description: 'Locate the circuit breaker and switch it off for safety.',
                        ),
                        _StepTile(
                          stepNumber: 2,
                          title: 'Remove the old component',
                          description: 'Carefully unscrew and remove the damaged part.',
                        ),
                        _StepTile(
                          stepNumber: 3,
                          title: 'Install the replacement',
                          description: 'Attach the new component and secure it properly.',
                        ),
                        _StepTile(
                          stepNumber: 4,
                          title: 'Test the repair',
                          description: 'Turn the power back on and verify everything works.',
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            Expanded(
              child: CustomButton(
                text: 'Mark as Fixed',
                onPressed: () => setState(() => _currentStep = 0),
                backgroundColor: AppColors.secondary,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: CustomButton(
                text: 'Need More Help',
                onPressed: () => setState(() => _currentStep = 3),
                backgroundColor: AppColors.accent,
                textColor: AppColors.text,
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildHumanHelpStep() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Find Local Help',
          style: Theme.of(context).textTheme.headlineMedium,
        ),
        const SizedBox(height: 24),
        Expanded(
          child: ListView.builder(
            itemCount: 3,
            itemBuilder: (context, index) {
              return Card(
                margin: const EdgeInsets.only(bottom: 12),
                child: ListTile(
                  leading: CircleAvatar(
                    backgroundColor: AppColors.primary,
                    child: Text(
                      '${index + 1}',
                      style: const TextStyle(color: Colors.white),
                    ),
                  ),
                  title: Text('Local Fixer ${index + 1}'),
                  subtitle: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('${(index + 1) * 0.5} miles away'),
                      Row(
                        children: [
                          const Icon(Icons.star, color: AppColors.accent, size: 16),
                          Text(' 4.${8 - index} (${20 + index * 5} reviews)'),
                        ],
                      ),
                    ],
                  ),
                  trailing: ElevatedButton(
                    onPressed: () {},
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.primary,
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    ),
                    child: const Text('Contact', style: TextStyle(color: Colors.white)),
                  ),
                ),
              );
            },
          ),
        ),
        const SizedBox(height: 16),
        CustomButton(
          text: 'Back to Camera',
          onPressed: () => setState(() => _currentStep = 0),
          backgroundColor: Colors.grey[300]!,
          textColor: AppColors.text,
        ),
      ],
    );
  }
}

class _StepTile extends StatelessWidget {
  final int stepNumber;
  final String title;
  final String description;

  const _StepTile({
    required this.stepNumber,
    required this.title,
    required this.description,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 24,
            height: 24,
            decoration: const BoxDecoration(
              color: AppColors.primary,
              shape: BoxShape.circle,
            ),
            child: Center(
              child: Text(
                '$stepNumber',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 14,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  description,
                  style: const TextStyle(
                    color: AppColors.textSecondary,
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
