//
//  APIService.swift
//  Ascent Scholars
//
//  API service for backend communication
//

import Foundation
import Combine

class APIService {
    static let shared = APIService()
    
    // Change this to your actual backend URL
    private let baseURL = "https://tutor.noros.life/api"
    // For local testing: "http://localhost:5000/api"
    
    private init() {}
    
    // MARK: - Chat Endpoints
    
    func sendMessage(_ message: String, subject: String, conversationId: Int?) -> AnyPublisher<ChatResponse, Error> {
        let url = URL(string: "\(baseURL)/chat")!
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body: [String: Any] = [
            "message": message,
            "subject": subject,
            "conversation_id": conversationId as Any
        ]
        
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        
        return URLSession.shared.dataTaskPublisher(for: request)
            .tryMap { output in
                guard let httpResponse = output.response as? HTTPURLResponse,
                      (200...299).contains(httpResponse.statusCode) else {
                    throw APIError.serverError
                }
                return output.data
            }
            .decode(type: ChatResponse.self, decoder: JSONDecoder())
            .eraseToAnyPublisher()
    }
    
    func getPractice(subject: String, conversationId: Int?) -> AnyPublisher<PracticeResponse, Error> {
        let url = URL(string: "\(baseURL)/practice")!
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body: [String: Any] = [
            "subject": subject,
            "conversation_id": conversationId as Any
        ]
        
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        
        return URLSession.shared.dataTaskPublisher(for: request)
            .tryMap { output in
                guard let httpResponse = output.response as? HTTPURLResponse,
                      (200...299).contains(httpResponse.statusCode) else {
                    throw APIError.serverError
                }
                return output.data
            }
            .decode(type: PracticeResponse.self, decoder: JSONDecoder())
            .eraseToAnyPublisher()
    }
    
    func getSummary(subject: String, conversationId: Int?) -> AnyPublisher<SummaryResponse, Error> {
        let url = URL(string: "\(baseURL)/summary")!
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body: [String: Any] = [
            "subject": subject,
            "conversation_id": conversationId as Any
        ]
        
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        
        return URLSession.shared.dataTaskPublisher(for: request)
            .tryMap { output in
                guard let httpResponse = output.response as? HTTPURLResponse,
                      (200...299).contains(httpResponse.statusCode) else {
                    throw APIError.serverError
                }
                return output.data
            }
            .decode(type: SummaryResponse.self, decoder: JSONDecoder())
            .eraseToAnyPublisher()
    }
    
    func exportChat(subject: String, conversationId: Int?) -> AnyPublisher<ExportResponse, Error> {
        let url = URL(string: "\(baseURL)/export")!
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body: [String: Any] = [
            "subject": subject,
            "conversation_id": conversationId as Any
        ]
        
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        
        return URLSession.shared.dataTaskPublisher(for: request)
            .tryMap { output in
                guard let httpResponse = output.response as? HTTPURLResponse,
                      (200...299).contains(httpResponse.statusCode) else {
                    throw APIError.serverError
                }
                return output.data
            }
            .decode(type: ExportResponse.self, decoder: JSONDecoder())
            .eraseToAnyPublisher()
    }
    
    func clearChat(conversationId: Int?) -> AnyPublisher<SuccessResponse, Error> {
        let url = URL(string: "\(baseURL)/clear")!
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body: [String: Any] = [
            "conversation_id": conversationId as Any
        ]
        
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        
        return URLSession.shared.dataTaskPublisher(for: request)
            .tryMap { output in
                guard let httpResponse = output.response as? HTTPURLResponse,
                      (200...299).contains(httpResponse.statusCode) else {
                    throw APIError.serverError
                }
                return output.data
            }
            .decode(type: SuccessResponse.self, decoder: JSONDecoder())
            .eraseToAnyPublisher()
    }
}

// MARK: - Response Models

struct ChatResponse: Codable {
    let success: Bool
    let response: String
    let conversationId: Int?
    
    enum CodingKeys: String, CodingKey {
        case success
        case response
        case conversationId = "conversation_id"
    }
}

struct PracticeResponse: Codable {
    let success: Bool
    let topic: String?
    let response: String
}

struct SummaryResponse: Codable {
    let success: Bool
    let summary: String
}

struct ExportResponse: Codable {
    let success: Bool
    let content: String
}

struct SuccessResponse: Codable {
    let success: Bool
}

enum APIError: LocalizedError {
    case invalidURL
    case serverError
    case decodingError
    
    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid URL"
        case .serverError:
            return "Server error occurred"
        case .decodingError:
            return "Failed to decode response"
        }
    }
}
