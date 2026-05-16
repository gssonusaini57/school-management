import SwiftUI

struct AppRoot: View {
    @EnvironmentObject var session: SessionStore

    var body: some View {
        Group {
            if !session.isAuthenticated {
                LoginView()
            } else if session.forcePasswordChange {
                ChangePasswordView()
            } else {
                HomeView()
            }
        }
        .onReceive(NotificationCenter.default.publisher(for: .kisAuthExpired)) { _ in
            session.logout()
        }
    }
}
