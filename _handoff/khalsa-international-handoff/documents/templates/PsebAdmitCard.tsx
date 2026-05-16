import React from 'react';
import { Document, Page, View, Text, Image, s, COLOR, formatDateShort, LetterheadHeaderA, LetterheadFooter, BilingualText } from './_shared';

type Data = {
  schoolCode: string; studentId: string;
  centre: { code: string; schoolCode: string; district: string; set: string; name: { en: string; pa: string } };
  candidate: { rollNo: string; regNo: string; name: { en: string; pa: string }; fatherName: { en: string; pa: string }; motherName: { en: string; pa: string }; dob: string; differentlyAbled?: string; category: string; photoUrl?: string };
  examTime: { en: string; pa: string };
  practicalDateRange?: { from: string; to: string };
  dateSheet: { subCode: string; subject: { en: string; pa: string }; theoryDate: string; practical: string }[];
  instructions: { en: string; pa: string }[];
};

export const PsebAdmitCard: React.FC<{ data: Data }> = ({ data }) => (
  <Document>
    <Page size="A4" style={s.page}>
      <LetterheadHeaderA />

      <View style={{ alignItems: 'center', marginBottom: 10 }}>
        <Text style={{ fontFamily: 'Playfair Display', fontSize: 16, color: COLOR.blue }}>PSEB Admit Card · Class X</Text>
        <Text style={{ fontFamily: 'Noto Sans Gurmukhi', fontSize: 10, color: COLOR.indigo }}>PSEB ਪ੍ਰਵੇਸ਼ ਪੱਤਰ · ਜਮਾਤ X</Text>
        <Text style={{ fontSize: 8, color: '#6B7280', marginTop: 2 }}>Annual Examination 2026</Text>
      </View>

      <View style={{ flexDirection: 'row', backgroundColor: COLOR.cream, padding: 8, marginBottom: 10, gap: 8 }}>
        <KV label="School Code" value={data.schoolCode} />
        <KV label="Student ID" value={data.studentId} />
        <KV label="Centre Code" value={data.centre.code} />
        <KV label="Centre School" value={data.centre.schoolCode} />
        <KV label="District" value={data.centre.district} />
        <KV label="Set" value={data.centre.set} />
      </View>

      <View style={{ flexDirection: 'row', marginBottom: 10 }}>
        <View style={{ flex: 1 }}>
          <Row label="Candidate" en={data.candidate.name.en} pa={data.candidate.name.pa} />
          <Row label="Father" en={data.candidate.fatherName.en} pa={data.candidate.fatherName.pa} />
          <Row label="Mother" en={data.candidate.motherName.en} pa={data.candidate.motherName.pa} />
          <View style={{ flexDirection: 'row', gap: 12, marginTop: 4 }}>
            <Mini label="Roll No" value={data.candidate.rollNo} />
            <Mini label="Reg No" value={data.candidate.regNo} />
            <Mini label="DOB" value={formatDateShort(data.candidate.dob)} />
            <Mini label="Category" value={data.candidate.category} />
            <Mini label="Diff. Abled" value={data.candidate.differentlyAbled || 'N.A.'} />
          </View>
        </View>
        <View style={{ width: 170, alignItems: 'center' }}>
          <View style={{ width: 110, height: 130, borderWidth: 1, borderColor: COLOR.ink, alignItems: 'center', justifyContent: 'center' }}>
            {data.candidate.photoUrl ? <Image src={data.candidate.photoUrl} style={{ width: '100%', height: '100%' }} /> : <Text style={{ fontSize: 7, color: '#9CA3AF' }}>CANDIDATE PHOTO</Text>}
          </View>
          <Text style={{ fontSize: 7, color: '#6B7280', marginTop: 4 }}>Affix attested photograph</Text>
        </View>
      </View>

      <View style={{ marginBottom: 8 }}>
        <Text style={{ fontSize: 8, color: '#6B7280' }}>EXAM CENTRE</Text>
        <BilingualText value={data.centre.name} />
      </View>

      <View style={{ flexDirection: 'row', gap: 8, marginBottom: 10 }}>
        <View style={{ flex: 1, padding: 6, borderWidth: 1, borderColor: COLOR.rule }}>
          <Text style={{ fontSize: 8, color: '#6B7280' }}>EXAM TIME</Text>
          <BilingualText value={data.examTime} />
        </View>
        {data.practicalDateRange && (
          <View style={{ flex: 1, padding: 6, borderWidth: 1, borderColor: COLOR.rule }}>
            <Text style={{ fontSize: 8, color: '#6B7280' }}>PRACTICAL DATES</Text>
            <Text>{data.practicalDateRange.from} → {data.practicalDateRange.to}</Text>
          </View>
        )}
      </View>

      <View style={{ borderWidth: 1, borderColor: COLOR.rule, marginBottom: 10 }}>
        <View style={{ flexDirection: 'row', backgroundColor: COLOR.blue, padding: 5 }}>
          <Text style={{ width: 50, color: 'white', fontWeight: 700, fontSize: 9 }}>Code</Text>
          <Text style={{ flex: 1, color: 'white', fontWeight: 700, fontSize: 9 }}>Subject</Text>
          <Text style={{ width: 80, color: 'white', fontWeight: 700, fontSize: 9 }}>Theory Date</Text>
          <Text style={{ width: 50, color: 'white', fontWeight: 700, fontSize: 9, textAlign: 'center' }}>Pract.</Text>
        </View>
        {data.dateSheet.map((d, i) => (
          <View key={i} style={{ flexDirection: 'row', padding: 5, borderTopWidth: 1, borderTopColor: COLOR.rule }}>
            <Text style={{ width: 50, fontSize: 9 }}>{d.subCode}</Text>
            <View style={{ flex: 1 }}><BilingualText value={d.subject} /></View>
            <Text style={{ width: 80, fontSize: 9 }}>{d.theoryDate}</Text>
            <Text style={{ width: 50, fontSize: 9, textAlign: 'center', color: d.practical === 'Yes' ? COLOR.red : '#6B7280' }}>{d.practical}</Text>
          </View>
        ))}
      </View>

      <View style={{ padding: 8, borderLeftWidth: 3, borderLeftColor: COLOR.red }}>
        <Text style={{ fontSize: 8, fontWeight: 700, color: COLOR.red, marginBottom: 4 }}>INSTRUCTIONS · ਹਦਾਇਤਾਂ</Text>
        {data.instructions.map((ins, i) => (
          <View key={i} style={{ marginBottom: 3 }}>
            <Text style={{ fontSize: 8 }}>{i + 1}. {ins.en}</Text>
            <Text style={{ fontFamily: 'Noto Sans Gurmukhi', fontSize: 8, color: '#374151' }}>   {ins.pa}</Text>
          </View>
        ))}
      </View>

      <LetterheadFooter />
    </Page>
  </Document>
);

const KV: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <View style={{ flex: 1 }}>
    <Text style={{ fontSize: 7, color: '#6B7280' }}>{label.toUpperCase()}</Text>
    <Text style={{ fontWeight: 700, fontSize: 9 }}>{value}</Text>
  </View>
);
const Row: React.FC<{ label: string; en: string; pa: string }> = ({ label, en, pa }) => (
  <View style={{ flexDirection: 'row', marginBottom: 4 }}>
    <Text style={{ width: 60, fontSize: 7, color: '#6B7280' }}>{label.toUpperCase()}</Text>
    <View style={{ flex: 1 }}>
      <Text style={{ fontSize: 10 }}>{en}</Text>
      <Text style={{ fontFamily: 'Noto Sans Gurmukhi', fontSize: 9, color: '#374151' }}>{pa}</Text>
    </View>
  </View>
);
const Mini: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <View>
    <Text style={{ fontSize: 7, color: '#6B7280' }}>{label.toUpperCase()}</Text>
    <Text style={{ fontSize: 9, fontWeight: 600 }}>{value}</Text>
  </View>
);
