import React from 'react';
import { Document, Page, View, Text, Image, s, COLOR, formatDateLong, LetterheadHeaderA, LetterheadFooter, BilingualText } from './_shared';

type Data = {
  session: string;
  student: { name: { en: string; pa: string }; class: string; section: string; rollNo: string; fatherName: { en: string; pa: string }; motherName: { en: string; pa: string }; dob: string; house: string; photoUrl?: string };
  subjects: { name: { en: string; pa: string }; marks: number; max: number; grade?: string }[];
  summary: { total: number; max: number; percentage: number; rank: number; attendancePct: number; remarks?: { en: string; pa: string }; promotion: string };
  signatures?: { classTeacher: string; principal: string };
};

export const ReportCard: React.FC<{ data: Data }> = ({ data }) => (
  <Document>
    <Page size="A4" style={s.page}>
      <LetterheadHeaderA />

      <View style={{ alignItems: 'center', marginBottom: 12 }}>
        <Text style={{ fontFamily: 'Playfair Display', fontSize: 18, color: COLOR.blue }}>Annual Report Card</Text>
        <Text style={{ fontFamily: 'Noto Sans Gurmukhi', fontSize: 11, color: COLOR.indigo }}>ਸਾਲਾਨਾ ਰਿਪੋਰਟ ਕਾਰਡ</Text>
        <Text style={{ fontSize: 9, color: '#6B7280', marginTop: 2 }}>Academic Session {data.session}</Text>
      </View>

      <View style={{ flexDirection: 'row', backgroundColor: COLOR.cream, padding: 10, marginBottom: 12 }}>
        <View style={{ flex: 1 }}>
          <Row label="Student" value={data.student.name.en} valuePa={data.student.name.pa} />
          <Row label="Father" value={data.student.fatherName.en} valuePa={data.student.fatherName.pa} />
          <Row label="Mother" value={data.student.motherName.en} valuePa={data.student.motherName.pa} />
        </View>
        <View style={{ width: 160 }}>
          <Row label="Class" value={`${data.student.class} — ${data.student.section}`} />
          <Row label="Roll No" value={data.student.rollNo} />
          <Row label="DOB" value={formatDateLong(data.student.dob)} />
          <Row label="House" value={data.student.house} />
        </View>
      </View>

      <View style={{ borderWidth: 1, borderColor: COLOR.rule }}>
        <View style={{ flexDirection: 'row', backgroundColor: COLOR.blue, padding: 6 }}>
          <Text style={{ flex: 2, color: 'white', fontWeight: 700 }}>Subject</Text>
          <Text style={{ width: 60, color: 'white', fontWeight: 700, textAlign: 'right' }}>Marks</Text>
          <Text style={{ width: 60, color: 'white', fontWeight: 700, textAlign: 'right' }}>Max</Text>
          <Text style={{ width: 50, color: 'white', fontWeight: 700, textAlign: 'right' }}>Grade</Text>
        </View>
        {data.subjects.map((sub, i) => (
          <View key={i} style={{ flexDirection: 'row', padding: 6, borderTopWidth: i === 0 ? 0 : 1, borderTopColor: COLOR.rule, backgroundColor: i % 2 ? '#F9FAFB' : 'white' }}>
            <View style={{ flex: 2 }}><BilingualText value={sub.name} /></View>
            <Text style={{ width: 60, textAlign: 'right' }}>{sub.marks}</Text>
            <Text style={{ width: 60, textAlign: 'right', color: '#6B7280' }}>{sub.max}</Text>
            <Text style={{ width: 50, textAlign: 'right', fontWeight: 700, color: COLOR.blue }}>{sub.grade || '—'}</Text>
          </View>
        ))}
      </View>

      <View style={{ flexDirection: 'row', marginTop: 12, gap: 8 }}>
        <Stat label="Total" value={`${data.summary.total}/${data.summary.max}`} />
        <Stat label="Percentage" value={`${data.summary.percentage.toFixed(2)}%`} />
        <Stat label="Rank" value={String(data.summary.rank)} />
        <Stat label="Attendance" value={`${data.summary.attendancePct}%`} />
        <Stat label="Result" value={data.summary.promotion} highlight />
      </View>

      {data.summary.remarks && (
        <View style={{ marginTop: 12, padding: 8, borderLeftWidth: 3, borderLeftColor: COLOR.gold }}>
          <Text style={{ fontSize: 8, color: '#6B7280', marginBottom: 2 }}>REMARKS</Text>
          <BilingualText value={data.summary.remarks} />
        </View>
      )}

      {data.signatures && (
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginTop: 36 }}>
          <SigSlot label="Class Teacher" name={data.signatures.classTeacher} />
          <SigSlot label="Principal" name={data.signatures.principal} />
        </View>
      )}

      <LetterheadFooter />
    </Page>
  </Document>
);

const Row: React.FC<{ label: string; value: string; valuePa?: string }> = ({ label, value, valuePa }) => (
  <View style={{ flexDirection: 'row', marginBottom: 3 }}>
    <Text style={{ width: 60, fontSize: 8, color: '#6B7280' }}>{label.toUpperCase()}</Text>
    <View style={{ flex: 1 }}>
      <Text style={{ fontSize: 10 }}>{value}</Text>
      {valuePa && <Text style={{ fontFamily: 'Noto Sans Gurmukhi', fontSize: 9, color: '#374151' }}>{valuePa}</Text>}
    </View>
  </View>
);

const Stat: React.FC<{ label: string; value: string; highlight?: boolean }> = ({ label, value, highlight }) => (
  <View style={{ flex: 1, padding: 8, borderWidth: 1, borderColor: COLOR.rule, backgroundColor: highlight ? COLOR.cream : 'white', alignItems: 'center' }}>
    <Text style={{ fontSize: 7, color: '#6B7280' }}>{label.toUpperCase()}</Text>
    <Text style={{ fontWeight: 700, fontSize: 12, color: highlight ? COLOR.blue : COLOR.ink, marginTop: 2 }}>{value}</Text>
  </View>
);

const SigSlot: React.FC<{ label: string; name: string }> = ({ label, name }) => (
  <View style={{ alignItems: 'center', width: 180 }}>
    <View style={{ width: '100%', borderBottomWidth: 1, borderBottomColor: COLOR.ink, marginBottom: 4 }} />
    <Text style={{ fontWeight: 700, fontSize: 9 }}>{name}</Text>
    <Text style={{ fontSize: 8, color: '#6B7280' }}>{label}</Text>
  </View>
);
