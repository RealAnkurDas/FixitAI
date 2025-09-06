import 'package:geolocator/geolocator.dart';
import 'package:permission_handler/permission_handler.dart';

class LocationService {
  static final LocationService _instance = LocationService._internal();
  factory LocationService() => _instance;
  LocationService._internal();

  /// Check if location services are enabled
  Future<bool> isLocationServiceEnabled() async {
    return await Geolocator.isLocationServiceEnabled();
  }

  /// Check location permission status
  Future<LocationPermission> checkLocationPermission() async {
    return await Geolocator.checkPermission();
  }

  /// Request location permission
  Future<LocationPermission> requestLocationPermission() async {
    return await Geolocator.requestPermission();
  }

  /// Get current position with error handling
  Future<Position?> getCurrentPosition() async {
    try {
      // Check if location services are enabled
      bool serviceEnabled = await isLocationServiceEnabled();
      if (!serviceEnabled) {
        throw Exception('Location services are disabled');
      }

      // Check permissions
      LocationPermission permission = await checkLocationPermission();
      if (permission == LocationPermission.denied) {
        permission = await requestLocationPermission();
        if (permission == LocationPermission.denied) {
          throw Exception('Location permissions are denied');
        }
      }

      if (permission == LocationPermission.deniedForever) {
        throw Exception('Location permissions are permanently denied');
      }

      // Get current position
      Position position = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
        timeLimit: const Duration(seconds: 10),
      );

      return position;
    } catch (e) {
      print('Error getting location: $e');
      return null;
    }
  }

  /// Check if location is cached and get fresh location if needed
  Future<Position?> getFreshLocation() async {
    try {
      // First check if location services are enabled
      bool serviceEnabled = await isLocationServiceEnabled();
      if (!serviceEnabled) {
        return null;
      }

      // Check permissions
      LocationPermission permission = await checkLocationPermission();
      if (permission == LocationPermission.denied) {
        permission = await requestLocationPermission();
        if (permission == LocationPermission.denied || permission == LocationPermission.deniedForever) {
          return null;
        }
      }

      // Get last known position first
      Position? lastPosition = await Geolocator.getLastKnownPosition();
      print('DEBUG: Last known position: ${lastPosition?.latitude}, ${lastPosition?.longitude}');
      
      // Get current position with fresh data
      Position currentPosition = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.best,
        timeLimit: const Duration(seconds: 20),
        forceAndroidLocationManager: false,
      );
      
      print('DEBUG: Current position: ${currentPosition.latitude}, ${currentPosition.longitude}');
      print('DEBUG: Position accuracy: ${currentPosition.accuracy} meters');
      print('DEBUG: Position age: ${DateTime.now().difference(currentPosition.timestamp).inSeconds} seconds ago');
      
      return currentPosition;
    } catch (e) {
      print('Error getting fresh location: $e');
      return null;
    }
  }

  /// Get location with user-friendly error messages
  Future<LocationResult> getLocationWithErrorHandling() async {
    try {
      // Check if location services are enabled
      bool serviceEnabled = await isLocationServiceEnabled();
      if (!serviceEnabled) {
        return LocationResult(
          success: false,
          error: 'Location services are disabled. Please enable location services in your device settings.',
          canRequestPermission: false,
        );
      }

      // Check permissions
      LocationPermission permission = await checkLocationPermission();
      if (permission == LocationPermission.denied) {
        // Request permission
        permission = await requestLocationPermission();
        if (permission == LocationPermission.denied) {
          return LocationResult(
            success: false,
            error: 'Location permission is required to find nearby repair shops. Please grant location permission.',
            canRequestPermission: true,
          );
        }
      }

      if (permission == LocationPermission.deniedForever) {
        return LocationResult(
          success: false,
          error: 'Location permission is permanently denied. Please enable location permission in app settings.',
          canRequestPermission: false,
        );
      }

      // Get fresh location
      Position? position = await getFreshLocation();
      if (position == null) {
        return LocationResult(
          success: false,
          error: 'Failed to get current location',
          canRequestPermission: false,
        );
      }

      print('DEBUG: Got location - lat: ${position.latitude}, lng: ${position.longitude}');
      print('DEBUG: Location accuracy: ${position.accuracy} meters');
      print('DEBUG: Location timestamp: ${position.timestamp}');

      return LocationResult(
        success: true,
        latitude: position.latitude,
        longitude: position.longitude,
        error: null,
        canRequestPermission: false,
      );
    } catch (e) {
      return LocationResult(
        success: false,
        error: 'Failed to get location: ${e.toString()}',
        canRequestPermission: false,
      );
    }
  }

  /// Open app settings for permission management
  Future<void> openAppSettings() async {
    await openAppSettings();
  }
}

class LocationResult {
  final bool success;
  final double? latitude;
  final double? longitude;
  final String? error;
  final bool canRequestPermission;

  LocationResult({
    required this.success,
    this.latitude,
    this.longitude,
    this.error,
    required this.canRequestPermission,
  });
}
