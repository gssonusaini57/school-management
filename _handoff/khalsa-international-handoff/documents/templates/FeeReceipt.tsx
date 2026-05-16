import React from 'react';
import { Document, Page, View, Text, s, COLOR, formatDateLong, formatINR, LetterheadHeaderA, LetterheadFooter, SignatureBlock, BilingualText } from './_shared';

type Data = {
  receiptNo: string;
  date: string;
  student: { name: { en: string; pa: string }; class: string; section: string; rollNo: string; fatherName: { en: string; pa: string } };
  items: { particulars: { en: string; pa: string }; amount: number }[];
  total: number;
  amountInWords: string;
  modeOfPayment: string;
  txnRef?: string;
  signatory?: { name: string; role: string };
};

export const FeeReceipt: React.FC<{ data: Data }> = ({ data }) => (
  <Document>
    <Page size="A4" style={s.page}>
      <LetterheadHeaderA />

      <View style={{ alignItems: 'center', marginBottom: 14 }}>
        <Text style={{ fontFamily: 'Playfair Display', fontSize: 18, color: COLOR.blue }}>Fee Receipt</Text>
        <Text style={{ fontFamily: 'Noto Sans Gurmukhi', fontSize: 11, color: COLOR.indigo }}>ਫ਼ੀਸ ਰਸੀਦ</Text>
      </View>

      <View style={{ flexDirection: 'row', justifyContent: 'space-between', backgroundColor: COLOR.cream, padding: 8, marginBottom: 12 }}>
        <Text>Receipt No: <Text style={{ fontWeight: 700 }}>{data.receiptNo}</Text></Text>
        <Text>Date: <Text style={{ fontWeight: 700 }}>{formatDateLong(data.date)}</Text></Text>
      </View>

      <View style={{ flexDirection: 'row', marginBottom: 12 }}>
        <View style={{ flex: 1 }}>
          <Text style={{ color: '#6B7280', fontSize: 8 }}>STUDENT NAME</Text>
          <BilingualText value={data.student.name} />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={{ color: '#6B7280', fontSize: 8 }}>FATHER'S NAME</Text>
          <BilingualText value={data.student.fatherName} />
        </View>
        <View style={{ width: 90 }}>
          <Text style={{ color: '#6B7280', fontSize: 8 }}>CLASS / ROLL</Text>
          <Text>{data.student.class}-{data.student.section}  ·  Roll {data.student.rollNo}</Text>
        </View>
      </View>

      <View style={{ borderWidth: 1, borderColor: COLOR.rule, borderRadius: 4 }}>
        <View style={{ flexDirection: 'row', backgroundColor: COLOR.blue, padding: 6 }}>
          <Text style={{ flex: 1, color: 'white', fontWeight: 700 }}>Particulars</Text>
          <Text style={{ width: 90, color: 'white', fontWeight: 700, textAlign: 'right' }}>Amount</Text>
        </View>
        {data.items.map((it, i) => (
          <View key={i} style={{ flexDirection: 'row', padding: 6, borderTopWidth: i === 0 ? 0 : 1, borderTopColor: COLOR.rule }}>
            <View style={{ flex: 1 }}><BilingualText value={it.particulars} /></View>
            <Text style={{ width: 90, textAlign: 'right' }}>{formatINR(it.amount)}</Text>
          </View>
        ))}
        <View style={{ flexDirection: 'row', padding: 8, backgroundColor: COLOR.cream, borderTopWidth: 1, borderTopColor: COLOR.rule }}>
          <Text style={{ flex: 1, fontWeight: 700 }}>Total</Text>
          <Text style={{ width: 90, textAlign: 'right', fontWeight: 700, color: COLOR.blue }}>{formatINR(data.total)}</Text>
        </View>
      </View>

      <View style={{ marginTop: 10 }}>
        <Text style={{ fontStyle: 'italic', fontSize: 9 }}>Amount in words: {data.amountInWords}</Text>
      </View>

      <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginTop: 10 }}>
        <Text>Mode: {data.modeOfPayment}</Text>
        {data.txnRef ? <Text>Txn Ref: {data.txnRef}</Text> : null}
      </View>

      {data.signatory && <SignatureBlock name={data.signatory.name} role={data.signatory.role} />}

      <LetterheadFooter />
    </Page>
  </Document>
);
