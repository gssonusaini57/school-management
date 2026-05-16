import SwiftUI

struct ChangePasswordView: View {
    @EnvironmentObject var session: SessionStore
    @State private var current = ""
    @State private var newPassword = ""
    @State private var confirm = ""
    @State private var busy = false
    @State private var errorMessage: String?

    var body: some View {
        ScrollView {
            VStack(spacing: 18) {
                Spacer(minLength: 40)
                Image(systemName: "lock.rotation")
                    .font(.system(size: 56))
                    .foregroundStyle(Color("AccentColor"))
                Text("Change password")
                    .font(.title2.bold())
                Text("You're using a temporary password. Set a new one to continue.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 24)

                VStack(alignment: .leading, spacing: 12) {
                    Text("Current password").font(.caption).foregroundStyle(.secondary)
                    SecureField("Temporary password", text: $current)
                        .textFieldStyle(.roundedBorder)

                    Text("New password (min 6 chars)").font(.caption).foregroundStyle(.secondary)
                    SecureField("New password", text: $newPassword)
                        .textFieldStyle(.roundedBorder)

                    Text("Confirm new password").font(.caption).foregroundStyle(.secondary)
                    SecureField("Repeat new password", text: $confirm)
                        .textFieldStyle(.roundedBorder)

                    if let msg = errorMessage {
                        Text(msg)
                            .font(.footnote)
                            .foregroundStyle(.red)
                    }

                    Button(action: submit) {
                        HStack {
                            if busy { ProgressView().tint(.white) }
                            Text(busy ? "Updating…" : "Update password")
                                .font(.headline)
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 12)
                        .background(Color("AccentColor"))
                        .foregroundStyle(.white)
                        .clipShape(RoundedRectangle(cornerRadius: 10))
                    }
                    .disabled(busy || !canSubmit)
                }
                .padding(.horizontal, 24)

                Button("Sign out instead") { session.logout() }
                    .font(.footnote)
                    .padding(.top, 8)
            }
        }
        .background(Color(.systemGroupedBackground))
    }

    private var canSubmit: Bool {
        !current.isEmpty && newPassword.count >= 6 && newPassword == confirm
    }

    private func submit() {
        errorMessage = nil
        busy = true
        Task {
            defer { busy = false }
            do {
                try await ApiClient.shared.changeStaffPassword(current: current, new: newPassword)
                session.clearForcePasswordChange()
            } catch {
                errorMessage = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
            }
        }
    }
}
