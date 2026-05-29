import Foundation

enum ApiError: LocalizedError {
    case notAuthorized
    case http(Int, String)
    case decoding(Error)
    case transport(Error)

    var errorDescription: String? {
        switch self {
        case .notAuthorized:        return "Session expired — please sign in again."
        case .http(let code, let msg): return msg.isEmpty ? "HTTP \(code)" : msg
        case .decoding:             return "The server response was not in the expected format."
        case .transport(let err):   return err.localizedDescription
        }
    }
}

/// HTTP client that mounts every call under `https://kisschool.in/api/`,
/// attaches the JWT, and broadcasts a logout request on 401.
final class ApiClient {

    static let shared = ApiClient()

    private let baseURL = URL(string: "https://kisschool.in/api/")!
    private let session: URLSession

    /// SwiftUI views observe this stream to react to forced logouts (mirrors the
    /// `authExpired` SharedFlow in the Android app).
    let authExpired = NotificationCenter.default

    private init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        self.session = URLSession(configuration: config)
    }

    // MARK: - Public API

    func login(identifier: String, password: String) async throws -> LoginResponse {
        try await post(path: "auth/login",
                       body: LoginRequest(identifier: identifier, password: password),
                       authed: false)
    }

    func changeStaffPassword(current: String, new: String) async throws {
        let _: EmptyResponse = try await post(
            path: "staff/change-password",
            body: ChangePasswordRequest(current_password: current, new_password: new)
        )
    }

    func me() async throws -> MeResponse {
        try await get(path: "auth/me")
    }

    func students(className: String) async throws -> [StudentDto] {
        try await get(path: "students", query: ["class": className])
    }

    func attendance(className: String, date: String) async throws -> AttendanceDto? {
        do {
            return try await get(path: "attendance", query: ["class": className, "date": date]) as AttendanceDto
        } catch ApiError.http(404, _) {
            return nil
        }
    }

    func saveAttendance(_ body: AttendanceDto) async throws {
        let _: EmptyResponse = try await put(path: "attendance", body: body)
    }

    // MARK: - Plumbing

    private struct EmptyResponse: Decodable {}

    private func get<T: Decodable>(path: String, query: [String: String] = [:]) async throws -> T {
        try await send(method: "GET", path: path, query: query, body: Optional<EmptyResponse>.none)
    }

    private func post<T: Decodable, B: Encodable>(path: String, body: B, authed: Bool = true) async throws -> T {
        try await send(method: "POST", path: path, body: body, authed: authed)
    }

    private func put<T: Decodable, B: Encodable>(path: String, body: B) async throws -> T {
        try await send(method: "PUT", path: path, body: body)
    }

    private func send<T: Decodable, B: Encodable>(
        method: String,
        path: String,
        query: [String: String] = [:],
        body: B?,
        authed: Bool = true
    ) async throws -> T {
        var components = URLComponents(url: baseURL.appendingPathComponent(path), resolvingAgainstBaseURL: false)!
        if !query.isEmpty {
            components.queryItems = query.map { URLQueryItem(name: $0.key, value: $0.value) }
        }
        var req = URLRequest(url: components.url!)
        req.httpMethod = method
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        if authed, let token = AuthStore.shared.token {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        if let body = body {
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
            req.httpBody = try JSONEncoder().encode(body)
        }

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: req)
        } catch {
            throw ApiError.transport(error)
        }

        guard let http = response as? HTTPURLResponse else {
            throw ApiError.http(-1, "Invalid response")
        }
        switch http.statusCode {
        case 200..<300:
            if T.self == EmptyResponse.self { return EmptyResponse() as! T }
            do { return try JSONDecoder().decode(T.self, from: data) }
            catch { throw ApiError.decoding(error) }
        case 401:
            await MainActor.run {
                NotificationCenter.default.post(name: .kisAuthExpired, object: nil)
            }
            throw ApiError.notAuthorized
        default:
            let msg = (try? JSONDecoder().decode(ErrorBody.self, from: data))?.detail
                ?? String(data: data, encoding: .utf8)
                ?? ""
            throw ApiError.http(http.statusCode, msg)
        }
    }

    private struct ErrorBody: Decodable { let detail: String? }
}

extension Notification.Name {
    static let kisAuthExpired = Notification.Name("kis.authExpired")
}
