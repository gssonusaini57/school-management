import SwiftUI

struct TakeAttendanceView: View {
    @EnvironmentObject var session: SessionStore

    @State private var selectedClass: String = ""
    @State private var date: Date = Date()
    @State private var students: [StudentDto] = []
    @State private var marks: [Int64: AttendanceMark] = [:]
    @State private var loading = false
    @State private var saving = false
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
                    HStack { ProgressView(); Text("Loading roster…") }
                } else if students.isEmpty {
                    Text("Pick a class to load students")
                        .foregroundStyle(.secondary)
                } else {
                    ForEach(students) { s in
                        HStack {
                            Text(s.name).font(.body)
                            Spacer()
                            ForEach(AttendanceMark.allCases) { m in
                                Button {
                                    marks[s.id] = m
                                } label: {
                                    Text(m.rawValue)
                                        .font(.callout.bold())
                                        .frame(width: 36, height: 32)
                                        .background(marks[s.id] == m ? color(for: m) : Color(.tertiarySystemFill))
                                        .foregroundStyle(marks[s.id] == m ? .white : .primary)
                                        .clipShape(RoundedRectangle(cornerRadius: 8))
                                }
                                .buttonStyle(.plain)
                            }
                        }
                        .padding(.vertical, 4)
                    }
                }
            } header: {
                Text("Roster")
            } footer: {
                if let msg = message { Text(msg).foregroundStyle(.red) }
            }

            if !students.isEmpty {
                Section {
                    Button(action: save) {
                        HStack {
                            if saving { ProgressView() }
                            Text(saving ? "Saving…" : "Save attendance")
                                .frame(maxWidth: .infinity)
                                .font(.headline)
                        }
                    }
                    .disabled(saving)
                }
            }
        }
        .navigationTitle("Take Attendance")
        .navigationBarTitleDisplayMode(.inline)
        .onAppear {
            if selectedClass.isEmpty, let first = classes.first { selectedClass = first }
        }
        .onChange(of: selectedClass) { _, _ in load() }
        .onChange(of: date) { _, _ in load() }
        .task(id: selectedClass) { load() }
    }

    private func color(for mark: AttendanceMark) -> Color {
        switch mark {
        case .present: return .green
        case .absent:  return .red
        case .late:    return .orange
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
                let existing = try await ApiClient.shared.attendance(className: selectedClass, date: dateString)
                students = roster
                var initial: [Int64: AttendanceMark] = [:]
                for s in roster {
                    if let raw = existing?.records[String(s.id)], let m = AttendanceMark(rawValue: raw) {
                        initial[s.id] = m
                    } else {
                        initial[s.id] = .present
                    }
                }
                marks = initial
            } catch {
                message = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
            }
        }
    }

    private func save() {
        saving = true
        message = nil
        Task {
            defer { saving = false }
            do {
                let body = AttendanceDto(
                    class_name: selectedClass,
                    date: dateString,
                    records: marks.reduce(into: [:]) { acc, kv in acc[String(kv.key)] = kv.value.rawValue }
                )
                try await ApiClient.shared.saveAttendance(body)
                message = "Saved ✓"
            } catch {
                message = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
            }
        }
    }

    private var dateString: String {
        let f = DateFormatter()
        f.dateFormat = "yyyy-MM-dd"
        f.timeZone = .current
        return f.string(from: date)
    }
}

let ALL_CLASSES = [
    "Nursery", "L.K.G", "U.K.G",
    "1st", "2nd", "3rd", "4th", "5th", "6th",
    "7th", "8th", "9th", "10th", "11th", "12th"
]
