//
//  ChatViewModel.swift
//  Ascent Scholars
//
//  View model for chat functionality
//

import Foundation
import Combine

class ChatViewModel: ObservableObject {
    @Published var messages: [Message] = []
    @Published var isLoading = false
    @Published var showError = false
    @Published var errorMessage = ""
    
    let subject: Subject
    private var conversationId: Int?
    private let apiService = APIService.shared
    private var cancellables = Set<AnyCancellable>()
    
    init(subject: Subject) {
        self.subject = subject
    }
    
    func sendMessage(_ text: String) {
        // Add user message immediately
        let userMessage = Message(role: .user, content: text)
        messages.append(userMessage)
        
        isLoading = true
        
        apiService.sendMessage(text, subject: subject.id, conversationId: conversationId)
            .receive(on: DispatchQueue.main)
            .sink { [weak self] completion in
                self?.isLoading = false
                
                if case .failure(let error) = completion {
                    self?.showError(error.localizedDescription)
                }
            } receiveValue: { [weak self] response in
                // Add assistant message
                let assistantMessage = Message(role: .assistant, content: response.response)
                self?.messages.append(assistantMessage)
                
                // Save conversation ID
                if let convId = response.conversationId {
                    self?.conversationId = convId
                }
            }
            .store(in: &cancellables)
    }
    
    func getPracticeQuestions() {
        isLoading = true
        
        apiService.getPractice(subject: subject.id, conversationId: conversationId)
            .receive(on: DispatchQueue.main)
            .sink { [weak self] completion in
                self?.isLoading = false
                
                if case .failure(let error) = completion {
                    self?.showError(error.localizedDescription)
                }
            } receiveValue: { [weak self] response in
                let practiceMessage = Message(
                    role: .assistant,
                    content: "Practice Resources: \(response.topic ?? "")\n\n\(response.response)"
                )
                self?.messages.append(practiceMessage)
            }
            .store(in: &cancellables)
    }
    
    func getSummary() {
        guard conversationId != nil else {
            showError("No conversation to summarize yet")
            return
        }
        
        isLoading = true
        
        apiService.getSummary(subject: subject.id, conversationId: conversationId)
            .receive(on: DispatchQueue.main)
            .sink { [weak self] completion in
                self?.isLoading = false
                
                if case .failure(let error) = completion {
                    self?.showError(error.localizedDescription)
                }
            } receiveValue: { [weak self] response in
                let summaryMessage = Message(
                    role: .assistant,
                    content: "📝 Session Summary\n\n\(response.summary)"
                )
                self?.messages.append(summaryMessage)
            }
            .store(in: &cancellables)
    }
    
    func exportChat() {
        guard conversationId != nil else {
            showError("No conversation to export yet")
            return
        }
        
        apiService.exportChat(subject: subject.id, conversationId: conversationId)
            .receive(on: DispatchQueue.main)
            .sink { [weak self] completion in
                if case .failure(let error) = completion {
                    self?.showError(error.localizedDescription)
                }
            } receiveValue: { response in
                // Share the exported content
                self.shareText(response.content)
            }
            .store(in: &cancellables)
    }
    
    func clearChat() {
        messages.removeAll()
        conversationId = nil
        
        apiService.clearChat(conversationId: conversationId)
            .receive(on: DispatchQueue.main)
            .sink { _ in } receiveValue: { _ in }
            .store(in: &cancellables)
    }
    
    private func showError(_ message: String) {
        errorMessage = message
        showError = true
    }
    
    private func shareText(_ text: String) {
        let activityVC = UIActivityViewController(
            activityItems: [text],
            applicationActivities: nil
        )
        
        if let windowScene = UIApplication.shared.connectedScenes.first as? UIWindowScene,
           let window = windowScene.windows.first,
           let rootVC = window.rootViewController {
            rootVC.present(activityVC, animated: true)
        }
    }
}

// MARK: - Message Model

struct Message: Identifiable, Codable {
    let id: UUID
    let role: MessageRole
    let content: String
    
    init(id: UUID = UUID(), role: MessageRole, content: String) {
        self.id = id
        self.role = role
        self.content = content
    }
}

enum MessageRole: String, Codable {
    case user
    case assistant
}
