import SwiftUI

@main
struct KisAttendanceApp: App {
    @StateObject private var session = SessionStore()

    var body: some Scene {
        WindowGroup {
            AppRoot()
                .environmentObject(session)
                .tint(Color("AccentColor"))
        }
    }
}
