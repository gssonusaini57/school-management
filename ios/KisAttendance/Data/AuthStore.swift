import Foundation
import Security

/// Keychain-backed storage for the JWT and minimal user metadata.
/// Mirrors the Android `TokenStore` (which uses EncryptedSharedPreferences).
final class AuthStore {

    static let shared = AuthStore()
    private let service = "in.expressonly.kisattendance"
    private let tokenKey = "jwt"
    private let nameKey = "name"
    private let classesKey = "allowed_classes"
    private let forcePwKey = "force_password_change"

    func saveSession(token: String, name: String, allowedClasses: [String], forcePasswordChange: Bool = false) {
        save(tokenKey, token)
        save(nameKey, name)
        save(classesKey, allowedClasses.joined(separator: "|"))
        save(forcePwKey, forcePasswordChange ? "1" : "0")
    }

    func setForcePasswordChange(_ value: Bool) {
        save(forcePwKey, value ? "1" : "0")
    }

    var token: String? { read(tokenKey) }
    var name: String? { read(nameKey) }
    var allowedClasses: [String] {
        (read(classesKey) ?? "")
            .split(separator: "|")
            .map(String.init)
            .filter { !$0.isEmpty }
    }
    var forcePasswordChange: Bool { read(forcePwKey) == "1" }

    func clear() {
        delete(tokenKey)
        delete(nameKey)
        delete(classesKey)
        delete(forcePwKey)
    }

    // MARK: - Keychain primitives

    private func save(_ key: String, _ value: String) {
        let data = Data(value.utf8)
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key
        ]
        SecItemDelete(query as CFDictionary)
        var attrs = query
        attrs[kSecValueData as String] = data
        attrs[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        SecItemAdd(attrs as CFDictionary, nil)
    }

    private func read(_ key: String) -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]
        var item: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &item) == errSecSuccess,
              let data = item as? Data,
              let str = String(data: data, encoding: .utf8) else { return nil }
        return str
    }

    private func delete(_ key: String) {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key
        ]
        SecItemDelete(query as CFDictionary)
    }
}

@MainActor
final class SessionStore: ObservableObject {
    @Published var isAuthenticated: Bool
    @Published var name: String
    @Published var allowedClasses: [String]
    @Published var forcePasswordChange: Bool

    init() {
        let store = AuthStore.shared
        self.isAuthenticated = store.token != nil
        self.name = store.name ?? ""
        self.allowedClasses = store.allowedClasses
        self.forcePasswordChange = store.forcePasswordChange
    }

    func adopt(token: String, name: String, allowedClasses: [String], forcePasswordChange: Bool = false) {
        AuthStore.shared.saveSession(
            token: token,
            name: name,
            allowedClasses: allowedClasses,
            forcePasswordChange: forcePasswordChange
        )
        self.name = name
        self.allowedClasses = allowedClasses
        self.forcePasswordChange = forcePasswordChange
        self.isAuthenticated = true
    }

    func clearForcePasswordChange() {
        AuthStore.shared.setForcePasswordChange(false)
        self.forcePasswordChange = false
    }

    func logout() {
        AuthStore.shared.clear()
        self.name = ""
        self.allowedClasses = []
        self.forcePasswordChange = false
        self.isAuthenticated = false
    }
}
