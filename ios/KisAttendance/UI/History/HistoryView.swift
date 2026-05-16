import SwiftUI

struct HistoryView: View {
    @EnvironmentObject var session: SessionStore
    @State private var selectedClass: String = ""
    @State private var date: Date = Date()
    @State private var record: AttendanceDto?
    @State private var roster: [StudentDto] = []
    @State private var loading = false
    @State private var message: String?

    private var classes: [String] { session.allowedClasses.isEmpty ? ALL_CLASSES : session.allowedClasses }

    var body: some View {
        Form {
            Section {
                Picker("Class", selection: $selectedClass) {
                    ForEach(classes, id: \.self) { Text($0).tag($0) }
                }
                DatePicker("Date", selection: $date, displayedComponents: .date)
            }

            Section {
                if loading {
                    HStack { ProgressView(); Text("Loading…") }
                } else if record == nil {
                    Text("No attendance saved for this class on this date.")
                        .foregroundStyle(.secondary)
                } else {
                    ForEach(roster) { s in
                        let mark = record?.records[String(s.id)] ?? "—"
                        HStack {
                            Text(s.name)
                            Spacer()
                            Text(mark)
                                .font(.callout.bold())
                                .frame(width: 32, height: 28)
                                .background(color(forRaw: mark))
                                .foregroundStyle(.white)
                                .clipShape(RoundedRectangle(cornerRadius: 6))
                        }
                    }
                }
            } header: {
                Text("Roster")
            } footer: {
                if let msg = message { Text(msg).foregroundStyle(.red) }
            }
        }
        .navigationTitle("Attendance History")
        .navigationBarTitleDisplayMode(.inline)
        .onAppear {
            if selectedClass.isEmpty, let first = classes.first { selectedClass = first }
        }
        .onChange(of: selectedClass) { _, _ in load() }
        .onChange(of: date) { _, _ in load() }
        .task(id: selectedClass) { load() }
    }

    private func color(forRaw raw: String) -> Color {
        switch raw {
        case "P": return .green
        case "A": return .red
        case "L": return .orange
        default:  return .gray
        }
    }

    private func load() {
        guard !selectedClass.isEmpty else { return }
        loading = true
        message = nil
        Task {
            defer { loading = false }
            do {
                let roster = try await ApiClient.shared.students(className: selectedClass)
                let rec = try await ApiClient.shared.attendance(className: selectedClass, date: dateString)
                self.roster = roster
                self.record = rec
            } catch {
                message = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
            }
        }
    }

    private var dateString: String {
        let f = DateFormatter()
        f.dateFormat = "yyyy-MM-dd"
        return f.string(from: date)
    }
}
