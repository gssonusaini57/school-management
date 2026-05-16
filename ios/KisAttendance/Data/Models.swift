import Foundation

// Mirrors backend Pydantic schemas (the same the Android DTOs target).

struct LoginRequest: Codable {
    let identifier: String
    let password: String
}

struct LoginResponse: Codable {
    let token: String
    let role: String
    let name: String
    let allowed_classes: [String]
    let force_password_change: Bool?
}

struct ChangePasswordRequest: Codable {
    let current_password: String
    let new_password: String
}

struct MeResponse: Codable {
    let role: String
    let name: String
    let allowed_classes: [String]
}

struct StudentDto: Codable, Identifiable, Hashable {
    let id: Int64
    let name: String
    let father: String?
    let mother: String?
    let dob: String?
    let gender: String?
    let phone: String?
    let aadhar: String?
    let village: String?
    let alt_phone: String?
    let religion: String?
    let prev_school: String?
    let bank_name: String?
    let bank_acc: String?
    let bank_ifsc: String?
    let annual_fee: String?
    let class_name: String
    let created_at: String?
    let added_by: String?
    let updated_at: String?
    let updated_by: String?
    let has_photo: Bool?
    let has_dob_cert: Bool?
    let has_aadhar: Bool?
}

struct AttendanceDto: Codable {
    let class_name: String
    let date: String
    /// Keys are student IDs serialised as strings ("123"); values are "P"/"A"/"L".
    let records: [String: String]
}

enum AttendanceMark: String, CaseIterable, Identifiable {
    case present = "P"
    case absent  = "A"
    case late    = "L"
    var id: String { rawValue }
    var label: String {
        switch self {
        case .present: return "Present"
        case .absent:  return "Absent"
        case .late:    return "Late"
        }
    }
}
