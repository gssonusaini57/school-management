import SwiftUI

struct StudentDetailView: View {
    let student: StudentDto

    var body: some View {
        Form {
            Section("Personal") {
                row("Name", student.name)
                row("Class", student.class_name)
                row("Father", student.father)
                row("Mother", student.mother)
                row("DOB", student.dob)
                row("Gender", student.gender)
                row("Religion", student.religion)
            }
            Section("Contact") {
                row("Phone", student.phone)
                row("Alt phone", student.alt_phone)
                row("Aadhaar", student.aadhar)
                row("Village", student.village)
            }
            Section("School") {
                row("Previous school", student.prev_school)
                row("Annual fee", student.annual_fee)
                row("Added by", student.added_by)
                row("Added", student.created_at)
            }
        }
        .navigationTitle(student.name)
        .navigationBarTitleDisplayMode(.inline)
    }

    @ViewBuilder
    private func row(_ label: String, _ value: String?) -> some View {
        if let v = value, !v.isEmpty {
            LabeledContent(label, value: v)
        }
    }
}
