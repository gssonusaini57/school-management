import SwiftUI

struct ForgotPasswordView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var identifier = ""
    @State private var error: String?
    @State private var loading = false
    @State private var sent = false

    var body: some View {
        VStack(spacing: 16) {
            Spacer()
            Text("Forgot password").font(.title2).bold()

            if sent {
                Text("If that account exists, a password reset link has been sent. "
                    + "Open the link in your browser to choose a new password.")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
                Button("Back to sign in") { dismiss() }
                    .buttonStyle(.borderedProminent)
                    .padding(.top, 8)
            } else {
                Text("Enter your account email or phone and we'll send a reset link to your email.")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)

                TextField("Email or phone", text: $identifier)
                    .textFieldStyle(.roundedBorder)
                    .autocapitalization(.none)
                    .keyboardType(.emailAddress)

                if let error = error {
                    Text(error).font(.caption).foregroundColor(.red)
                }

                Button(action: submit) {
                    if loading {
                        ProgressView()
                    } else {
                        Text("Send reset link").bold().frame(maxWidth: .infinity)
                    }
                }
                .buttonStyle(.borderedProminent)
                .disabled(loading)

                Button("Cancel") { dismiss() }
                    .padding(.top, 4)
            }
            Spacer()
        }
        .padding(24)
    }

    private func submit() {
        let trimmed = identifier.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            error = "Enter your email or phone"
            return
        }
        loading = true
        error = nil
        Task {
            do {
                try await ApiClient.shared.forgotPassword(identifier: trimmed)
                sent = true
                loading = false
            } catch {
                self.error = error.localizedDescription
                self.loading = false
            }
        }
    }
}
