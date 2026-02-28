//
//  AuthManager.swift
//  Ascent Scholars
//
//  Manages authentication state
//

import Foundation
import Combine

class AuthManager: ObservableObject {
    static let shared = AuthManager()
    
    @Published var isAuthenticated = false
    @Published var currentUser: User?
    
    private let userDefaultsKey = "ascent_scholars_user"
    
    private init() {
        loadUser()
    }
    
    func login(googleId: String, email: String, name: String, picture: String?) {
        let user = User(
            id: UUID().uuidString,
            googleId: googleId,
            email: email,
            name: name,
            picture: picture
        )
        
        currentUser = user
        isAuthenticated = true
        
        saveUser(user)
    }
    
    func logout() {
        currentUser = nil
        isAuthenticated = false
        
        UserDefaults.standard.removeObject(forKey: userDefaultsKey)
    }
    
    private func saveUser(_ user: User) {
        if let encoded = try? JSONEncoder().encode(user) {
            UserDefaults.standard.set(encoded, forKey: userDefaultsKey)
        }
    }
    
    private func loadUser() {
        if let data = UserDefaults.standard.data(forKey: userDefaultsKey),
           let user = try? JSONDecoder().decode(User.self, from: data) {
            currentUser = user
            isAuthenticated = true
        }
    }
}

struct User: Codable {
    let id: String
    let googleId: String
    let email: String
    let name: String
    let picture: String?
}
