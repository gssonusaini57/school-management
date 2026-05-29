// CSV templates shipped with the frontend. Header row + one example row each.
// Backend bulk-import endpoints accept these column names exactly.

export const STUDENTS_TEMPLATE = [
  "name,father,mother,dob,gender,village,phone,aadhar,alt_phone,religion,prev_school,bank_name,bank_acc,bank_ifsc,annual_fee,class_name,admission_no,roll_no",
  "Arjun Singh,Rajesh Singh,Sunita Singh,2015-08-15,Male,Mohali,9876543210,123456789012,,Hindu,DPS Mohali,SBI,1234567890,SBIN0001234,12000,5th,421,14",
  "Priya Kaur,Harpreet Singh,Manjit Kaur,2014-03-22,Female,Chandigarh,9988776655,987654321012,,Sikh,,,,,15000,6th,422,15",
].join("\n");

export const STAFF_TEMPLATE = [
  "name,designation,phone,assigned_classes,email",
  "Priya Sharma,Class Teacher,9876543210,5th;6th,priya.sharma@kis.local",
  "Ravi Verma,Subject Teacher,9876500000,All,ravi.verma@kis.local",
  "Anita Rao,Principal,9999988888,All,anita.rao@kis.local",
].join("\n");

export const ATTENDANCE_TEMPLATE = [
  "class_name,date,student_id,status",
  "5th,2026-05-07,1,P",
  "5th,2026-05-07,2,A",
  "5th,2026-05-07,3,L",
].join("\n");

export const CLASS_SUBJECTS_TEMPLATE = [
  "class_name,subject_name,subject_name_pa,category,order_index",
  "5th,Mathematics,ਗਣਿਤ,academic,1",
  "5th,English,ਅੰਗਰੇਜ਼ੀ,academic,2",
  "5th,Punjabi,ਪੰਜਾਬੀ,academic,3",
  "5th,Hindi,ਹਿੰਦੀ,academic,4",
  "5th,E.V.S.,ਵਾਤਾਵਰਣ,academic,5",
  "5th,Drawing,ਚਿੱਤਰਕਾਰੀ,co_curricular,10",
  "5th,Computer,ਕੰਪਿਊਟਰ,grading,11",
].join("\n");

export const MARKS_TEMPLATE = [
  "class_name,exam_type,subject,max_marks,session,student_id,marks",
  "5th,Final / Annual,Mathematics,100,2025-26,1,85",
  "5th,Final / Annual,Science,100,2025-26,1,90",
  "5th,Final / Annual,Mathematics,100,2025-26,2,72",
].join("\n");
