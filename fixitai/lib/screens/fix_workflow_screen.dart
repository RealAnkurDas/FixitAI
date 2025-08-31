import 'dart:io';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:http/http.dart' as http;
import 'package:path/path.dart' as path;
import '../utils/app_colors.dart';
import '../widgets/custom_button.dart';

class FixWorkflowScreen extends StatefulWidget {
  const FixWorkflowScreen({super.key});

  @override
  State<FixWorkflowScreen> createState() => _FixWorkflowScreenState();
}

class _FixWorkflowScreenState extends State<FixWorkflowScreen> {
  final _messageController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final List<ChatMessage> _messages = [];
  
  CameraController? _cameraController;
  List<CameraDescription>? _cameras;
  bool _isCameraInitialized = false;
  bool _isTyping = false;
  String? _cameraError;
  bool _useMockCamera = false;
  
  // API Configuration
  static const String baseUrl = 'https://prawn-correct-muskrat.ngrok-free.app/api';
  String? _sessionId;
  String? _lastUploadedImage;
  bool _isConnecting = false;
  
  // Track conversation state
  bool _isInGuidanceMode = false;

  @override
  void initState() {
    super.initState();
    _initializeCamera();
    _createSession();
  }

  Future<void> _createSession() async {
    setState(() {
      _isConnecting = true;
    });

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/session'),
        headers: {
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': 'true',  // Skip ngrok browser warning
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        setState(() {
          _sessionId = data['session_id'];
          _isConnecting = false;
        });
        _addAIMessage(data['message'] ?? "Hi! I'm your AI repair assistant. I can see through your camera and help you fix things. Point your camera at the problem and tell me what's broken!");
      } else {
        throw Exception('Failed to create session: ${response.statusCode}');
      }
    } catch (e) {
      setState(() {
        _isConnecting = false;
      });
      _addAIMessage("Connection error. Using offline mode. Describe your problem and I'll help as best I can!");
      print('Session creation error: $e');
    }
  }

  Future<void> _initializeCamera() async {
    try {
      _cameras = await availableCameras();
      if (_cameras != null && _cameras!.isNotEmpty) {
        _cameraController = CameraController(
          _cameras![0],
          ResolutionPreset.medium,
          enableAudio: false,
        );
        await _cameraController!.initialize();
        if (mounted) {
          setState(() {
            _isCameraInitialized = true;
          });
        }
      } else {
        setState(() {
          _cameraError = "No cameras available";
          _useMockCamera = true;
        });
      }
    } catch (e) {
      print('Error initializing camera: $e');
      setState(() {
        _cameraError = "Camera permission denied or not available";
        _useMockCamera = true;
      });
    }
  }

  @override
  void dispose() {
    _cameraController?.dispose();
    _messageController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _addAIMessage(String message) {
    setState(() {
      _messages.add(ChatMessage(message: message, isUser: false));
    });
    _scrollToBottom();
  }

  void _addUserMessage(String message) {
    setState(() {
      _messages.add(ChatMessage(message: message, isUser: true));
    });
    _scrollToBottom();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _captureAndUploadImage() async {
    if (_cameraController == null || !_cameraController!.value.isInitialized) {
      _addUserMessage("Taking a photo for analysis");
      _addAIMessage("I can see the issue better now. Please describe what specific problem you're experiencing.");
      return;
    }

    try {
      setState(() {
        _isTyping = true;
      });

      final XFile image = await _cameraController!.takePicture();
      _addUserMessage("📷 Photo captured for analysis");

      if (_sessionId != null) {
        await _uploadImage(File(image.path));
      } else {
        _addAIMessage("Photo captured! Please describe the problem you're seeing so I can help you fix it.");
      }
    } catch (e) {
      _addAIMessage("Couldn't capture photo, but I can still help! Please describe the problem.");
      print('Camera capture error: $e');
    } finally {
      setState(() {
        _isTyping = false;
      });
    }
  }

  Future<void> _uploadImage(File imageFile) async {
    if (_sessionId == null) return;

    try {
      var request = http.MultipartRequest('POST', Uri.parse('$baseUrl/upload'));
      request.fields['session_id'] = _sessionId!;
      request.files.add(await http.MultipartFile.fromPath('image', imageFile.path));

      var response = await request.send();
      var responseBody = await response.stream.bytesToString();

      if (response.statusCode == 200) {
        final data = json.decode(responseBody);
        setState(() {
          _lastUploadedImage = data['filename'];
        });
        _addAIMessage(data['message'] ?? "Image uploaded! Now tell me what's wrong.");
      } else {
        _addAIMessage("Image upload failed, but I can still help based on your description.");
      }
    } catch (e) {
      _addAIMessage("Couldn't upload image, but I can still help! Please describe what you see.");
      print('Upload error: $e');
    }
  }

  void _sendMessage() {
    final message = _messageController.text.trim();
    if (message.isNotEmpty) {
      _addUserMessage(message);
      _messageController.clear();
      
      // Show typing indicator
      setState(() {
        _isTyping = true;
      });
      
      if (_sessionId != null) {
        _sendToAPI(message);
      } else {
        // Fallback to mock responses
        Future.delayed(const Duration(milliseconds: 1500), () {
          if (mounted) {
            setState(() {
              _isTyping = false;
            });
            _generateMockResponse(message);
          }
        });
      }
    }
  }

  Future<void> _sendToAPI(String message) async {
    if (_sessionId == null) return;

    try {
      Map<String, dynamic> requestBody = {
        'message': message,
      };

      // Include last uploaded image if available for analysis calls
      if (_lastUploadedImage != null && !_isInGuidanceMode) {
        requestBody['image_filename'] = _lastUploadedImage;
      }

      // Choose endpoint based on current mode
      String endpoint = _isInGuidanceMode 
          ? '$baseUrl/session/$_sessionId/guide'
          : '$baseUrl/session/$_sessionId/analyze';

      print('Sending to endpoint: $endpoint');
      print('Request body: ${json.encode(requestBody)}');

      final response = await http.post(
        Uri.parse(endpoint),
        headers: {
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': 'true',  // Add this to skip ngrok warning
        },
        body: json.encode(requestBody),
      );

      print('Response status: ${response.statusCode}');
      print('Response body: ${response.body}');

      if (mounted) {
        setState(() {
          _isTyping = false;
        });

        if (response.statusCode == 200) {
          final data = json.decode(response.body);
          
          // Extract the response text properly
          String responseText = data['response'] ?? 
                               data['message'] ?? 
                               "I'm processing your request...";
          
          if (responseText.trim().isEmpty) {
            responseText = "I received your message but had trouble formulating a response. Can you try asking in a different way?";
          }
          
          _addAIMessage(responseText);
          
          // Clear the used image reference
          _lastUploadedImage = null;
          
          // Check if we've entered guidance mode
          if (data['ready_for_guidance'] == true || data['mode'] == 'conversational') {
            _isInGuidanceMode = true;
          }
          
          // Update guidance mode based on response
          if (data['current_step'] != null || data['conversation_length'] != null) {
            _isInGuidanceMode = true;
          }
          
        } else {
          print('Error response: ${response.body}');
          try {
            final errorData = json.decode(response.body);
            String errorMessage = errorData['error'] ?? 'Unknown error occurred';
            
            // Handle specific error cases
            if (response.statusCode == 400 && errorMessage.contains('Not in guidance mode')) {
              _isInGuidanceMode = false;
              _addAIMessage("Let me analyze your repair issue first. Please describe what's broken or upload an image.");
            } else {
              _addAIMessage("Sorry, I encountered an issue: $errorMessage");
            }
          } catch (e) {
            _addAIMessage("Sorry, I encountered a server error. Let me try to help with what I know...");
          }
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isTyping = false;
        });
        _addAIMessage("Connection error. Let me try to help based on what you've described...");
        _generateMockResponse(message);
      }
      print('API request error: $e');
    }
  }

  void _generateMockResponse(String userMessage) {
    // Fallback mock responses when API is unavailable
    String response;
    final lowerMessage = userMessage.toLowerCase();
    
    if (lowerMessage.contains('broken') || lowerMessage.contains('not working')) {
      response = "I understand something is broken. While I can't see the full details right now, can you describe what exactly isn't working? Is it making sounds, not turning on, or something else?";
    } else if (lowerMessage.contains('leak') || lowerMessage.contains('drip')) {
      response = "Water leaks can cause damage quickly. First, turn off the water supply if possible. Can you tell me where exactly you see the leak coming from?";
    } else if (lowerMessage.contains('wire') || lowerMessage.contains('electric')) {
      response = "⚠️ SAFETY FIRST: Please turn off the electrical power at the circuit breaker before we continue. Safety is our top priority with electrical issues.";
    } else if (lowerMessage.contains('screen') || lowerMessage.contains('display')) {
      response = "For display issues, try these steps: 1) Force restart by holding power button for 10 seconds, 2) Check all cable connections. What happens when you try these?";
    } else {
      response = "I want to help you fix this! Can you give me more specific details about what's wrong? The more information you provide, the better I can assist you.";
    }
    
    _addAIMessage(response);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey[50],
      body: SafeArea(
        child: Column(
          children: [
            // Camera Preview Section
            Container(
              height: MediaQuery.of(context).size.height * 0.4,
              margin: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.black,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.grey[300]!, width: 2),
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(14),
                child: _buildCameraContent(),
              ),
            ),
            
            // Chat Interface Section
            Expanded(
              child: Container(
                margin: const EdgeInsets.symmetric(horizontal: 16),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: Colors.grey[200]!),
                ),
                child: Column(
                  children: [
                    // Chat header
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: AppColors.primary,
                        borderRadius: const BorderRadius.only(
                          topLeft: Radius.circular(16),
                          topRight: Radius.circular(16),
                        ),
                      ),
                      child: Row(
                        children: [
                          Container(
                            width: 40,
                            height: 40,
                            decoration: const BoxDecoration(
                              color: Colors.white,
                              shape: BoxShape.circle,
                            ),
                            child: _isConnecting 
                                ? const SizedBox(
                                    width: 20,
                                    height: 20,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                      valueColor: AlwaysStoppedAnimation<Color>(AppColors.primary),
                                    ),
                                  )
                                : const Icon(
                                    Icons.smart_toy,
                                    color: AppColors.primary,
                                    size: 24,
                                  ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Text(
                                  'AI Repair Assistant',
                                  style: TextStyle(
                                    color: Colors.white,
                                    fontWeight: FontWeight.bold,
                                    fontSize: 16,
                                  ),
                                ),
                                Text(
                                  _isConnecting 
                                      ? 'Connecting...' 
                                      : (_sessionId != null ? 'Online • Multi-Agent Ready' : 'Offline • Basic Help Available'),
                                  style: const TextStyle(
                                    color: Colors.white70,
                                    fontSize: 12,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          if (_sessionId != null)
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                              decoration: BoxDecoration(
                                color: Colors.green,
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: const Text(
                                'CONNECTED',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 10,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ),
                        ],
                      ),
                    ),
                    
                    // Chat messages
                    Expanded(
                      child: ListView.builder(
                        controller: _scrollController,
                        padding: const EdgeInsets.all(16),
                        itemCount: _messages.length + (_isTyping ? 1 : 0),
                        itemBuilder: (context, index) {
                          if (index == _messages.length && _isTyping) {
                            return _buildTypingIndicator();
                          }
                          return _buildChatMessage(_messages[index]);
                        },
                      ),
                    ),
                    
                    // Input area
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: Colors.grey[50],
                        border: Border(
                          top: BorderSide(color: Colors.grey[200]!),
                        ),
                      ),
                      child: Row(
                        children: [
                          Expanded(
                            child: TextField(
                              controller: _messageController,
                              decoration: InputDecoration(
                                hintText: _sessionId != null 
                                    ? 'Describe the repair problem to the AI...'
                                    : 'Describe your problem (offline mode)...',
                                border: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(24),
                                  borderSide: BorderSide.none,
                                ),
                                filled: true,
                                fillColor: Colors.white,
                                contentPadding: const EdgeInsets.symmetric(
                                  horizontal: 16,
                                  vertical: 12,
                                ),
                              ),
                              maxLines: null,
                              textCapitalization: TextCapitalization.sentences,
                              onSubmitted: (_) => _sendMessage(),
                            ),
                          ),
                          const SizedBox(width: 8),
                          IconButton(
                            onPressed: _sendMessage,
                            icon: const Icon(Icons.send),
                            style: IconButton.styleFrom(
                              backgroundColor: AppColors.primary,
                              foregroundColor: Colors.white,
                              padding: const EdgeInsets.all(12),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }

  Widget _buildCameraContent() {
    if (_useMockCamera || _cameraError != null) {
      return _buildMockCamera();
    }
    
    if (_isCameraInitialized && _cameraController != null) {
      return Stack(
        children: [
          FittedBox(
            fit: BoxFit.cover,
            child: SizedBox(
              width: _cameraController!.value.previewSize!.width+50,
              height: _cameraController!.value.previewSize!.height+265,
              child: CameraPreview(_cameraController!),
            ),
          ),
          _buildCameraOverlay(),
        ],
      );
    }
    
    return _buildLoadingCamera();
  }

  Widget _buildMockCamera() {
    return Container(
      color: Colors.grey[800],
      child: Stack(
        children: [
          Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  Icons.camera_alt_outlined,
                  size: 64,
                  color: Colors.grey[400],
                ),
                const SizedBox(height: 16),
                Text(
                  _cameraError ?? 'Camera Preview',
                  style: TextStyle(
                    color: Colors.grey[300],
                    fontSize: 16,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 8),
                Text(
                  'The AI can still help based on your description',
                  style: TextStyle(
                    color: Colors.grey[400],
                    fontSize: 12,
                  ),
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
          _buildCameraOverlay(),
        ],
      ),
    );
  }

  Widget _buildLoadingCamera() {
    return const Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          CircularProgressIndicator(
            color: AppColors.primary,
          ),
          SizedBox(height: 16),
          Text(
            'Initializing camera...',
            style: TextStyle(
              color: Colors.white70,
              fontSize: 14,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCameraOverlay() {
    return Stack(
      children: [
        // AI status indicator
        Positioned(
          top: 16,
          left: 16,
          child: Container(
            padding: const EdgeInsets.symmetric(
              horizontal: 12,
              vertical: 6,
            ),
            decoration: BoxDecoration(
              color: Colors.black54,
              borderRadius: BorderRadius.circular(20),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    color: _sessionId != null ? AppColors.secondary : Colors.orange,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 6),
                Text(
                  _sessionId != null 
                      ? (_useMockCamera ? 'AI Connected' : 'AI Watching')
                      : 'AI Offline',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
        ),
        // Capture/retry button
        Positioned(
          bottom: 16,
          right: 16,
          child: FloatingActionButton(
            mini: true,
            backgroundColor: AppColors.primary,
            onPressed: () {
              if (_useMockCamera && _cameraError != null) {
                // Retry camera initialization
                setState(() {
                  _useMockCamera = false;
                  _cameraError = null;
                  _isCameraInitialized = false;
                });
                _initializeCamera();
              } else {
                _captureAndUploadImage();
              }
            },
            child: Icon(
              _useMockCamera && _cameraError != null ? Icons.refresh : Icons.camera_alt,
              color: Colors.white,
              size: 20,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildChatMessage(ChatMessage message) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Row(
        mainAxisAlignment: message.isUser 
            ? MainAxisAlignment.end 
            : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (!message.isUser) ...[
            Container(
              width: 32,
              height: 32,
              decoration: const BoxDecoration(
                color: AppColors.primary,
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.smart_toy,
                color: Colors.white,
                size: 16,
              ),
            ),
            const SizedBox(width: 8),
          ],
          Flexible(
            child: Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: message.isUser 
                    ? AppColors.primary 
                    : Colors.grey[100],
                borderRadius: BorderRadius.circular(16),
              ),
              child: Text(
                message.message,
                style: TextStyle(
                  color: message.isUser ? Colors.white : AppColors.text,
                  fontSize: 14,
                ),
              ),
            ),
          ),
          if (message.isUser) ...[
            const SizedBox(width: 8),
            Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: Colors.grey[300],
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.person,
                color: Colors.grey,
                size: 16,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildTypingIndicator() {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 32,
            height: 32,
            decoration: const BoxDecoration(
              color: AppColors.primary,
              shape: BoxShape.circle,
            ),
            child: const Icon(
              Icons.smart_toy,
              color: Colors.white,
              size: 16,
            ),
          ),
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.grey[100],
              borderRadius: BorderRadius.circular(16),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    valueColor: AlwaysStoppedAnimation<Color>(
                      Colors.grey[600]!,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  _sessionId != null ? 'AI agents are analyzing...' : 'AI is thinking...',
                  style: TextStyle(
                    color: Colors.grey[600],
                    fontSize: 14,
                    fontStyle: FontStyle.italic,
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

class ChatMessage {
  final String message;
  final bool isUser;

  ChatMessage({required this.message, required this.isUser});
}