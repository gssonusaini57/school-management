import SwiftUI

struct StudentsListView: View {
    @EnvironmentObject var session: SessionStore
    @State private var selectedClass: String = ""
    @State private var students: [StudentDto] = []
    @State private var loading = false
    @State private var message: String?

    private var classes: [String] { session.allowedClasses.isEmpty ? ALL_CLASSES : session.allowedClasses }

    var body: some View {
        VStack(spacing: 0) {
            Picker("Class", selection: $selectedClass) {
                ForEach(classes, id: \.self) { Text($0).tag($0) }
            }
            .pickerStyle(.segmented)
            .padding()

            if loading {
                ProgressView().padding()
                Spacer()
            } else if let msg = message {
                Text(msg).foregroundStyle(.red).padding()
                Spacer()
            } else {
                List(students) { s in
                    NavigationLink {
                        StudentDetailView(student: s)
                    } label: {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(s.name).font(.headline)
                            if let father = s.father, !father.isEmpty {
                                Text("Father: \(father)").font(.caption).foregroundStyle(.secondary)
                            }
                        }
                    }
                }
                .listStyle(.plain)
            }
        }
        .navigationTitle("Students")
        .navigationBarTitleDisplayMode(.inline)
        .onAppear {
            if selectedClass.isEmpty, let first = classes.first { selectedClass = first }
        }
        .onChange(of: selectedClass) { _, _ in load() }
        .task(id: selectedClass) { load() }
    }

    private func load() {
        guard !selectedClass.isEmpty else { return }
        loading = true
        message = nil
        Task {
            defer { loading = false }
            do {
                students = try await ApiClient.shared.students(className: selectedClass)
            } catch {
                message = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
            }
        }
    }
}
