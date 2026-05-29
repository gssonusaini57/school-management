import SwiftUI

struct LoginView: View {
    @EnvironmentObject var session: SessionStore
    @State private var identifier: String = ""
    @State private var password: String = ""
    @State private var busy = false
    @State private var errorMessage: String?
    @FocusState private var focused: Field?

    enum Field { case identifier, password }

    var body: some View {
        ScrollView {
            VStack(spacing: 18) {
                Spacer(minLength: 60)
                Image(systemName: "graduationcap.fill")
                    .font(.system(size: 56))
                    .foregroundStyle(Color("AccentColor"))
                Text("KIS School Management")
                    .font(.title2.bold())
                Text("Sign in")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)

                VStack(alignment: .leading, spacing: 12) {
                    Text("Email or phone").font(.caption).foregroundStyle(.secondary)
                    TextField("nsnishasaini57@gmail.com or your phone number", text: $identifier)
                        .textFieldStyle(.roundedBorder)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .keyboardType(.emailAddress)
                        .focused($focused, equals: .identifier)

                    Text("Password").font(.caption).foregroundStyle(.secondary)
                    SecureField("Password", text: $password)
                        .textFieldStyle(.roundedBorder)
                        .focused($focused, equals: .password)

                    if let msg = errorMessage {
                        Text(msg)
                            .font(.footnote)
                            .foregroundStyle(.red)
                    }

                    Button(action: submit) {
                        HStack {
                            if busy { ProgressView().tint(.white) }
                            Text(busy ? "Signing in…" : "Sign in")
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
                .padding(.vertical, 8)

                Spacer(minLength: 20)
                Text(versionLabel())
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .padding(.bottom, 12)
            }
        }
        .background(Color(.systemGroupedBackground))
    }

    private var canSubmit: Bool {
        !identifier.isEmpty && !password.isEmpty
    }

    private func submit() {
        focused = nil
        errorMessage = nil
        busy = true
        Task {
            defer { busy = false }
            do {
                let resp = try await ApiClient.shared.login(
                    identifier: identifier.trimmingCharacters(in: .whitespaces),
                    password: password
                )
                session.adopt(
                    token: resp.token,
                    name: resp.name,
                    allowedClasses: resp.allowed_classes,
                    forcePasswordChange: resp.force_password_change ?? false
                )
            } catch {
                errorMessage = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
            }
        }
    }
}

func versionLabel() -> String {
    let info = Bundle.main.infoDictionary
    let v = info?["CFBundleShortVersionString"] as? String ?? "?"
    let b = info?["CFBundleVersion"] as? String ?? "?"
    return "v\(v) · build \(b)"
}
