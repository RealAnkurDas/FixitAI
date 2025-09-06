# 🗺️ Google Maps Setup Instructions

## The Problem
Your map shows a black/light blue screen with "Google" at the bottom because you need a valid Google Maps API key.

## Quick Fix (5 minutes)

### Step 1: Get Google Maps API Key
1. Go to: https://console.cloud.google.com/
2. Click "Create Project" or select existing project
3. Go to "APIs & Services" → "Library"
4. Search for "Maps SDK for Android" and enable it
5. Go to "APIs & Services" → "Credentials"
6. Click "Create Credentials" → "API Key"
7. Copy the API key (starts with "AIza...")

### Step 2: Update Your App
1. Open `fixitai/android/app/src/main/AndroidManifest.xml`
2. Find this line:
   ```xml
   <meta-data android:name="com.google.android.geo.API_KEY"
              android:value="YOUR_ACTUAL_API_KEY_HERE"/>
   ```
3. Replace `YOUR_ACTUAL_API_KEY_HERE` with your real API key:
   ```xml
   <meta-data android:name="com.google.android.geo.API_KEY"
              android:value="AIzaSyBxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"/>
   ```

### Step 3: Update Search Function
1. Open `fixitai/lib/screens/location_picker_screen.dart`
2. Find line 116:
   ```dart
   final apiKey = "YOUR_GOOGLE_MAPS_API_KEY";
   ```
3. Replace with your real API key:
   ```dart
   final apiKey = "AIzaSyBxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx";
   ```

### Step 4: Rebuild App
```bash
flutter clean
flutter pub get
flutter run
```

## What You'll See After Setup
- ✅ Map shows countries, states, cities, roads
- ✅ Search works (type "Dubai" and click Search)
- ✅ Tap to select location works
- ✅ Current location button works

## Security Note
For production, restrict your API key to your app's package name in Google Cloud Console.

## Troubleshooting
- **Still black screen?** Check API key is correct
- **Search not working?** Make sure Geocoding API is enabled
- **Build errors?** Check API key format in XML

## Test It
1. Open location picker
2. Type "Dubai" in search box
3. Click "Search" button
4. Map should zoom to Dubai
5. Tap anywhere to select location
6. Click "Select Location"

The map will now show the full geographic atlas with countries, states, and cities!
