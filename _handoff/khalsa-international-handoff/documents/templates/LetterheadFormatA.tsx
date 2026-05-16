import React from 'react';
import { Document, Page, View, Text, s, COLOR, formatDateLong, LetterheadHeaderA, LetterheadFooter, SignatureBlock, BilingualText } from './_shared';

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

export const LetterheadFormatA: React.FC<{ data: Data }> = ({ data }) => (
  <Document>
    <Page size="A4" style={s.page}>
      <LetterheadHeaderA />

      <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 16 }}>
        <Text>Ref: {data.ref}</Text>
        <Text>{formatDateLong(data.date)}</Text>
      </View>

      <View style={{ marginBottom: 14 }}>
        <Text style={{ fontWeight: 600 }}>{data.recipient.name}</Text>
        {data.recipient.lines.map((l, i) => <Text key={i} style={{ color: '#4B5563' }}>{l}</Text>)}
      </View>

      <View style={{ marginBottom: 14 }}>
        <Text style={{ fontWeight: 700, marginBottom: 2 }}>Subject:</Text>
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
