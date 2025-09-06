# Google Maps Setup for Location Picker

## Overview
The app now includes a map-based location picker that allows users to visually select their location instead of manually entering coordinates.

## Setup Required

### 1. Get Google Maps API Key

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the following APIs:
   - **Maps SDK for Android**
   - **Maps SDK for iOS** (if building for iOS)
   - **Places API** (for location search)
4. Create credentials (API Key)
5. Restrict the API key to your app's package name for security

### 2. Configure API Key

**For Android:**
1. Open `android/app/src/main/AndroidManifest.xml`
2. Replace `YOUR_GOOGLE_MAPS_API_KEY_HERE` with your actual API key:

```xml
<meta-data android:name="com.google.android.geo.API_KEY"
           android:value="YOUR_ACTUAL_API_KEY_HERE"/>
```

**For iOS:**
1. Open `ios/Runner/AppDelegate.swift`
2. Add the following import and configuration:

```swift
import GoogleMaps

// In application:didFinishLaunchingWithOptions:
GMSServices.provideAPIKey("YOUR_ACTUAL_API_KEY_HERE")
```

### 3. Test the Implementation

1. Run the app: `flutter run`
2. Click "Find Local Repair" button
3. If GPS location is cached/inaccurate, you'll see a dialog
4. Choose "Select on Map" to open the location picker
5. Tap anywhere on the map to select your location
6. Click "Done" to confirm and search for repair shops

## Features

### Location Picker Screen
- **Interactive Map**: Tap to select location
- **Current Location Button**: Jump to your GPS location
- **Search Bar**: Search for places (requires Places API)
- **Visual Feedback**: Shows selected coordinates
- **Default Location**: Falls back to Dubai if no location available

### User Experience
1. **GPS Detection**: Automatically detects if location is cached
2. **Map Selection**: Visual location selection instead of manual coordinates
3. **Current Location**: One-tap access to GPS location
4. **Search Integration**: Search for places by name
5. **Coordinate Display**: Shows exact coordinates of selected location

## Security Notes

- **API Key Restrictions**: Always restrict your API key to your app's package name
- **Billing**: Google Maps API has usage limits and billing
- **Rate Limiting**: Consider implementing rate limiting for production use

## Troubleshooting

### Map Not Loading
- Check if API key is correctly configured
- Verify API key has proper permissions
- Check internet connection

### Location Not Accurate
- Ensure location permissions are granted
- Check if location services are enabled
- Try the "Current Location" button in the map

### Search Not Working
- Verify Places API is enabled
- Check API key restrictions
- Ensure billing is set up for the project

## Example Usage

```dart
// Navigate to location picker
final selectedLocation = await Navigator.of(context).push<LatLng>(
  MaterialPageRoute(
    builder: (context) => const LocationPickerScreen(),
  ),
);

if (selectedLocation != null) {
  // Use the selected location
  print('Selected: ${selectedLocation.latitude}, ${selectedLocation.longitude}');
}
```

The location picker provides a much better user experience compared to manual coordinate entry, allowing users to visually select their location on an interactive map.
