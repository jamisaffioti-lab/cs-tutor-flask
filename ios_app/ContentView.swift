//
//  ContentView.swift
//  Ascent Scholars
//
//  Main app entry point with subject selection
//

import SwiftUI

struct ContentView: View {
    @StateObject private var authManager = AuthManager.shared
    @State private var selectedSubject: Subject?
    
    var body: some View {
        Group {
            if authManager.isAuthenticated {
                NavigationView {
                    SubjectSelectionView(selectedSubject: $selectedSubject)
                }
                .accentColor(Color("AccentBlue"))
            } else {
                LoginView()
            }
        }
    }
}

struct SubjectSelectionView: View {
    @Binding var selectedSubject: Subject?
    @StateObject private var authManager = AuthManager.shared
    
    let subjects: [Subject] = [
        Subject(id: "ap_cs_a", name: "AP Computer Science A", icon: "cupojoe", description: "Java programming"),
        Subject(id: "ap_cs_principles", name: "AP CS Principles", icon: "pysnake", description: "Python & computing concepts"),
        Subject(id: "arduino", name: "Arduino Programming", icon: "arduino", description: "Electronics & C++"),
        Subject(id: "artificial_intelligence", name: "Artificial Intelligence", icon: "brain", description: "ML & AI concepts"),
        Subject(id: "algorithms", name: "Algorithms", icon: "algodata", description: "Data structures"),
        Subject(id: "general", name: "General CS", icon: "compsci", description: "All topics")
    ]
    
    var body: some View {
        ZStack {
            // Mountain background
            Image("noros_life")
                .resizable()
                .aspectRatio(contentMode: .fill)
                .edgesIgnoringSafeArea(.all)
                .overlay(Color.black.opacity(0.3))
            
            ScrollView {
                VStack(spacing: 20) {
                    // Header
                    VStack(spacing: 10) {
                        Image("noros-logo-white")
                            .resizable()
                            .frame(width: 60, height: 60)
                        
                        Text("ascent scholars")
                            .font(.custom("Orbitron-Bold", size: 28))
                            .foregroundColor(.white)
                        
                        Text("select your course")
                            .font(.system(size: 16, design: .monospaced))
                            .foregroundColor(.white.opacity(0.8))
                    }
                    .padding(.top, 40)
                    .padding(.bottom, 20)
                    
                    // Subject Cards
                    LazyVGrid(columns: [GridItem(.adaptive(minimum: 150))], spacing: 15) {
                        ForEach(subjects) { subject in
                            NavigationLink(
                                destination: ChatView(subject: subject),
                                tag: subject,
                                selection: $selectedSubject
                            ) {
                                SubjectCard(subject: subject)
                            }
                        }
                    }
                    .padding(.horizontal)
                    
                    Spacer(minLength: 50)
                }
            }
        }
        .navigationTitle("")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .navigationBarTrailing) {
                Menu {
                    Button(action: {
                        // Navigate to dashboard
                    }) {
                        Label("Dashboard", systemImage: "chart.bar")
                    }
                    
                    Button(role: .destructive, action: {
                        authManager.logout()
                    }) {
                        Label("Logout", systemImage: "rectangle.portrait.and.arrow.right")
                    }
                } label: {
                    Image(systemName: "ellipsis.circle")
                        .foregroundColor(.white)
                }
            }
        }
    }
}

struct SubjectCard: View {
    let subject: Subject
    
    var body: some View {
        VStack(spacing: 15) {
            Image(subject.icon)
                .resizable()
                .frame(width: 50, height: 50)
            
            Text(subject.name)
                .font(.custom("Orbitron-Bold", size: 14))
                .foregroundColor(.white)
                .multilineTextAlignment(.center)
                .fixedSize(horizontal: false, vertical: true)
            
            if let description = subject.description {
                Text(description)
                    .font(.system(size: 12, design: .monospaced))
                    .foregroundColor(.white.opacity(0.7))
                    .multilineTextAlignment(.center)
            }
        }
        .frame(maxWidth: .infinity)
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 15)
                .fill(Color("CardBackground"))
                .overlay(
                    RoundedRectangle(cornerRadius: 15)
                        .stroke(Color("AccentBlue").opacity(0.4), lineWidth: 1)
                )
        )
        .shadow(color: .black.opacity(0.2), radius: 5)
    }
}

// MARK: - Models

struct Subject: Identifiable, Hashable {
    let id: String
    let name: String
    let icon: String
    let description: String?
}

#Preview {
    ContentView()
}
