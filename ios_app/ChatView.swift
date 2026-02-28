//
//  ChatView.swift
//  Ascent Scholars
//
//  Chat interface with AI tutor
//

import SwiftUI

struct ChatView: View {
    let subject: Subject
    
    @StateObject private var viewModel: ChatViewModel
    @State private var messageText = ""
    @FocusState private var isInputFocused: Bool
    
    init(subject: Subject) {
        self.subject = subject
        _viewModel = StateObject(wrappedValue: ChatViewModel(subject: subject))
    }
    
    var body: some View {
        ZStack {
            // Mountain background
            Image("noros_life")
                .resizable()
                .aspectRatio(contentMode: .fill)
                .edgesIgnoringSafeArea(.all)
                .overlay(Color.black.opacity(0.3))
            
            VStack(spacing: 0) {
                // Chat header
                VStack(spacing: 5) {
                    HStack {
                        Image(subject.icon)
                            .resizable()
                            .frame(width: 40, height: 40)
                        
                        VStack(alignment: .leading) {
                            Text(subject.name)
                                .font(.custom("Orbitron-Bold", size: 18))
                                .foregroundColor(.white)
                            
                            Text("AI Tutor")
                                .font(.system(size: 13, design: .monospaced))
                                .foregroundColor(.white.opacity(0.6))
                        }
                        
                        Spacer()
                    }
                    .padding()
                }
                .background(Color("HeaderBackground"))
                
                // Messages
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(spacing: 15) {
                            // Welcome message
                            if viewModel.messages.isEmpty {
                                WelcomeMessageView(subject: subject)
                            }
                            
                            // Messages
                            ForEach(viewModel.messages) { message in
                                MessageBubble(message: message)
                                    .id(message.id)
                            }
                            
                            // Loading indicator
                            if viewModel.isLoading {
                                HStack(spacing: 8) {
                                    ForEach(0..<3) { index in
                                        Circle()
                                            .fill(Color("AccentBlue"))
                                            .frame(width: 8, height: 8)
                                            .scaleEffect(viewModel.isLoading ? 1 : 0.5)
                                            .animation(
                                                Animation.easeInOut(duration: 0.6)
                                                    .repeatForever()
                                                    .delay(Double(index) * 0.2),
                                                value: viewModel.isLoading
                                            )
                                    }
                                }
                                .padding()
                                .background(
                                    RoundedRectangle(cornerRadius: 18)
                                        .fill(Color("AssistantBubble"))
                                )
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .padding(.leading)
                            }
                        }
                        .padding()
                    }
                    .onChange(of: viewModel.messages.count) { _ in
                        if let lastMessage = viewModel.messages.last {
                            withAnimation {
                                proxy.scrollTo(lastMessage.id, anchor: .bottom)
                            }
                        }
                    }
                }
                
                // Input area
                VStack(spacing: 10) {
                    // Action buttons
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 10) {
                            if subject.id.contains("ap_cs") {
                                ActionButton(title: "AP Practice", icon: "target") {
                                    viewModel.getPracticeQuestions()
                                }
                            }
                            
                            ActionButton(title: "Summary", icon: "doc.text") {
                                viewModel.getSummary()
                            }
                            
                            ActionButton(title: "Export", icon: "square.and.arrow.up") {
                                viewModel.exportChat()
                            }
                            
                            ActionButton(title: "Clear", icon: "trash") {
                                viewModel.clearChat()
                            }
                        }
                        .padding(.horizontal)
                    }
                    
                    // Message input
                    HStack(spacing: 12) {
                        Button(action: {
                            // Attach file
                        }) {
                            Image(systemName: "paperclip")
                                .foregroundColor(.white.opacity(0.7))
                                .frame(width: 44, height: 44)
                        }
                        
                        TextField("Ask your tutor...", text: $messageText, axis: .vertical)
                            .textFieldStyle(.plain)
                            .padding(.vertical, 12)
                            .padding(.horizontal, 15)
                            .background(Color("InputBackground"))
                            .foregroundColor(.white)
                            .font(.system(size: 15, design: .monospaced))
                            .cornerRadius(12)
                            .focused($isInputFocused)
                            .lineLimit(1...4)
                        
                        Button(action: sendMessage) {
                            Text("Send")
                                .font(.system(size: 15, weight: .bold, design: .monospaced))
                                .foregroundColor(.white)
                                .padding(.horizontal, 20)
                                .padding(.vertical, 12)
                                .background(
                                    RoundedRectangle(cornerRadius: 25)
                                        .fill(Color("AccentBlue").opacity(0.25))
                                        .overlay(
                                            RoundedRectangle(cornerRadius: 25)
                                                .stroke(Color("AccentBlue").opacity(0.4), lineWidth: 1)
                                        )
                                )
                        }
                        .disabled(messageText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || viewModel.isLoading)
                    }
                    .padding(.horizontal)
                    .padding(.bottom, 10)
                }
                .background(Color("InputContainerBackground"))
            }
        }
        .navigationBarTitleDisplayMode(.inline)
        .alert("Error", isPresented: $viewModel.showError) {
            Button("OK", role: .cancel) { }
        } message: {
            Text(viewModel.errorMessage)
        }
    }
    
    private func sendMessage() {
        let text = messageText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }
        
        messageText = ""
        isInputFocused = false
        
        viewModel.sendMessage(text)
    }
}

struct WelcomeMessageView: View {
    let subject: Subject
    
    let examples = [
        "Explain recursion",
        "Debug my code",
        "Practice problems"
    ]
    
    var body: some View {
        VStack(spacing: 20) {
            Image("noros-logo-white")
                .resizable()
                .frame(width: 50, height: 50)
            
            Text("Hi! I'm your \(subject.name) tutor")
                .font(.custom("Orbitron-Bold", size: 20))
                .foregroundColor(Color("AccentBlue"))
            
            Text("I'm here to help you learn through the Socratic method. Ask me anything!")
                .font(.system(size: 15, design: .monospaced))
                .foregroundColor(.white.opacity(0.7))
                .multilineTextAlignment(.center)
            
            VStack(spacing: 10) {
                Text("Try asking:")
                    .font(.system(size: 13, design: .monospaced))
                    .foregroundColor(.white.opacity(0.5))
                
                ForEach(examples, id: \.self) { example in
                    Button(action: {
                        // Set example as message
                    }) {
                        Text(example)
                            .font(.system(size: 13, weight: .bold, design: .monospaced))
                            .foregroundColor(.white)
                            .padding(.horizontal, 16)
                            .padding(.vertical, 10)
                            .background(
                                RoundedRectangle(cornerRadius: 20)
                                    .fill(Color("AccentBlue").opacity(0.15))
                                    .overlay(
                                        RoundedRectangle(cornerRadius: 20)
                                            .stroke(Color("AccentBlue").opacity(0.3), lineWidth: 1)
                                    )
                            )
                    }
                }
            }
        }
        .padding()
    }
}

struct MessageBubble: View {
    let message: Message
    
    var body: some View {
        HStack {
            if message.role == .user {
                Spacer(minLength: 50)
            }
            
            Text(message.content)
                .font(.system(size: 15, design: .monospaced))
                .foregroundColor(.white)
                .padding(.vertical, 12)
                .padding(.horizontal, 16)
                .background(
                    RoundedRectangle(cornerRadius: 18)
                        .fill(message.role == .user ? Color("UserBubble") : Color("AssistantBubble"))
                        .overlay(
                            RoundedRectangle(cornerRadius: 18)
                                .stroke(
                                    message.role == .user ?
                                    Color("AccentBlue").opacity(0.4) :
                                        Color.white.opacity(0.1),
                                    lineWidth: 1
                                )
                        )
                )
            
            if message.role == .assistant {
                Spacer(minLength: 50)
            }
        }
    }
}

struct ActionButton: View {
    let title: String
    let icon: String
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            HStack(spacing: 6) {
                Image(systemName: icon)
                    .font(.system(size: 13))
                Text(title)
                    .font(.system(size: 13, weight: .bold, design: .monospaced))
            }
            .foregroundColor(Color("AccentBlue"))
            .padding(.horizontal, 15)
            .padding(.vertical, 10)
            .background(
                RoundedRectangle(cornerRadius: 20)
                    .fill(Color("AccentBlue").opacity(0.15))
                    .overlay(
                        RoundedRectangle(cornerRadius: 20)
                            .stroke(Color("AccentBlue").opacity(0.3), lineWidth: 1)
                    )
            )
        }
    }
}

// MARK: - Preview

#Preview {
    NavigationView {
        ChatView(subject: Subject(id: "ap_cs_a", name: "AP CS A", icon: "cupojoe", description: "Java"))
    }
}
