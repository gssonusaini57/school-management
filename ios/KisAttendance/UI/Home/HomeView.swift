import SwiftUI

struct HomeView: View {
    @EnvironmentObject var session: SessionStore
    @State private var showAbout = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Welcome,")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                        Text(session.name.isEmpty ? "Teacher" : session.name)
                            .font(.title2.bold())
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.horizontal)

                    NavigationLink {
                        TakeAttendanceView()
                    } label: {
                        HomeTile(icon: "checkmark.circle.fill",
                                 title: "Take Attendance",
                                 subtitle: "Mark today's class P / A / L",
                                 color: .green)
                    }
                    .buttonStyle(.plain)

                    NavigationLink {
                        HistoryView()
                    } label: {
                        HomeTile(icon: "clock.arrow.circlepath",
                                 title: "History",
                                 subtitle: "View past attendance",
                                 color: .blue)
                    }
                    .buttonStyle(.plain)

                    NavigationLink {
                        StudentsListView()
                    } label: {
                        HomeTile(icon: "person.3.fill",
                                 title: "Students",
                                 subtitle: "Browse class rosters",
                                 color: .purple)
                    }
                    .buttonStyle(.plain)

                    Spacer(minLength: 12)
                }
                .padding(.vertical, 12)
            }
            .navigationTitle("KIS Attendance")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Menu {
                        Button {
                            showAbout = true
                        } label: {
                            Label("About", systemImage: "info.circle")
                        }
                        Divider()
                        Button(role: .destructive) {
                            session.logout()
                        } label: {
                            Label("Log out", systemImage: "rectangle.portrait.and.arrow.right")
                        }
                    } label: {
                        Image(systemName: "ellipsis.circle")
                    }
                }
            }
            .sheet(isPresented: $showAbout) {
                AboutSheet()
            }
        }
    }
}

private struct HomeTile: View {
    let icon: String
    let title: String
    let subtitle: String
    let color: Color

    var body: some View {
        HStack(spacing: 14) {
            Image(systemName: icon)
                .font(.title)
                .foregroundStyle(color)
                .frame(width: 44, height: 44)
                .background(color.opacity(0.12))
                .clipShape(RoundedRectangle(cornerRadius: 10))
            VStack(alignment: .leading, spacing: 2) {
                Text(title).font(.headline)
                Text(subtitle).font(.subheadline).foregroundStyle(.secondary)
            }
            Spacer()
            Image(systemName: "chevron.right").foregroundStyle(.tertiary)
        }
        .padding(14)
        .background(Color(.secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 14))
        .padding(.horizontal)
    }
}

private struct AboutSheet: View {
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            List {
                LabeledContent("App", value: "KIS Attendance")
                LabeledContent("Version", value: Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "?")
                LabeledContent("Build", value: Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "?")
                LabeledContent("Bundle ID", value: Bundle.main.bundleIdentifier ?? "?")
                Section("Server") {
                    Text("expressonly.in/school")
                        .font(.callout.monospaced())
                        .foregroundStyle(.secondary)
                }
            }
            .navigationTitle("About")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") { dismiss() }
                }
            }
        }
    }
}
