import 'dart:io';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:permission_handler/permission_handler.dart';
import '../utils/app_colors.dart';

class CameraScreen extends StatefulWidget {
  final Function(File) onImageCaptured;
  
  const CameraScreen({
    super.key,
    required this.onImageCaptured,
  });

  @override
  State<CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen> {
  CameraController? _controller;
  List<CameraDescription>? _cameras;
  bool _isInitialized = false;
  bool _isCapturing = false;

  @override
  void initState() {
    super.initState();
    _initializeCamera();
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  Future<void> _initializeCamera() async {
    // Request camera permission
    final status = await Permission.camera.request();
    if (status != PermissionStatus.granted) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Camera permission is required to capture photos'),
            backgroundColor: Colors.red,
          ),
        );
        Navigator.of(context).pop();
      }
      return;
    }

    try {
      _cameras = await availableCameras();
      if (_cameras != null && _cameras!.isNotEmpty) {
        _controller = CameraController(
          _cameras![0],
          ResolutionPreset.high,
          enableAudio: false,
        );
        
        await _controller!.initialize();
        
        if (mounted) {
          setState(() {
            _isInitialized = true;
          });
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to initialize camera: $e'),
            backgroundColor: Colors.red,
          ),
        );
        Navigator.of(context).pop();
      }
    }
  }

  Future<void> _captureImage() async {
    if (_controller == null || !_isInitialized || _isCapturing) return;

    setState(() {
      _isCapturing = true;
    });

    try {
      final XFile image = await _controller!.takePicture();
      final File imageFile = File(image.path);
      
      if (mounted) {
        widget.onImageCaptured(imageFile);
        Navigator.of(context).pop();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to capture image: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isCapturing = false;
        });
      }
    }
  }

  Future<void> _switchCamera() async {
    if (_cameras == null || _cameras!.length < 2) return;

    final currentIndex = _cameras!.indexOf(_controller!.description);
    final newIndex = (currentIndex + 1) % _cameras!.length;

    await _controller!.dispose();
    _controller = CameraController(
      _cameras![newIndex],
      ResolutionPreset.high,
      enableAudio: false,
    );

    await _controller!.initialize();
    if (mounted) {
      setState(() {});
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: Stack(
          children: [
            // Camera preview
            if (_isInitialized && _controller != null)
              CameraPreview(_controller!)
            else
              const Center(
                child: CircularProgressIndicator(
                  color: AppColors.primary,
                ),
              ),
            
            // Top controls
            Positioned(
              top: 0,
              left: 0,
              right: 0,
              child: Container(
                padding: const EdgeInsets.all(16),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    IconButton(
                      onPressed: () => Navigator.of(context).pop(),
                      icon: const Icon(
                        Icons.close,
                        color: Colors.white,
                        size: 30,
                      ),
                    ),
                    if (_cameras != null && _cameras!.length > 1)
                      IconButton(
                        onPressed: _switchCamera,
                        icon: const Icon(
                          Icons.flip_camera_ios,
                          color: Colors.white,
                          size: 30,
                        ),
                      ),
                  ],
                ),
              ),
            ),
            
            // Bottom controls
            Positioned(
              bottom: 0,
              left: 0,
              right: 0,
              child: Container(
                padding: const EdgeInsets.all(32),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    GestureDetector(
                      onTap: _isCapturing ? null : _captureImage,
                      child: Container(
                        width: 80,
                        height: 80,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          border: Border.all(
                            color: Colors.white,
                            width: 4,
                          ),
                          color: _isCapturing 
                            ? Colors.grey 
                            : Colors.white.withValues(alpha: 0.3),
                        ),
                        child: _isCapturing
                          ? const Center(
                              child: CircularProgressIndicator(
                                color: Colors.white,
                              ),
                            )
                          : const Icon(
                              Icons.camera,
                              color: Colors.white,
                              size: 40,
                            ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
