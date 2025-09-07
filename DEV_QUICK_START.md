# 🚀 FixitAI Development Quick Start Guide

This guide will get you up and running with the FixitAI development environment in minutes.

## 📋 Prerequisites

Before starting, ensure you have:
- **Python 3.8+** installed
- **Flutter SDK** (latest stable version)
- **Ollama** installed and running
- **Firebase project** set up
- **Google Cloud Console** access for API keys

## 🔑 Configuration Setup

### **Backend Environment Variables**

Create a `.env` file in the `Backend/` directory with the following variables:

### **Required API Keys**
```bash
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434

# Google Maps API (for local repair shop search)
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here

# Google Programmable Search Engine (PSE) APIs
GOOGLE_PSE_API_KEY_REDDIT=AIzaSyDnoSyRVvIBXWfaGzBI-eyboIP9NpSlBeE
GOOGLE_PSE_CX_REDDIT=963dbddd12d434e90
GOOGLE_PSE_API_KEY_MEDIUM=your_medium_pse_api_key_here
GOOGLE_PSE_CX_MEDIUM=your_medium_pse_cx_here

# Tavily AI Search API
TAVILY_API_KEY=your_tavily_api_key_here

# Firebase Configuration (for Flutter app)
FIREBASE_PROJECT_ID=your_firebase_project_id
FIREBASE_API_KEY=your_firebase_api_key
FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
FIREBASE_STORAGE_BUCKET=your_project.appspot.com
```

### **Optional API Keys**
```bash
# iFixit API (for advanced repair guides)
IFIXIT_API_KEY=your_ifixit_api_key_here

# Additional Google PSE configurations
GOOGLE_PSE_API_KEY_WIKIHOW=your_wikihow_pse_api_key_here
GOOGLE_PSE_CX_WIKIHOW=your_wikihow_pse_cx_here
```

### **Flutter App Configuration**

The Flutter app has API keys and configuration directly in the source files:

#### **Current Configuration (Already Set Up)**
- **Cloudinary**: Configured in `lib/services/cloudinary_service.dart`
- **Backend API**: Configured in `lib/screens/fix_workflow_screen.dart`
- **Google Maps**: Configured in `android/app/src/main/AndroidManifest.xml`
- **Firebase**: Configured in `android/app/google-services.json`

#### **Configuration Templates Available:**
- `android/app/src/main/AndroidManifest_template.xml` - Android manifest template
- `android/app/google-services_template.json` - Firebase configuration template

**To set up your own configuration:**

1. **Update API Keys in Source Files:**
   - Edit `lib/services/cloudinary_service.dart` for Cloudinary settings
   - Edit `lib/screens/fix_workflow_screen.dart` for backend API URLs
   - Edit `android/app/src/main/AndroidManifest.xml` for Google Maps API key

2. **Android Configuration (Required for build):**
   ```bash
   # Copy Android templates if needed
   cp android/app/src/main/AndroidManifest_template.xml android/app/src/main/AndroidManifest.xml
   cp android/app/google-services_template.json android/app/google-services.json
   
   # Edit these files with your actual values:
   # - AndroidManifest.xml: Update Google Maps API key
   # - google-services.json: Update Firebase project details
   ```

3. **Firebase Setup:**
   - Go to [Firebase Console](https://console.firebase.google.com)
   - Create/select your project
   - Add Android app with package name `com.example.fixitai`
   - Download `google-services.json` and replace the template
   - Enable Authentication, Firestore, and Storage

4. **Google Maps Setup:**
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Enable Maps SDK for Android
   - Create API key and update in `AndroidManifest.xml`

## 🛠️ Backend Setup

### 1. **Navigate to Backend Directory**
```bash
cd ~/FixitAI/Backend
```

### 2. **Create Virtual Environment**
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

### 4. **Install Ollama Models**
```bash
# Install required LLM models
ollama pull qwen2.5vl:7b
# ollama pull llama3.1:8b  # Removed - not used in codebase

# Start Ollama server (if not already running)
ollama serve
```

### 5. **Run Backend Server**
```bash
python fixagent_api.py
```

The backend will start on `http://localhost:8000`

## 📱 Flutter App Setup

### 1. **Navigate to Flutter Directory**
```bash
cd ~/FixitAI/fixitai
```

### 2. **Install Flutter Dependencies**
```bash
flutter pub get
```

### 3. **Configure Firebase**
- Add your `google-services.json` (Android) to `android/app/`
- Add your `GoogleService-Info.plist` (iOS) to `ios/Runner/`
- Update Firebase configuration in `lib/main.dart` if needed

### 4. **Configure Flutter App (Optional)**
The app is already configured with working API keys. If you want to use your own:

```bash
# Update API keys in source files:
# 1. Edit lib/services/cloudinary_service.dart for Cloudinary settings
# 2. Edit lib/screens/fix_workflow_screen.dart for backend API URLs
# 3. Edit android/app/src/main/AndroidManifest.xml for Google Maps API key
```

### 5. **Configure Android (Required for Build)**
```bash
# Copy Android configuration templates if needed
cp android/app/src/main/AndroidManifest_template.xml android/app/src/main/AndroidManifest.xml
cp android/app/google-services_template.json android/app/google-services.json

# IMPORTANT: Update these files with your actual values:
# 1. AndroidManifest.xml - Update Google Maps API key
# 2. google-services.json - Update Firebase project details
# 
# These files contain the current working values and should be updated
# with your own Firebase project and Google Maps API key
```

### 6. **Run Flutter App**
```bash
flutter run
```

## 🌐 Ngrok Setup (for External Access)

### 1. **Install Ngrok**
- Download from [ngrok.com](https://ngrok.com)
- Create account and get your auth token

### 2. **Configure Ngrok**
```bash
ngrok config add-authtoken your_auth_token_here
```

### 3. **Start Ngrok Tunnel**
```bash
# In a separate terminal, expose your backend
ngrok http 8000
```

### 4. **Update Flutter API Endpoint**
Copy the ngrok HTTPS URL (e.g., `https://abc123.ngrok.io`) and update it in:
- `lib/services/api_service.dart`
- Replace `http://localhost:8000` with your ngrok URL

## 🧪 Testing the Setup

### 1. **Test Backend**
```bash
# Test health endpoint
curl http://localhost:8000/api/health

# Test with ngrok URL
curl https://your-ngrok-url.ngrok.io/api/health
```

### 2. **Test Flutter App**
- Launch the app on your device/emulator
- Try logging in with Firebase Auth
- Test the repair workflow by uploading an image

### 3. **Test API Integration**
- Send a test message through the Flutter app
- Check backend logs for incoming requests
- Verify multi-agent processing is working

## 🔧 Development Workflow

### **Backend Development**
1. Make changes to Python files in `Backend/`
2. Restart the FastAPI server: `python fixagent_api.py`
3. Test changes via API endpoints or Flutter app

### **Flutter Development**
1. Make changes to Dart files in `fixitai/lib/`
2. Hot reload: Press `r` in terminal or save files
3. Hot restart: Press `R` in terminal for major changes

### **Full Stack Testing**
1. Ensure backend is running on `localhost:8000`
2. Ensure Flutter app is connected to correct API endpoint
3. Test complete user workflows end-to-end

## 🚨 Troubleshooting

### **Common Issues**

#### **Backend Won't Start**
- Check if Ollama is running: `ollama list`
- Verify all environment variables are set
- Check Python dependencies: `pip list`

#### **Flutter Can't Connect to Backend**
- Verify backend is running on correct port
- Check API endpoint URL in `api_service.dart`
- Test backend directly with curl

#### **Ollama Models Not Found**
```bash
# Reinstall models
ollama pull qwen2.5vl:7b
# ollama pull llama3.1:8b  # Removed - not used in codebase

# Check model status
ollama list
```

#### **Firebase Authentication Issues**
- Verify Firebase project configuration
- Check `google-services.json` and `GoogleService-Info.plist` files
- Ensure Firebase Auth is enabled in Firebase Console

### **API Key Issues**
- Verify all required API keys are in `.env` file
- Check API key permissions and quotas
- Test API keys individually with curl commands

## 📚 Next Steps

Once everything is running:
1. **Explore the codebase** using the documentation in each directory
2. **Test all features** - image upload, repair analysis, local search, social features
3. **Check logs** for any errors or warnings
4. **Start developing** new features or improvements

## 🆘 Getting Help

- Check the individual README files in each directory
- Review the API documentation in `Backend/README.md`
- Test individual components using the test files in `Backend/modules/modules_test/`
- Check Flutter app structure in `fixitai/README.md`

---

**Happy Coding! 🎉**

The FixitAI development environment is now ready for development.
