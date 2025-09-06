# 🌐 Ngrok Setup Guide

## Your Configuration
- **Ngrok URL**: `https://fermin-unlegible-unrefreshingly.ngrok-free.app`
- **API Endpoint**: `https://fermin-unlegible-unrefreshingly.ngrok-free.app/api`

## Backend Setup

### 1. Start Your Backend Server
```bash
cd Backend
python fixagent_api.py
```
Your server should start on `http://localhost:8000`

### 2. Start Ngrok Tunnel
In a new terminal:
```bash
ngrok http --url=fermin-unlegible-unrefreshingly.ngrok-free.app 8000
```

### 3. Verify Your Ngrok URL
- Ngrok will show your public URL (should be `https://fermin-unlegible-unrefreshingly.ngrok-free.app`)
- Make sure it's forwarding to `http://localhost:8000`

## Frontend Configuration ✅

I've already updated your Flutter app to use the ngrok URL:

**File**: `fixitai/lib/screens/fix_workflow_screen.dart`
```dart
static const String baseUrl = 'https://fermin-unlegible-unrefreshingly.ngrok-free.app/api';
```

## Testing the Connection

### 1. Test API Endpoint
Visit in browser: `https://fermin-unlegible-unrefreshingly.ngrok-free.app/api/health`

Should return: `{"status": "healthy"}`

### 2. Test from Flutter App
1. Run your Flutter app: `flutter run`
2. Try the "Find Local Repair" feature
3. Check the console for API calls to your ngrok URL

## API Endpoints Available

Your ngrok URL exposes these endpoints:
- `GET /api/health` - Health check
- `POST /api/session` - Create new session
- `POST /api/session/{id}/analyze` - Analyze repair request
- `POST /api/local-repair` - Search for local repair shops
- `POST /api/upload` - Upload images

## Troubleshooting

### Ngrok Issues
- **URL not working?** Make sure ngrok is running and forwarding to port 8000
- **Connection refused?** Check if your backend server is running on localhost:8000
- **SSL errors?** Ngrok provides HTTPS automatically

### Flutter Issues
- **API calls failing?** Check the console for error messages
- **Network errors?** Make sure your device has internet access
- **CORS errors?** The backend already has CORS enabled for all origins

## Benefits of Using Ngrok

✅ **Public Access**: Your API is accessible from anywhere  
✅ **HTTPS**: Automatic SSL encryption  
✅ **No Port Forwarding**: No need to configure router  
✅ **Easy Testing**: Share your API with others  
✅ **Mobile Testing**: Works on physical devices  

## Security Note

Since this is a public URL, be careful not to expose sensitive data. For production, use proper authentication and restrict access.

## Quick Test Commands

```bash
# Test health endpoint
curl https://fermin-unlegible-unrefreshingly.ngrok-free.app/api/health

# Test local repair endpoint
curl -X POST https://fermin-unlegible-unrefreshingly.ngrok-free.app/api/local-repair \
  -H "Content-Type: application/json" \
  -d '{"latitude": 25.066101, "longitude": 55.208664}'
```

Your Flutter app is now configured to use your ngrok URL! 🚀
