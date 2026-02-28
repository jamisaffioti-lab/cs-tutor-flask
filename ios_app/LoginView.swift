//
//  LoginView.swift
//  Ascent Scholars
//
//  Login screen with Google Sign-In
//

import SwiftUI
import AuthenticationServices

struct LoginView: View {
    @StateObject private var authManager = AuthManager.shared
    @State private var showError = false
    @State private var errorMessage = ""
    
    var body: some View {
        ZStack {
            // Mountain background
            Image("noros_life")
                .resizable()
                .aspectRatio(contentMode: .fill)
                .edgesIgnoringSafeArea(.all)
                .overlay(Color.black.opacity(0.3))
            
            VStack(spacing: 30) {
                Spacer()
                
                // Logo and title
                VStack(spacing: 15) {
                    Image("noros-logo-white")
                        .resizable()
                        .frame(width: 80, height: 80)
                    
                    Text("ascent scholars")
                        .font(.custom("Orbitron-Bold", size: 32))
                        .foregroundColor(.white)
                    
                    Text("your personal AI tutor for computer science")
                        .font(.system(size: 16, design: .monospaced))
                        .foregroundColor(.white.opacity(0.8))
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 40)
                }
                
                // Features
                VStack(alignment: .leading, spacing: 12) {
                    FeatureRow(text: "expert tutoring in AP CS, Python, Arduino & more")
                    FeatureRow(text: "Socratic method to help you learn")
                    FeatureRow(text: "save conversations and track progress")
                    FeatureRow(text: "practice with real AP exam questions")
                }
                .padding(.horizontal, 40)
                
                Spacer()
                
                // Sign in button
                Button(action: {
                    // For demo - in production you'd use Google Sign-In SDK
                    demoLogin()
                }) {
                    HStack(spacing: 12) {
                        Image(systemName: "person.circle.fill")
                            .font(.system(size: 20))
                        
                        Text("sign in with Google")
                            .font(.system(size: 16, weight: .bold, design: .monospaced))
                    }
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 16)
                    .background(
                        RoundedRectangle(cornerRadius: 50)
                            .fill(Color("AccentBlue").opacity(0.25))
                            .overlay(
                                RoundedRectangle(cornerRadius: 50)
                                    .stroke(Color("AccentBlue").opacity(0.4), lineWidth: 1)
                            )
                    )
                }
                .padding(.horizontal, 40)
                
                Text("we respect your privacy")
                    .font(.system(size: 12, design: .monospaced))
                    .foregroundColor(.white.opacity(0.5))
                    .padding(.bottom, 40)
            }
        }
        .alert("Error", isPresented: $showError) {
            Button("OK", role: .cancel) { }
        } message: {
            Text(errorMessage)
        }
    }
    
    private func demoLogin() {
        // Demo login for testing
        // In production, implement Google Sign-In
        authManager.login(
            googleId: "demo_\(UUID().uuidString)",
            email: "demo@student.edu",
            name: "Demo Student",
            picture: nil
        )
    }
}

struct FeatureRow: View {
    let text: String
    
    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Text("✓")
                .font(.system(size: 18, weight: .bold))
                .foregroundColor(Color("AccentBlue"))
            
            Text(text)
                .font(.system(size: 14, design: .monospaced))
                .foregroundColor(.white.opacity(0.9))
        }
    }
}

#Preview {
    LoginView()
}
