# FixitAI Flutter Application

A comprehensive mobile application for repair assistance, combining AI-powered analysis with community-driven repair guidance.

## Architecture Overview

### **Core Components**

#### **Authentication & User Management**
- **Firebase Authentication**: User registration, login, and profile management
- **User Profiles**: Custom user data with profile pictures and repair history
- **Session Management**: Persistent authentication state

#### **Main Screens**
- **`auth_screen.dart`**: Login/registration interface
- **`home_screen.dart`**: Main dashboard with repair options
- **`fix_workflow_screen.dart`**: Multi-agent conversation interface
- **`profile_screen.dart`**: User profile, posts, and settings
- **`socials_screen.dart`**: Community posts and social features

#### **Services**
- **`api_service.dart`**: Backend API communication
- **`auth_service.dart`**: Firebase authentication management
- **`storage_service.dart`**: Local data persistence
- **`social_service.dart`**: Social features and post management

#### **Models**
- **`user_model.dart`**: User data structure
- **`post_model.dart`**: Social post data structure
- **`repair_model.dart`**: Repair session data structure

#### **Widgets**
- **`post_card.dart`**: Reusable social post display component
- **`chat_bubble.dart`**: Conversation message display
- **`image_picker_widget.dart`**: Camera and gallery integration

## Key Features

### **Repair Assistance Workflow**
1. **Image Capture**: Camera integration for problem documentation
2. **Multi-Agent Analysis**: AI-powered repair guidance via backend
3. **Local Repair Discovery**: Google Maps integration for nearby services
4. **Upcycling Suggestions**: Creative reuse ideas for broken items

### **Social Features**
- **Community Posts**: Share repair experiences and solutions
- **User Profiles**: View other users' repair history and expertise
- **Post Interactions**: Like, save, and comment on community content

### **User Experience**
- **Material Design**: Modern, intuitive interface
- **Custom Color Scheme**: Branded visual identity
- **Responsive Layout**: Optimized for various screen sizes
- **Offline Support**: Local data caching and persistence

## Data Flow

1. **User Input** → Flutter UI components
2. **API Calls** → Backend services via `api_service.dart`
3. **Backend Processing** → Multi-agent analysis and external data sources
4. **Response Handling** → UI updates and data persistence
5. **Social Features** → Firebase Firestore for community data

## Getting Started

### Prerequisites
- Flutter SDK (latest stable version)
- Firebase project with Authentication and Firestore enabled
- Backend API running (see Backend/README.md)

### Setup
1. Install Flutter dependencies:
   ```bash
   flutter pub get
   ```

2. Configure Firebase:
   - Add your `google-services.json` (Android) and `GoogleService-Info.plist` (iOS)
   - Update Firebase configuration in `main.dart`

3. Update API endpoints in `services/api_service.dart` to point to your backend

4. Run the application:
   ```bash
   flutter run
   ```

## Project Structure

```
lib/
├── main.dart                 # App entry point
├── models/                   # Data models
├── screens/                  # Main application screens
├── services/                 # Backend communication and utilities
├── utils/                    # Helper functions and constants
└── widgets/                  # Reusable UI components
```

## Dependencies

Key Flutter packages used:
- `firebase_core` & `firebase_auth`: Authentication
- `cloud_firestore`: Database
- `firebase_storage`: File storage
- `image_picker`: Camera integration
- `google_maps_flutter`: Maps integration
- `http`: API communication
- `shared_preferences`: Local storage
