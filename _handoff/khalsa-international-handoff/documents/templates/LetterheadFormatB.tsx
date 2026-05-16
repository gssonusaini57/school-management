import React from 'react';
import { Document, Page, View, Text, s, COLOR, formatDateLong, LetterheadHeaderB, LetterheadFooter, SignatureBlock, BilingualText } from './_shared';

type Data = {
  format: 'A' | 'B';
  ref: string;
  date: string;
  recipient: { name: string; lines: string[] };
  subject: { en: string; pa: string };
  salutation: string;
  body: string[];
  closing: string;
  signatory: { name: string; role: string };
};

export const LetterheadFormatB: React.FC<{ data: Data }> = ({ data }) => (
  <Document>
    <Page size="A4" style={s.page}>
      <LetterheadHeaderB />

      <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 14 }}>
        <Text style={{ color: '#6B7280', fontSize: 9 }}>Ref: {data.ref}</Text>
        <Text style={{ color: '#6B7280', fontSize: 9 }}>{formatDateLong(data.date)}</Text>
      </View>

      <Text style={{ fontWeight: 600, marginBottom: 10 }}>{data.recipient.name}</Text>

      <View style={{ marginBottom: 14, paddingLeft: 10, borderLeftWidth: 3, borderLeftColor: COLOR.gold }}>
        <BilingualText value={data.subject} />
      </View>

      <Text style={{ marginBottom: 10 }}>{data.salutation}</Text>

      {data.body.map((p, i) => (
        <Text key={i} style={{ marginBottom: 10, lineHeight: 1.5, textAlign: 'justify' }}>{p}</Text>
      ))}

      <Text style={{ marginTop: 18 }}>{data.closing}</Text>

      <SignatureBlock name={data.signatory.name} role={data.signatory.role} />

      <LetterheadFooter />
    </Page>
  </Document>
);
