//
//  SETUP_INSTRUCTIONS.md
//  Ascent Scholars iOS App
//
//  Complete setup guide for the iOS app
//

# Ascent Scholars iOS App - Setup Guide

## 📱 Project Structure

```
AscentScholars/
├── AscentScholarsApp.swift          (Main app entry)
├── ContentView.swift                (Subject selection)
├── Views/
│   ├── LoginView.swift              (Login screen)
│   ├── ChatView.swift               (Chat interface)
│   └── Components/                  (Reusable UI components)
├── ViewModels/
│   └── ChatViewModel.swift          (Chat logic)
├── Services/
│   ├── APIService.swift             (Backend API)
│   └── AuthManager.swift            (Authentication)
├── Models/
│   └── (Message, Subject models already in files)
└── Assets.xcassets/
    ├── Colors/                      (Color definitions below)
    └── Images/                      (Logo and icons)
```

## 🎨 Color Definitions (Add to Assets.xcassets)

Create these color sets in Xcode:

### AccentBlue
- Light/Dark: #8CC9F0

### CardBackground
- Light/Dark: rgba(140, 201, 240, 0.2)
- Use: Subject cards

### HeaderBackground
- Light/Dark: rgba(44, 62, 80, 0.9)
- Use: Chat header, navigation

### InputBackground
- Light/Dark: rgba(22, 33, 62, 0.6)
- Use: Text input field

### InputContainerBackground
- Light/Dark: rgba(44, 62, 80, 0.9)
- Use: Input area container

### UserBubble
- Light/Dark: rgba(140, 201, 240, 0.3)
- Use: User message bubbles

### AssistantBubble
- Light/Dark: rgba(36, 41, 67, 0.8)
- Use: Assistant message bubbles

## 🖼️ Required Images

Add these to Assets.xcassets:

### Logos
- noros-logo-white (80x80pt @1x, @2x, @3x)
- noros_life (background image - the mountain scene)

### Subject Icons (60x60pt each)
- cupojoe (AP CS A - coffee cup)
- pysnake (AP CS Principles - Python logo)
- arduino (Arduino - infinity symbol)
- brain (AI - brain icon)
- algodata (Algorithms - data structure icon)
- compsci (General CS - computer icon)

## 📦 Required Dependencies

### 1. Add to Package Dependencies (in Xcode):

File → Add Package Dependencies...

None required for basic version! The app uses native SwiftUI and URLSession.

### Optional (for production):
- Google Sign-In SDK: https://github.com/google/GoogleSignIn-iOS
- Keychain Swift: https://github.com/evgenyneu/keychain-swift

## ⚙️ Configuration Steps

### 1. Create New Xcode Project
- File → New → Project
- iOS → App
- Product Name: "Ascent Scholars"
- Interface: SwiftUI
- Language: Swift

### 2. Add Custom Font (Orbitron)

Download Orbitron font from Google Fonts:
https://fonts.google.com/specimen/Orbitron

Add to project:
1. Drag Orbitron-Bold.ttf into Xcode
2. Add to Info.plist:
```xml
<key>UIAppFonts</key>
<array>
    <string>Orbitron-Bold.ttf</string>
</array>
```

### 3. Configure App Transport Security

For local testing, add to Info.plist:
```xml
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsArbitraryLoads</key>
    <true/>
</dict>
```

**Remove this for production!** Use HTTPS only.

### 4. Update Backend URL

In `APIService.swift`, change:
```swift
private let baseURL = "https://tutor.noros.life/api"
```

For local testing:
```swift
private let baseURL = "http://YOUR_COMPUTER_IP:5000/api"
```

### 5. App Icon

Create an app icon (1024x1024) with your Noros logo.
Add to Assets.xcassets → AppIcon

## 🔧 Backend Configuration

Your Flask app needs to handle iOS requests. Add CORS support:

### Install Flask-CORS:
```bash
pip install flask-cors
```

### Update app.py:
```python
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Add this line
```

## 📲 Running the App

### On Simulator:
1. Open in Xcode
2. Select iPhone simulator (iPhone 15 Pro recommended)
3. Press ⌘R to run

### On Physical Device:
1. Connect iPhone via USB
2. Select your device in Xcode
3. Click "Trust Computer" on iPhone
4. Update Signing & Capabilities:
   - Select your Apple ID team
   - Bundle ID: com.yourname.ascentscholars
5. Press ⌘R to run

## 🧪 Testing Without Mac

Upload to TestFlight:
1. Build in Xcode
2. Archive: Product → Archive
3. Distribute → TestFlight
4. Test on any iOS device via TestFlight app

## 🚀 Future Enhancements

### Authentication
- Implement real Google Sign-In
- Add Apple Sign-In (required for App Store)
- Secure token storage with Keychain

### Features to Add
- File upload support
- Code syntax highlighting
- Offline message queue
- Push notifications for responses
- Dark/Light mode toggle
- Accessibility improvements

### App Store Requirements
- Privacy Policy URL
- App Store screenshots (6.5" and 5.5")
- App description and keywords
- Rating: 4+ (educational)

## 📝 App Store Submission Checklist

- [ ] Real authentication (not demo)
- [ ] Privacy policy
- [ ] App icon (all sizes)
- [ ] Screenshots
- [ ] Remove any test/demo code
- [ ] HTTPS only (no HTTP)
- [ ] Handle all error states
- [ ] Accessibility labels
- [ ] Support latest iOS version

## 🔐 Security Notes

**Before App Store:**
1. Remove demo login
2. Implement proper Google OAuth
3. Store tokens securely (Keychain)
4. Add certificate pinning
5. Validate all inputs
6. Rate limit requests

## 📊 File Sizes

Expected sizes:
- App binary: ~15-20 MB
- With images: ~25-30 MB
- First download: ~30 MB

## ⚡ Performance

Optimizations included:
- LazyVStack for messages (efficient scrolling)
- Image caching
- Debounced API calls
- Minimal redraws

## 🐛 Common Issues

**Build fails:**
- Clean build folder: ⌘⇧K
- Delete derived data
- Restart Xcode

**Simulator crashes:**
- Reset simulator: Device → Erase All Content
- Use newer iOS version

**Network errors:**
- Check backend is running
- Verify URL is correct
- Check CORS is enabled
- Use computer's IP (not localhost) for simulator

## 📞 Support

Need help? Check:
1. Console logs in Xcode
2. Network tab in Instruments
3. Backend logs (Flask terminal)

---

**Ready to build!** 🚀

Start with: File → Open → (this project folder)
Then: ⌘R to run
