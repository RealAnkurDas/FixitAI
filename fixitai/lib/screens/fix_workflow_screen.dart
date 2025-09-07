import 'dart:io';
import 'dart:convert';
import 'dart:async';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:path/path.dart' as path;
import 'package:image_picker/image_picker.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:firebase_auth/firebase_auth.dart';
import '../utils/app_colors.dart';
import '../services/location_service.dart';
import 'location_picker_screen.dart';
import 'social/create_post_screen.dart';

class FixWorkflowScreen extends StatefulWidget {
  const FixWorkflowScreen({super.key});

  @override
  State<FixWorkflowScreen> createState() => _FixWorkflowScreenState();
}

class _FixWorkflowScreenState extends State<FixWorkflowScreen>
    with TickerProviderStateMixin {
  final _messageController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final ImagePicker _imagePicker = ImagePicker();
  final FirebaseAuth _auth = FirebaseAuth.instance;
  
  // Session Management
  List<ChatSession> sessions = [];
  ChatSession? currentSession;
  bool isSidebarOpen = false;
  
  // Animation controllers
  late AnimationController _sidebarAnimationController;
  late Animation<double> _sidebarAnimation;
  late Animation<Offset> _chatSlideAnimation;
  
  // Chat state
  List<ChatMessage> messages = [];
  bool isLoading = false;
  String? sessionId;
  String loadingDots = '';
  Timer? _loadingTimer;
  File? selectedImage;
  
  // Demo progress messages
  List<String> demoProgressMessages = [
    "🔍 Running research agent...",
    "📚 Checking iFixit manuals...",
    "📖 Checking WikiHow guides...",
    "🔧 Searching repair databases...",
    "📋 Collecting results...",
    "🧠 Analyzing findings...",
    "⚙️ Crafting repair plan...",
    "✅ Finalizing solution..."
  ];
  int currentProgressIndex = 0;
  bool showingProgress = false;
  
  // API Configuration - Updated to use FixAgent API via ngrok
  static const String baseUrl = 'https://fermin-unlegible-unrefreshingly.ngrok-free.app/api';

  @override
  void initState() {
    super.initState();
    
    // Initialize animation controllers
    _sidebarAnimationController = AnimationController(
      duration: const Duration(milliseconds: 300),
      vsync: this,
    );
    
    _sidebarAnimation = Tween<double>(
      begin: 0.0,
      end: 0.8, // 80% of screen width
    ).animate(CurvedAnimation(
      parent: _sidebarAnimationController,
      curve: Curves.easeInOut,
    ));
    
    _chatSlideAnimation = Tween<Offset>(
      begin: Offset.zero,
      end: const Offset(0.8, 0.0), // Slide right by 80%
    ).animate(CurvedAnimation(
      parent: _sidebarAnimationController,
      curve: Curves.easeInOut,
    ));
    
    // Ensure sidebar starts closed
    _sidebarAnimationController.value = 0.0;
    
    // Load saved sessions and create initial session
    _loadSavedSessions();
    
    // Load user's last query if available
    _loadUserLastQuery();
  }

  @override
  void dispose() {
    _sidebarAnimationController.dispose();
    _messageController.dispose();
    _scrollController.dispose();
    _loadingTimer?.cancel();
    super.dispose();
  }

  void _toggleSidebar() {
    setState(() {
      isSidebarOpen = !isSidebarOpen;
      if (isSidebarOpen) {
        _sidebarAnimationController.forward();
      } else {
        _sidebarAnimationController.reverse();
      }
    });
  }

  // Session persistence methods
  Future<void> _loadSavedSessions() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final sessionsJson = prefs.getStringList('chat_sessions') ?? [];
      
      final loadedSessions = <ChatSession>[];
      for (final sessionJson in sessionsJson) {
        try {
          final sessionData = json.decode(sessionJson);
          final messages = <ChatMessage>[];
          
          for (final messageData in sessionData['messages']) {
            messages.add(ChatMessage(
              message: messageData['message'],
              isUser: messageData['isUser'],
              imageFile: null, // Images can't be saved to SharedPreferences, so they'll be lost on restart
              responseSource: messageData['responseSource'],
              localRepairAvailable: messageData['localRepairAvailable'] ?? false,
            ));
          }
          
          loadedSessions.add(ChatSession(
            id: sessionData['id'],
            title: sessionData['title'],
            timestamp: DateTime.parse(sessionData['timestamp']),
            messages: messages,
          ));
        } catch (e) {
          print('Error parsing session: $e');
        }
      }
      
      setState(() {
        sessions = loadedSessions;
      });
      
      // Always create a new session when app opens
      await _createNewSession();
    } catch (e) {
      print('Error loading sessions: $e');
      _createNewSession();
    }
  }

  Future<void> _loadUserLastQuery() async {
    try {
      final user = _auth.currentUser;
      if (user?.uid == null) return;
      
      print('DEBUG: Loading last query for user: ${user!.uid}');
      
      final response = await http.get(
        Uri.parse('$baseUrl/user/${user.uid}/last-query'),
        headers: {'Content-Type': 'application/json'},
      );
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data['success'] == true) {
          final lastQuery = data['query'];
          print('DEBUG: Found last query: $lastQuery');
          
          // Optionally show the last query to the user
          // You can customize this behavior based on your UX requirements
          if (lastQuery.isNotEmpty && messages.isEmpty) {
            // Add a suggestion message if no messages exist yet
            final suggestionMessage = ChatMessage(
              message: "💡 Last time you asked: \"$lastQuery\"\n\nWould you like to continue with this repair or ask something new?",
              isUser: false,
              responseSource: "system",
            );
            
            setState(() {
              messages.add(suggestionMessage);
              if (currentSession != null) {
                currentSession!.addMessage(suggestionMessage);
              }
            });
          }
        }
      } else if (response.statusCode == 404) {
        print('DEBUG: No previous query found for user');
      } else {
        print('DEBUG: Failed to load last query: ${response.statusCode}');
      }
    } catch (e) {
      print('DEBUG: Error loading user last query: $e');
    }
  }

  Future<void> _saveSessions() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final sessionsJson = sessions.map((session) {
        return json.encode({
          'id': session.id,
          'title': session.title,
          'timestamp': session.timestamp.toIso8601String(),
          'messages': session.messages.map((message) {
            return {
              'message': message.message,
              'isUser': message.isUser,
              'responseSource': message.responseSource,
              'localRepairAvailable': message.localRepairAvailable,
            };
          }).toList(),
        });
      }).toList();
      
      await prefs.setStringList('chat_sessions', sessionsJson);
    } catch (e) {
      print('Error saving sessions: $e');
    }
  }

  void _startLoadingAnimation() {
    _loadingTimer?.cancel();
    currentProgressIndex = 0;
    showingProgress = true;
    
    // Randomly select 5-8 progress messages
    final random = Random();
    final numSteps = random.nextInt(4) + 5; // 5-8 steps
    final selectedSteps = demoProgressMessages.take(numSteps).toList();
    
    int stepIndex = 0;
    _loadingTimer = Timer.periodic(const Duration(milliseconds: 800), (timer) {
      if (stepIndex < selectedSteps.length) {
        setState(() {
          loadingDots = selectedSteps[stepIndex];
        });
        stepIndex++;
      } else {
        timer.cancel();
      }
    });
  }

  void _stopLoadingAnimation() {
    _loadingTimer?.cancel();
    setState(() {
      loadingDots = '';
      showingProgress = false;
    });
  }

  Future<void> _createNewSession() async {
    try {
      // Create session on the backend first
      final sessionResponse = await http.post(
        Uri.parse('$baseUrl/session'),
        headers: {'Content-Type': 'application/json'},
      );
      
      if (sessionResponse.statusCode == 200) {
        final sessionData = json.decode(sessionResponse.body);
        final newSessionId = sessionData['session_id'];
        
        final newSession = ChatSession(
          id: newSessionId,
          title: 'New Session ${sessions.length + 1}',
          timestamp: DateTime.now(),
          messages: [],
        );
        
        setState(() {
          sessions.add(newSession);
          currentSession = newSession;
          messages = [];
          sessionId = newSessionId;
        });
        
        // Send initial greeting
        _sendInitialGreeting();
      } else {
        throw Exception('Failed to create session: ${sessionResponse.statusCode}');
      }
    } catch (e) {
      print('Error creating session: $e');
      
      // Show error to user instead of creating local session
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to create session. Please check your connection and try again.'),
            backgroundColor: Colors.red,
            duration: const Duration(seconds: 3),
            behavior: SnackBarBehavior.floating,
            margin: EdgeInsets.only(
              bottom: MediaQuery.of(context).size.height - 150,
              left: 16,
              right: 16,
            ),
          ),
        );
      }
      
      // Don't create a local session - this causes ID mismatches
      // Instead, just show an error state
    }
  }

  Future<void> _selectSession(ChatSession session) async {
    try {
      // Fetch conversation history from backend
      final response = await http.get(
        Uri.parse('$baseUrl/session/${session.id}/history'),
        headers: {'Content-Type': 'application/json'},
      );
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final history = data['conversation_history'] as List<dynamic>;
        
        // Convert history to ChatMessage objects
        final historyMessages = history.map((msg) => ChatMessage(
          message: msg['message'],
          isUser: msg['isUser'],
          imageFile: null, // Images from backend history won't have file references
        )).toList();
        
        setState(() {
          currentSession = session;
          session.updateMessages(historyMessages);
          messages = List.from(historyMessages);
          sessionId = session.id;
        });
      } else {
        // Fallback to local messages if backend fails
        setState(() {
          currentSession = session;
          messages = List.from(session.messages);
          sessionId = session.id;
        });
      }
    } catch (e) {
      print('Error fetching session history: $e');
      // Fallback to local messages
      setState(() {
        currentSession = session;
        messages = List.from(session.messages);
        sessionId = session.id;
      });
    }
    
    _toggleSidebar();
  }

  Future<void> _deleteSession(ChatSession session) async {
    // Show confirmation dialog
    final shouldDelete = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Session'),
        content: Text('Are you sure you want to delete "${session.title}"? This action cannot be undone.'),
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
      // Delete from backend
      final response = await http.delete(
        Uri.parse('$baseUrl/session/${session.id}'),
        headers: {'Content-Type': 'application/json'},
      );
      
      if (response.statusCode != 200 && response.statusCode != 404) {
        print('Failed to delete session from backend: ${response.statusCode}');
      }

      // Remove from local sessions
      setState(() {
        sessions.remove(session);
        
        // If we deleted the current session, switch to the first available session
        if (currentSession?.id == session.id) {
          if (sessions.isNotEmpty) {
            currentSession = sessions.first;
            sessionId = currentSession!.id;
            messages = List.from(currentSession!.messages);
          } else {
            currentSession = null;
            sessionId = null;
            messages = [];
          }
        }
      });

      // Save updated sessions
      await _saveSessions();

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text('Session deleted successfully'),
            backgroundColor: Colors.green,
            behavior: SnackBarBehavior.floating,
            margin: EdgeInsets.only(
              bottom: MediaQuery.of(context).size.height - 150,
              left: 16,
              right: 16,
            ),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to delete session: $e'),
            backgroundColor: Colors.red,
            behavior: SnackBarBehavior.floating,
            margin: EdgeInsets.only(
              bottom: MediaQuery.of(context).size.height - 150,
              left: 16,
              right: 16,
            ),
          ),
        );
      }
    }
  }

  void _sendInitialGreeting() {
    final greeting = ChatMessage(
      message: "Hello! I'm your AI repair assistant. I can help you diagnose and fix issues with your devices. You can:\n\n• Describe the problem you're experiencing\n• Upload photos of the issue\n• Ask for step-by-step repair instructions\n\nWhat can I help you with today?",
      isUser: false,
    );
    
    setState(() {
      messages.add(greeting);
      if (currentSession != null) {
        currentSession!.messages.add(greeting);
      }
    });
  }

  Future<void> _sendMessage() async {
    // Don't send if no text and no image, or if only image without text
    if (_messageController.text.trim().isEmpty && selectedImage == null) return;
    if (selectedImage != null && _messageController.text.trim().isEmpty) return;

    String messageText = _messageController.text.trim();
    
    // Store image reference before clearing it
    final imageToSend = selectedImage;
    
    // Debug: Print current state
    print('DEBUG: Sending message: "$messageText"');
    print('DEBUG: Current sessionId: $sessionId');
    print('DEBUG: Has image: ${imageToSend != null}');

    final userMessage = ChatMessage(
      message: messageText,
      isUser: true,
      imageFile: imageToSend, // Include the selected image
    );

    setState(() {
      messages.add(userMessage);
      if (currentSession != null) {
        currentSession!.addMessage(userMessage);
      }
      isLoading = true;
    });
    _startLoadingAnimation();
    
    // Save sessions after adding message
    _saveSessions();

    _messageController.clear();
    selectedImage = null; // Clear the UI reference
    _scrollToBottom();

    try {
      // First ensure we have a session
      if (sessionId == null) {
        final sessionResponse = await http.post(
          Uri.parse('$baseUrl/session'),
          headers: {'Content-Type': 'application/json'},
        );
        
        if (sessionResponse.statusCode == 200) {
          final sessionData = json.decode(sessionResponse.body);
          sessionId = sessionData['session_id'];
        } else {
          throw Exception('Failed to create session');
        }
      }

      // Send message with image and text together
      http.Response response;
      
      if (imageToSend != null) {
        // Send image and text together in one request
        final multipartRequest = http.MultipartRequest(
          'POST',
          Uri.parse('$baseUrl/session/$sessionId/analyze'),
        );

        // Add session_id, message, and user_id as fields
        multipartRequest.fields['message'] = messageText;
        if (_auth.currentUser?.uid != null) {
          multipartRequest.fields['user_id'] = _auth.currentUser!.uid;
        }

        // Add image file
        final imageStream = http.ByteStream(imageToSend.openRead());
        final imageLength = await imageToSend.length();
        final multipartFile = http.MultipartFile(
          'image',
          imageStream,
          imageLength,
          filename: path.basename(imageToSend.path),
        );
        multipartRequest.files.add(multipartFile);

        final streamedResponse = await multipartRequest.send();
        response = await http.Response.fromStream(streamedResponse);
      } else {
        // Send text-only message
        final requestBody = <String, dynamic>{
          'message': messageText,
        };
        
        // Add user_id if available
        if (_auth.currentUser?.uid != null) {
          requestBody['user_id'] = _auth.currentUser!.uid;
        }
        
        response = await http.post(
          Uri.parse('$baseUrl/session/$sessionId/analyze'),
          headers: {'Content-Type': 'application/json'},
          body: json.encode(requestBody),
        );
      }

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        // Debug: Print received data
        print('DEBUG: Received API response:');
        print('  - response: ${data['response']?.substring(0, 100)}...');
        print('  - item_name: ${data['item_name']}');
        print('  - post_title: ${data['post_title']}');
        
        final aiMessage = ChatMessage(
          message: data['response'] ?? 'Sorry, I encountered an error.',
          isUser: false,
          responseSource: data['response_source'],
          localRepairAvailable: data['local_repair_available'] ?? false,
          itemName: data['item_name'],
          postTitle: data['post_title'],
        );

        setState(() {
          messages.add(aiMessage);
          if (currentSession != null) {
            currentSession!.addMessage(aiMessage);
          }
        });
        
        // Save sessions after AI response
        _saveSessions();
      } else {
        _addErrorMessage('Failed to get response from AI');
      }
    } catch (e) {
      print('DEBUG: Error in _sendMessage: $e');
      _addErrorMessage('Connection error. Please check your internet connection.');
    } finally {
      setState(() {
        isLoading = false;
      });
      _stopLoadingAnimation();
      _scrollToBottom();
    }
  }




  void _addErrorMessage(String message) {
    final errorMessage = ChatMessage(
      message: message,
      isUser: false,
    );
    setState(() {
      messages.add(errorMessage);
      if (currentSession != null) {
        currentSession!.messages.add(errorMessage);
      }
    });
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

  void _showImageDialog(File imageFile) {
    showDialog(
      context: context,
      builder: (BuildContext context) {
        return Dialog(
          backgroundColor: Colors.transparent,
          child: Stack(
            children: [
              // Full screen image
              Center(
                child: InteractiveViewer(
                  child: Image.file(
                    imageFile,
                    fit: BoxFit.contain,
                  ),
                ),
              ),
              // Close button
              Positioned(
                top: 40,
                right: 20,
                child: Container(
                  decoration: BoxDecoration(
                    color: Colors.black.withOpacity(0.5),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: IconButton(
                    icon: const Icon(Icons.close, color: Colors.white),
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
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
                title: const Text('Upload Image'),
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
        setState(() {
          selectedImage = File(photo.path);
        });
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text('Failed to take photo'),
          behavior: SnackBarBehavior.floating,
          margin: EdgeInsets.only(
            bottom: MediaQuery.of(context).size.height - 100,
            left: 16,
            right: 16,
          ),
        ),
      );
    }
  }

  Future<void> _pickImage() async {
    try {
      final XFile? image = await _imagePicker.pickImage(
        source: ImageSource.gallery,
        imageQuality: 80,
      );
      
      if (image != null) {
        setState(() {
          selectedImage = File(image.path);
        });
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text('Failed to pick image'),
          behavior: SnackBarBehavior.floating,
          margin: EdgeInsets.only(
            bottom: MediaQuery.of(context).size.height - 100,
            left: 16,
            right: 16,
          ),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey[50],
      body: Stack(
        children: [
          // Main chat area with slide animation
          AnimatedBuilder(
            animation: _chatSlideAnimation,
            builder: (context, child) {
              return Transform.translate(
                offset: Offset(
                  MediaQuery.of(context).size.width * _chatSlideAnimation.value.dx,
                  0,
                ),
                child: Container(
                  width: MediaQuery.of(context).size.width,
                  child: _buildChatArea(),
                ),
              );
            },
          ),
          
          // Sidebar overlay - only show when open
          if (isSidebarOpen)
            AnimatedBuilder(
              animation: _sidebarAnimation,
              builder: (context, child) {
                return Positioned(
                  left: 0,
                  top: 0,
                  bottom: 0,
                  width: MediaQuery.of(context).size.width * _sidebarAnimation.value,
                  child: Container(
                    decoration: BoxDecoration(
                      color: Colors.white,
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withOpacity(0.2),
                          blurRadius: 8,
                          offset: const Offset(2, 0),
                        ),
                      ],
                    ),
                    child: ClipRect(
                      child: _buildSidebar(),
                    ),
                  ),
                );
              },
            ),
        ],
      ),
    );
  }

  Widget _buildChatArea() {
    return SafeArea(
      child: Column(
        children: [
          // Chat header with floating sessions button
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white,
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.1),
                  blurRadius: 4,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: Row(
              children: [
                // Floating sessions button
                Container(
                  decoration: BoxDecoration(
                    color: AppColors.primary,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: IconButton(
                    icon: const Icon(Icons.history, color: Colors.white),
                    onPressed: _toggleSidebar,
                    tooltip: 'Previous Sessions',
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Text(
                    currentSession?.title ?? 'New Session',
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
          ),
          
          // Messages area
          Expanded(
            child: messages.isEmpty
                ? const Center(
                    child: Text(
                      'Start a conversation with your AI repair assistant',
                      style: TextStyle(
                        fontSize: 16,
                        color: Colors.grey,
                      ),
                    ),
                  )
                : ListView.builder(
                    controller: _scrollController,
                    padding: const EdgeInsets.all(16),
                    itemCount: messages.length,
                    itemBuilder: (context, index) {
                      final message = messages[index];
                      return _buildMessageBubble(message);
                    },
                  ),
          ),
          
                     // Loading indicator
           if (isLoading)
             Container(
               padding: const EdgeInsets.all(16),
               child: Row(
                 children: [
                   Container(
                     width: 32,
                     height: 32,
                     decoration: BoxDecoration(
                       color: AppColors.primary,
                       borderRadius: BorderRadius.circular(16),
                     ),
                     child: const Icon(
                       Icons.smart_toy,
                       color: Colors.white,
                       size: 20,
                     ),
                   ),
                   const SizedBox(width: 8),
                   Expanded(
                     child: Text(
                       loadingDots,
                       style: const TextStyle(
                         fontSize: 14,
                         color: Colors.grey,
                       ),
                     ),
                   ),
                 ],
               ),
             ),
          
          // Input area
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white,
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.1),
                  blurRadius: 4,
                  offset: const Offset(0, -2),
                ),
              ],
            ),
            child: Column(
              children: [
                // Image preview (if image is selected)
                if (selectedImage != null)
                  Container(
                    margin: const EdgeInsets.only(bottom: 8),
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: Colors.grey[50],
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: Colors.grey[300]!),
                    ),
                    child: Row(
                      children: [
                        // Mini image preview
                        Container(
                          width: 40,
                          height: 40,
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(4),
                            image: DecorationImage(
                              image: FileImage(selectedImage!),
                              fit: BoxFit.cover,
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        // Image info
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Image selected',
                                style: TextStyle(
                                  fontSize: 12,
                                  color: Colors.grey[600],
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                              Text(
                                path.basename(selectedImage!.path),
                                style: TextStyle(
                                  fontSize: 10,
                                  color: Colors.grey[500],
                                ),
                                overflow: TextOverflow.ellipsis,
                              ),
                            ],
                          ),
                        ),
                        // Remove image button
                        IconButton(
                          icon: const Icon(Icons.close, size: 16, color: Colors.grey),
                          onPressed: () {
                            setState(() {
                              selectedImage = null;
                            });
                          },
                          padding: EdgeInsets.zero,
                          constraints: const BoxConstraints(minWidth: 24, minHeight: 24),
                        ),
                      ],
                    ),
                  ),
                
                // Input row
                LayoutBuilder(
                  builder: (context, constraints) {
                    // If width is too small, show a simplified input
                    if (constraints.maxWidth < 200) {
                      return Row(
                        children: [
                          // Camera button
                          IconButton(
                            icon: const Icon(Icons.camera_alt, color: Colors.blue, size: 20),
                            onPressed: _showImageOptions,
                            padding: const EdgeInsets.all(8),
                            constraints: const BoxConstraints(minWidth: 40, minHeight: 40),
                          ),
                          const SizedBox(width: 4),
                          
                          // Text input
                          Expanded(
                            child: TextField(
                              controller: _messageController,
                              decoration: InputDecoration(
                                hintText: 'Message...',
                                border: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(20),
                                  borderSide: BorderSide.none,
                                ),
                                filled: true,
                                fillColor: Colors.grey[100],
                                contentPadding: const EdgeInsets.symmetric(
                                  horizontal: 12,
                                  vertical: 8,
                                ),
                              ),
                              maxLines: 1,
                              textInputAction: TextInputAction.send,
                              onSubmitted: (_) => _sendMessage(),
                            ),
                          ),
                          const SizedBox(width: 4),
                          
                          // Send button
                          ValueListenableBuilder<TextEditingValue>(
                            valueListenable: _messageController,
                            builder: (context, value, child) {
                              return IconButton(
                                icon: const Icon(Icons.send, color: AppColors.primary, size: 20),
                                onPressed: (value.text.trim().isNotEmpty) 
                                    ? _sendMessage 
                                    : null,
                                padding: const EdgeInsets.all(8),
                                constraints: const BoxConstraints(minWidth: 40, minHeight: 40),
                              );
                            },
                          ),
                        ],
                      );
                    } else {
                      // Normal input for larger screens
                      return Row(
                        children: [
                          // Camera button
                          IconButton(
                            icon: const Icon(Icons.camera_alt, color: Colors.blue),
                            onPressed: _showImageOptions,
                          ),
                          const SizedBox(width: 8),
                          
                          // Text input
                          Expanded(
                            child: TextField(
                              controller: _messageController,
                              decoration: InputDecoration(
                                hintText: 'Type your message...',
                                border: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(25),
                                  borderSide: BorderSide.none,
                                ),
                                filled: true,
                                fillColor: Colors.grey[100],
                                contentPadding: const EdgeInsets.symmetric(
                                  horizontal: 16,
                                  vertical: 12,
                                ),
                              ),
                              maxLines: null,
                              textInputAction: TextInputAction.send,
                              onSubmitted: (_) => _sendMessage(),
                            ),
                          ),
                          const SizedBox(width: 8),
                          
                          // Send button
                          ValueListenableBuilder<TextEditingValue>(
                            valueListenable: _messageController,
                            builder: (context, value, child) {
                              return IconButton(
                                icon: const Icon(Icons.send, color: AppColors.primary),
                                onPressed: (value.text.trim().isNotEmpty) 
                                    ? _sendMessage 
                                    : null,
                              );
                            },
                          ),
                        ],
                      );
                    }
                  },
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSidebar() {
    return Column(
      children: [
        // Sidebar header
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AppColors.primary,
          ),
          child: Row(
            children: [
              const Expanded(
                child: Text(
                  'Sessions',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              IconButton(
                icon: const Icon(Icons.close, color: Colors.white),
                onPressed: _toggleSidebar,
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(minWidth: 40, minHeight: 40),
              ),
            ],
          ),
        ),
        
        // Sessions list
        Expanded(
          child: sessions.isEmpty
              ? const Center(
                  child: Text(
                    'No previous sessions',
                    style: TextStyle(color: Colors.grey),
                  ),
                )
              : ListView.builder(
                  itemCount: sessions.length,
                  itemBuilder: (context, index) {
                    final session = sessions[index];
                    final isSelected = currentSession?.id == session.id;
                    
                                         return Container(
                       margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                       decoration: BoxDecoration(
                         color: isSelected ? Colors.blue.withOpacity(0.1) : Colors.transparent,
                         borderRadius: BorderRadius.circular(8),
                       ),
                       child: Material(
                         color: Colors.transparent,
                         child: InkWell(
                           borderRadius: BorderRadius.circular(8),
                           onTap: () => _selectSession(session),
                           child: Padding(
                             padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                             child: Row(
                               children: [
                                 Icon(
                                   isSelected ? Icons.chat_bubble : Icons.chat_bubble_outline,
                                   color: isSelected ? AppColors.primary : Colors.grey,
                                   size: 18,
                                 ),
                                 const SizedBox(width: 8),
                                 Expanded(
                                   child: Column(
                                     crossAxisAlignment: CrossAxisAlignment.start,
                                     children: [
                                       Text(
                                         session.title,
                                         style: TextStyle(
                                           fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                                           color: isSelected ? AppColors.primary : Colors.black,
                                           fontSize: 13,
                                         ),
                                         overflow: TextOverflow.ellipsis,
                                       ),
                                       Text(
                                         '${session.messages.length} messages',
                                         style: const TextStyle(fontSize: 10, color: Colors.grey),
                                         overflow: TextOverflow.ellipsis,
                                       ),
                                     ],
                                   ),
                                 ),
                                 if (sessions.length > 1) // Don't show delete for last session
                                   IconButton(
                                     onPressed: () => _deleteSession(session),
                                     icon: const Icon(Icons.delete_outline, size: 16),
                                     tooltip: 'Delete Session',
                                     color: Colors.red,
                                     padding: EdgeInsets.zero,
                                     constraints: const BoxConstraints(minWidth: 24, minHeight: 24),
                                   ),
                               ],
                             ),
                           ),
                         ),
                       ),
                     );
                  },
                ),
        ),
        
        // New session button
        Container(
          padding: const EdgeInsets.all(12),
          child: SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: () {
                _createNewSession();
                _toggleSidebar();
              },
              icon: const Icon(Icons.add, size: 18),
              label: const Text('New Session', style: TextStyle(fontSize: 14)),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.primary,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 10),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildLocalRepairButton() {
    return Container(
      width: double.infinity,
      child: ElevatedButton.icon(
        onPressed: () => _searchLocalRepairShops(),
        icon: const Icon(Icons.store, size: 16),
        label: const Text('Local Repair'),
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.primary,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
          ),
        ),
      ),
    );
  }

  Widget _buildUpcycleButton() {
    return Container(
      width: double.infinity,
      child: ElevatedButton.icon(
        onPressed: () => _generateUpcycleIdeas(),
        icon: const Icon(Icons.recycling, size: 16),
        label: const Text('Upcycle Ideas'),
        style: ElevatedButton.styleFrom(
          backgroundColor: Colors.orange,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
          ),
        ),
      ),
    );
  }

  Widget _buildPostButton(ChatMessage message) {
    return Container(
      width: double.infinity,
      child: ElevatedButton.icon(
        onPressed: () => _navigateToCreatePost(message),
        icon: const Icon(Icons.share, size: 16),
        label: const Text('Share Fix'),
        style: ElevatedButton.styleFrom(
          backgroundColor: Colors.green,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
          ),
        ),
      ),
    );
  }

  Future<void> _navigateToCreatePost(ChatMessage message) async {
    try {
      // First, try to get LLM-generated data from the backend
      Map<String, dynamic> repairData = {};
      
      try {
        print('DEBUG: Fetching LLM-generated post data from backend...');
        final response = await http.get(
          Uri.parse('http://localhost:8000/api/post-data'),
          headers: {'Content-Type': 'application/json'},
        );
        
        if (response.statusCode == 200) {
          final postData = json.decode(response.body);
          print('DEBUG: Received post data from backend: $postData');
          
          if (postData['error'] == null) {
            // Use LLM-generated data
            repairData = {
              'title': postData['post_title'] ?? '',
              'description': postData['final_response'] ?? message.message,
              'itemName': postData['item_name'] ?? '',
            };
            print('DEBUG: Using LLM-generated data: $repairData');
          } else {
            print('DEBUG: No LLM data available, falling back to message extraction');
            repairData = _extractRepairDataFromMessage(message);
          }
        } else {
          print('DEBUG: Failed to fetch post data, falling back to message extraction');
          repairData = _extractRepairDataFromMessage(message);
        }
      } catch (e) {
        print('DEBUG: Error fetching post data: $e, falling back to message extraction');
        repairData = _extractRepairDataFromMessage(message);
      }
      
      // Navigate to create post screen with pre-filled data
      final result = await Navigator.push(
        context,
        MaterialPageRoute(
          builder: (context) => CreatePostScreen(
            preFilledData: repairData,
          ),
        ),
      );
      
      // Show success message if post was created
      if (result == true) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Post shared successfully!'),
            backgroundColor: Colors.green,
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to open post creation: $e'),
          backgroundColor: Colors.red,
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  Map<String, dynamic> _extractRepairDataFromMessage(ChatMessage message) {
    final repairData = <String, dynamic>{};
    
    // Debug: Print message data
    print('DEBUG: Extracting repair data from message:');
    print('  - postTitle: ${message.postTitle}');
    print('  - itemName: ${message.itemName}');
    
    // Use LLM-generated title if available, otherwise leave empty
    if (message.postTitle != null && message.postTitle!.isNotEmpty) {
      repairData['title'] = message.postTitle!;
      print('DEBUG: Using LLM-generated title: ${message.postTitle}');
    } else {
      print('DEBUG: No LLM-generated title available, leaving title field empty');
      repairData['title'] = ''; // Explicitly set empty instead of fallback
    }
    
    // Use the full message as description
    repairData['description'] = message.message;
    
    // Use LLM-extracted item name if available, otherwise try to extract from message
    if (message.itemName != null && message.itemName!.isNotEmpty) {
      repairData['itemName'] = message.itemName!;
    } else {
      final itemType = _extractItemType(message.message);
      if (itemType.isNotEmpty) {
        repairData['itemName'] = itemType;
      }
    }
    
    // Try to extract tools from the message
    final tools = _extractTools(message.message);
    if (tools.isNotEmpty) {
      repairData['tools'] = tools.join(', ');
    }
    
    // Set default difficulty and time
    repairData['difficulty'] = 'Medium';
    repairData['timeRequired'] = 30;
    
    // Include the image if available
    if (message.imageFile != null) {
      repairData['imageFile'] = message.imageFile;
    }
    
    print('DEBUG: Final repair data being passed to CreatePostScreen: $repairData');
    return repairData;
  }

  String _extractItemType(String message) {
    // Common item patterns
    final itemPatterns = [
      RegExp(r'(iPhone\s+\d+)', caseSensitive: false),
      RegExp(r'(Samsung\s+\w+)', caseSensitive: false),
      RegExp(r'(MacBook\s+\w+)', caseSensitive: false),
      RegExp(r'(iPad\s+\w*)', caseSensitive: false),
      RegExp(r'(Dell\s+\w+)', caseSensitive: false),
      RegExp(r'(HP\s+\w+)', caseSensitive: false),
      RegExp(r'(Lenovo\s+\w+)', caseSensitive: false),
      RegExp(r'(office chair)', caseSensitive: false),
      RegExp(r'(dining chair)', caseSensitive: false),
      RegExp(r'(chair)', caseSensitive: false),
      RegExp(r'(bicycle)', caseSensitive: false),
      RegExp(r'(bike)', caseSensitive: false),
      RegExp(r'(car)', caseSensitive: false),
      RegExp(r'(laptop)', caseSensitive: false),
      RegExp(r'(phone)', caseSensitive: false),
      RegExp(r'(tablet)', caseSensitive: false),
      RegExp(r'(computer)', caseSensitive: false),
      RegExp(r'(TV)', caseSensitive: false),
      RegExp(r'(television)', caseSensitive: false),
      RegExp(r'(monitor)', caseSensitive: false),
      RegExp(r'(watch)', caseSensitive: false),
      RegExp(r'(headphones)', caseSensitive: false),
      RegExp(r'(earphones)', caseSensitive: false),
    ];
    
    for (final pattern in itemPatterns) {
      final match = pattern.firstMatch(message);
      if (match != null) {
        return match.group(1) ?? match.group(0) ?? '';
      }
    }
    
    return '';
  }

  List<String> _extractTools(String message) {
    final tools = <String>[];
    
    // Common tool patterns
    final toolPatterns = [
      RegExp(r'(screwdriver)', caseSensitive: false),
      RegExp(r'(pliers)', caseSensitive: false),
      RegExp(r'(soldering iron)', caseSensitive: false),
      RegExp(r'(multimeter)', caseSensitive: false),
      RegExp(r'(heat gun)', caseSensitive: false),
      RegExp(r'(pry tool)', caseSensitive: false),
      RegExp(r'(spudger)', caseSensitive: false),
      RegExp(r'(tweezers)', caseSensitive: false),
      RegExp(r'(torx driver)', caseSensitive: false),
      RegExp(r'(phillips head)', caseSensitive: false),
    ];
    
    for (final pattern in toolPatterns) {
      final match = pattern.firstMatch(message);
      if (match != null) {
        final tool = match.group(1) ?? match.group(0) ?? '';
        if (!tools.contains(tool.toLowerCase())) {
          tools.add(tool);
        }
      }
    }
    
    return tools;
  }

  Future<void> _generateUpcycleIdeas() async {
    try {
      // Show loading dialog
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (BuildContext context) {
          return const AlertDialog(
            content: Row(
              children: [
                CircularProgressIndicator(),
                SizedBox(width: 20),
                Text('Generating upcycling ideas...'),
              ],
            ),
          );
        },
      );

      // Call the UpcycleIdeasTool API endpoint
      final requestBody = <String, dynamic>{};
      
      // Add user_id if available
      if (_auth.currentUser?.uid != null) {
        requestBody['user_id'] = _auth.currentUser!.uid;
      }
      
      print('DEBUG: Sending upcycle ideas request: $requestBody');
      
      final response = await http.post(
        Uri.parse('$baseUrl/upcycle-ideas'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode(requestBody),
      );

      // Close loading dialog
      Navigator.of(context).pop();

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        
        if (data['success'] == true) {
          // Add the upcycling ideas as a new message in the chat
          final upcycleMessage = ChatMessage(
            message: data['content'] ?? 'No upcycling ideas generated.',
            isUser: false,
            responseSource: 'upcycle_ideas',
          );

          setState(() {
            messages.add(upcycleMessage);
            if (currentSession != null) {
              currentSession!.addMessage(upcycleMessage);
            }
          });
          
          // Save sessions after adding message
          _saveSessions();
          
          // Scroll to bottom to show the new message
          _scrollToBottom();
        } else {
          // Show error message
          _addErrorMessage(data['content'] ?? 'Failed to generate upcycling ideas.');
        }
      } else {
        _addErrorMessage('Failed to generate upcycling ideas. Please try again.');
      }
    } catch (e) {
      // Close loading dialog if it's still open
      if (Navigator.of(context).canPop()) {
        Navigator.of(context).pop();
      }
      _addErrorMessage('Error generating upcycling ideas: $e');
    }
  }

  Future<void> _searchLocalRepairShops() async {
    try {
      // First, get user's location
      final locationService = LocationService();
      
      // Show initial loading dialog
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (BuildContext context) {
          return const AlertDialog(
            content: Row(
              children: [
                CircularProgressIndicator(),
                SizedBox(width: 20),
                Text('Getting your location...'),
              ],
            ),
          );
        },
      );

      // Get location with error handling
      final locationResult = await locationService.getLocationWithErrorHandling();
      
      // Close initial loading dialog
      Navigator.of(context).pop();

      if (!locationResult.success) {
        // Show error dialog with option to retry, open settings, or enter location manually
        _showLocationErrorDialog(locationResult);
        return;
      }
      
      // Check if the location seems reasonable (not obviously cached/default)
      if (locationResult.latitude != null && locationResult.longitude != null) {
        // Check if coordinates look like they might be cached (common default locations)
        bool isLikelyCached = _isLikelyCachedLocation(locationResult.latitude!, locationResult.longitude!);
        if (isLikelyCached) {
          print('DEBUG: Location appears to be cached, offering manual input option');
          _showLocationAccuracyDialog(locationResult);
          return;
        }
      }

      // Show searching dialog
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (BuildContext context) {
          return const AlertDialog(
            content: Row(
              children: [
                CircularProgressIndicator(),
                SizedBox(width: 20),
                Text('Searching for local repair shops...'),
              ],
            ),
          );
        },
      );

      // Call the LocalRepairTool API endpoint with location data
      final requestBody = <String, dynamic>{
        'latitude': locationResult.latitude,
        'longitude': locationResult.longitude,
      };
      
      // Add user_id if available
      if (_auth.currentUser?.uid != null) {
        requestBody['user_id'] = _auth.currentUser!.uid;
      }
      
      print('DEBUG: Sending location data: $requestBody');
      
      final response = await http.post(
        Uri.parse('$baseUrl/local-repair'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode(requestBody),
      );

      // Close loading dialog
      Navigator.of(context).pop();

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        
        if (data['success'] == true) {
          // Show the repair shops in a dialog
          _showLocalRepairDialog(data['content'], data['local_repair_links']);
        } else {
          // Show error message
          _showLocalRepairDialog(data['content'], []);
        }
      } else {
        _showLocalRepairDialog('Failed to search for repair shops. Please try again.', []);
      }
    } catch (e) {
      // Close loading dialog if it's still open
      if (Navigator.of(context).canPop()) {
        Navigator.of(context).pop();
      }
      _showLocalRepairDialog('Error searching for repair shops: $e', []);
    }
  }

  bool _isLikelyCachedLocation(double lat, double lng) {
    // Check for common cached/default locations
    // San Francisco area (37.7749, -122.4194)
    if ((lat >= 37.4 && lat <= 38.0) && (lng >= -122.5 && lng <= -122.0)) {
      return true;
    }
    // Mountain View/Google area (37.4219983, -122.084)
    if ((lat >= 37.3 && lat <= 37.5) && (lng >= -122.2 && lng <= -122.0)) {
      return true;
    }
    // New York area (40.7128, -74.0060)
    if ((lat >= 40.5 && lat <= 41.0) && (lng >= -74.2 && lng <= -73.8)) {
      return true;
    }
    // Default 0, 0 coordinates
    if (lat == 0.0 && lng == 0.0) {
      return true;
    }
    return false;
  }

  void _showLocationAccuracyDialog(LocationResult locationResult) {
    showDialog(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: const Row(
            children: [
              Icon(Icons.location_searching, color: Colors.orange),
              SizedBox(width: 8),
              Text('Location Accuracy'),
            ],
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'The location detected (${locationResult.latitude!.toStringAsFixed(4)}, ${locationResult.longitude!.toStringAsFixed(4)}) appears to be cached or inaccurate.',
                style: const TextStyle(fontSize: 14),
              ),
              const SizedBox(height: 16),
              const Text(
                'Would you like to:',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              const Text('• Try getting a fresh GPS location'),
              const Text('• Select your location on a map'),
              const Text('• Use the detected location anyway'),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.of(context).pop();
                _searchLocalRepairShops(); // Retry with fresh location
              },
              child: const Text('Try Again'),
            ),
            TextButton(
              onPressed: () async {
                Navigator.of(context).pop();
                final selectedLocation = await LocationPickerDialog.show(context);
                
                if (selectedLocation != null) {
                  final manualLocation = LocationResult(
                    success: true,
                    latitude: selectedLocation.latitude,
                    longitude: selectedLocation.longitude,
                    error: null,
                    canRequestPermission: false,
                  );
                  _proceedWithLocation(manualLocation);
                }
              },
              child: const Text('Select on Map'),
            ),
            TextButton(
              onPressed: () {
                Navigator.of(context).pop();
                _proceedWithLocation(locationResult);
              },
              child: const Text('Use This Location'),
            ),
          ],
        );
      },
    );
  }


  void _proceedWithLocation(LocationResult locationResult) {
    // Continue with the search using the provided location
    _searchWithLocation(locationResult);
  }

  Future<void> _searchWithLocation(LocationResult locationResult) async {
    try {
      // Show searching dialog
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (BuildContext context) {
          return const AlertDialog(
            content: Row(
              children: [
                CircularProgressIndicator(),
                SizedBox(width: 20),
                Text('Searching for local repair shops...'),
              ],
            ),
          );
        },
      );

      // Call the LocalRepairTool API endpoint with location data
      final requestBody = <String, dynamic>{
        'latitude': locationResult.latitude,
        'longitude': locationResult.longitude,
      };
      
      // Add user_id if available
      if (_auth.currentUser?.uid != null) {
        requestBody['user_id'] = _auth.currentUser!.uid;
      }
      
      print('DEBUG: Sending location data: $requestBody');
      
      final response = await http.post(
        Uri.parse('$baseUrl/local-repair'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode(requestBody),
      );

      // Close loading dialog
      Navigator.of(context).pop();

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        
        if (data['success'] == true) {
          // Show the repair shops in a dialog
          _showLocalRepairDialog(data['content'], data['local_repair_links']);
        } else {
          // Show error message
          _showLocalRepairDialog(data['content'], []);
        }
      } else {
        _showLocalRepairDialog('Failed to search for repair shops. Please try again.', []);
      }
    } catch (e) {
      // Close loading dialog if it's still open
      if (Navigator.of(context).canPop()) {
        Navigator.of(context).pop();
      }
      _showLocalRepairDialog('Error searching for repair shops: $e', []);
    }
  }

  void _showLocationErrorDialog(LocationResult locationResult) {
    showDialog(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: const Row(
            children: [
              Icon(Icons.location_off, color: Colors.orange),
              SizedBox(width: 8),
              Text('Location Required'),
            ],
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                locationResult.error ?? 'Location access is required to find nearby repair shops.',
                style: const TextStyle(fontSize: 14),
              ),
              const SizedBox(height: 16),
              const Text(
                'To find repair shops near you, please:',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              const Text('• Enable location services on your device'),
              const Text('• Grant location permission to this app'),
              const Text('• Try again'),
            ],
          ),
          actions: [
            if (locationResult.canRequestPermission)
              TextButton(
                onPressed: () {
                  Navigator.of(context).pop();
                  _searchLocalRepairShops(); // Retry
                },
                child: const Text('Try Again'),
              ),
            TextButton(
              onPressed: () async {
                Navigator.of(context).pop();
                await openAppSettings();
              },
              child: const Text('Open Settings'),
            ),
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Cancel'),
            ),
          ],
        );
      },
    );
  }

  void _showLocalRepairDialog(String content, List<dynamic> repairLinks) {
    // Parse the content to extract shop information and links
    List<Map<String, String>> shops = _parseRepairShopsContent(content);
    
    showDialog(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: const Text('Local Repair Stores'),
          content: SizedBox(
            width: double.maxFinite,
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (shops.isEmpty)
                    const Text('No repair shops found in your area.')
                  else
                    ...shops.map((shop) => _buildRepairShopCard(shop)).toList(),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Close'),
            ),
          ],
        );
      },
    );
  }

  List<Map<String, String>> _parseRepairShopsContent(String content) {
    List<Map<String, String>> shops = [];
    List<String> lines = content.split('\n');
    
    String currentShopInfo = '';
    String currentShopLink = '';
    bool isCollectingShopInfo = false;
    
    for (String line in lines) {
      line = line.trim();
      if (line.isEmpty) {
        // Empty line indicates end of current shop
        if (currentShopInfo.isNotEmpty) {
          shops.add({
            'info': currentShopInfo,
            'link': currentShopLink,
          });
          currentShopInfo = '';
          currentShopLink = '';
          isCollectingShopInfo = false;
        }
      } else if (line.startsWith('SHOP:')) {
        // Start of shop information
        currentShopInfo = line.substring(5).trim(); // Remove the "SHOP:" prefix
        isCollectingShopInfo = true;
      } else if (line.startsWith('LINK:')) {
        // Google Maps link line
        currentShopLink = line.substring(5).trim(); // Remove the "LINK:" prefix
        isCollectingShopInfo = false;
      } else if (isCollectingShopInfo && line.isNotEmpty) {
        // Continue collecting shop information (address, phone, etc.)
        currentShopInfo += '\n$line';
      }
    }
    
    // Add the last shop if there's no trailing empty line
    if (currentShopInfo.isNotEmpty) {
      shops.add({
        'info': currentShopInfo,
        'link': currentShopLink,
      });
    }
    
    return shops;
  }

  Widget _buildRepairShopCard(Map<String, String> shop) {
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 8),
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Shop information (selectable)
            SelectableText(
              shop['info'] ?? '',
              style: const TextStyle(fontSize: 14),
            ),
            
            // Google Maps button
            if (shop['link']?.isNotEmpty == true) ...[
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: () => _openGoogleMaps(shop['link']!),
                  icon: const Icon(Icons.location_on, size: 16),
                  label: const Text('Open in Google Maps'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.blue,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Future<void> _openGoogleMaps(String url) async {
    try {
      final Uri uri = Uri.parse(url);
      print('DEBUG: Attempting to open URL: $url');
      
      // Try to launch the URL
      bool launched = false;
      
      // First try with platformDefault mode (recommended for cross-platform)
      if (await canLaunchUrl(uri)) {
        try {
          await launchUrl(uri, mode: LaunchMode.platformDefault);
          launched = true;
          print('DEBUG: Successfully launched with platformDefault mode');
        } catch (e) {
          print('DEBUG: platformDefault failed: $e');
        }
      }
      
      // If platformDefault failed, try externalApplication
      if (!launched && await canLaunchUrl(uri)) {
        try {
          await launchUrl(uri, mode: LaunchMode.externalApplication);
          launched = true;
          print('DEBUG: Successfully launched with externalApplication mode');
        } catch (e) {
          print('DEBUG: externalApplication failed: $e');
        }
      }
      
      // If both failed, try externalNonBrowserApplication
      if (!launched && await canLaunchUrl(uri)) {
        try {
          await launchUrl(uri, mode: LaunchMode.externalNonBrowserApplication);
          launched = true;
          print('DEBUG: Successfully launched with externalNonBrowserApplication mode');
        } catch (e) {
          print('DEBUG: externalNonBrowserApplication failed: $e');
        }
      }
      
      if (!launched) {
        // Fallback: copy to clipboard
        await Clipboard.setData(ClipboardData(text: url));
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Could not open Google Maps. Link copied to clipboard.'),
              duration: Duration(seconds: 3),
            ),
          );
        }
        print('DEBUG: All launch modes failed, copied to clipboard');
      }
      
    } catch (e) {
      print('DEBUG: Error in _openGoogleMaps: $e');
      // Fallback: copy to clipboard
      await Clipboard.setData(ClipboardData(text: url));
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Error opening Google Maps. Link copied to clipboard.'),
            duration: Duration(seconds: 3),
          ),
        );
      }
    }
  }

  Widget _buildMessageBubble(ChatMessage message) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: message.isUser
            ? MainAxisAlignment.end
            : MainAxisAlignment.start,
        children: [
          if (!message.isUser) ...[
            Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: AppColors.primary,
                borderRadius: BorderRadius.circular(16),
              ),
              child: const Icon(
                Icons.smart_toy,
                color: Colors.white,
                size: 20,
              ),
            ),
            const SizedBox(width: 8),
          ],
          
          Flexible(
            child: Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: message.isUser ? AppColors.primary : Colors.white,
                borderRadius: BorderRadius.circular(16),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.1),
                    blurRadius: 4,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Show image preview if available
                  if (message.imageFile != null) ...[
                    Container(
                      margin: const EdgeInsets.only(bottom: 8),
                      child: Stack(
                        children: [
                          GestureDetector(
                            onTap: () => _showImageDialog(message.imageFile!),
                            child: ClipRRect(
                              borderRadius: BorderRadius.circular(8),
                              child: Image.file(
                                message.imageFile!,
                                width: 120,
                                height: 120,
                                fit: BoxFit.cover,
                              ),
                            ),
                          ),
                          // Small indicator showing image is being processed
                          if (message.isUser) ...[
                            Positioned(
                              top: 4,
                              right: 4,
                              child: Container(
                                padding: const EdgeInsets.all(4),
                                decoration: BoxDecoration(
                                  color: Colors.blue.withOpacity(0.8),
                                  borderRadius: BorderRadius.circular(12),
                                ),
                                child: const Icon(
                                  Icons.image,
                                  color: Colors.white,
                                  size: 12,
                                ),
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ],
                  // Message text (selectable)
                  SelectableText(
                    message.message,
                    style: TextStyle(
                      color: message.isUser ? Colors.white : Colors.black,
                      fontSize: 14,
                    ),
                  ),
                  
                  // Action buttons (only for AI messages that are not conversation and have local repair available)
                  if (!message.isUser && 
                      message.responseSource != "conversation" &&
                      message.localRepairAvailable == true) ...[
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        // Local Repair Stores button
                        Expanded(child: _buildLocalRepairButton()),
                        const SizedBox(width: 8),
                        // Upcycle Ideas button
                        Expanded(child: _buildUpcycleButton()),
                        const SizedBox(width: 8),
                        // Post to Social button
                        Expanded(child: _buildPostButton(message)),
                      ],
                    ),
                  ],
                ],
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
                borderRadius: BorderRadius.circular(16),
              ),
              child: const Icon(
                Icons.person,
                color: Colors.grey,
                size: 20,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class ChatSession {
  final String id;
  final String title;
  final DateTime timestamp;
  List<ChatMessage> messages;

  ChatSession({
    required this.id,
    required this.title,
    required this.timestamp,
    required this.messages,
  });

  void addMessage(ChatMessage message) {
    messages.add(message);
  }

  void updateMessages(List<ChatMessage> newMessages) {
    messages = List.from(newMessages);
  }
}

class ChatMessage {
  final String message;
  final bool isUser;
  final File? imageFile; // Add image file support
  final String? responseSource; // "conversation" or "problem_identification"
  final bool? localRepairAvailable; // True if local repair search is available
  final String? itemName; // Item name extracted from LLM
  final String? postTitle; // Title generated by LLM for social posts

  ChatMessage({
    required this.message, 
    required this.isUser, 
    this.imageFile,
    this.responseSource,
    this.localRepairAvailable,
    this.itemName,
    this.postTitle,
  });
}