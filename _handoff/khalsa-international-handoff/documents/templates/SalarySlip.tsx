import React from 'react';
import { Document, Page, View, Text, s, COLOR, formatINR, LetterheadHeaderB, LetterheadFooter } from './_shared';

type Data = {
  month: string;
  employee: { id: string; name: string; designation: string; department: string; doj: string; pan?: string };
  workingDays?: number;
  leavesTaken?: number;
  earnings: Record<string, number>;
  deductions: Record<string, number>;
  netPay: number;
  bank?: { accountNo: string; ifsc: string; bankName: string };
};

const sum = (o: Record<string, number>) => Object.values(o).reduce((a, b) => a + (b || 0), 0);
const monthLabel = (ym: string) => {
  const [y, m] = ym.split('-').map(Number);
  return new Date(y, m - 1, 1).toLocaleDateString('en-IN', { month: 'long', year: 'numeric' });
};

export const SalarySlip: React.FC<{ data: Data }> = ({ data }) => {
  const grossEarnings = sum(data.earnings);
  const grossDeductions = sum(data.deductions);

  return (
    <Document>
      <Page size="A4" style={s.page}>
        <LetterheadHeaderB />

        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: 12 }}>
          <View>
            <Text style={{ fontFamily: 'Playfair Display', fontSize: 16, color: COLOR.blue }}>Salary Slip</Text>
            <Text style={{ fontFamily: 'Noto Sans Gurmukhi', fontSize: 10, color: COLOR.indigo }}>ਤਨਖ਼ਾਹ ਸਲਿੱਪ</Text>
          </View>
          <Text style={{ fontWeight: 700 }}>{monthLabel(data.month)}</Text>
        </View>

        <View style={{ flexDirection: 'row', backgroundColor: COLOR.cream, padding: 8, marginBottom: 12 }}>
          <KV label="Employee ID" value={data.employee.id} />
          <KV label="Name" value={data.employee.name} />
          <KV label="Designation" value={data.employee.designation} />
        </View>
        <View style={{ flexDirection: 'row', padding: 8, borderBottomWidth: 1, borderBottomColor: COLOR.rule, marginBottom: 12 }}>
          <KV label="Department" value={data.employee.department} />
          <KV label="DOJ" value={data.employee.doj} />
          {data.employee.pan && <KV label="PAN" value={data.employee.pan} />}
        </View>

        {(data.workingDays || data.leavesTaken !== undefined) && (
          <View style={{ flexDirection: 'row', marginBottom: 12, gap: 8 }}>
            {data.workingDays !== undefined && <Stat label="Working Days" value={String(data.workingDays)} />}
            {data.leavesTaken !== undefined && <Stat label="Leaves" value={String(data.leavesTaken)} />}
          </View>
        )}

        <View style={{ flexDirection: 'row', gap: 10 }}>
          <Side title="Earnings" rows={data.earnings} total={grossEarnings} />
          <Side title="Deductions" rows={data.deductions} total={grossDeductions} accent={COLOR.red} />
        </View>

        <View style={{ marginTop: 12, padding: 10, backgroundColor: COLOR.blue, flexDirection: 'row', justifyContent: 'space-between' }}>
          <Text style={{ color: 'white', fontWeight: 700, fontSize: 12 }}>Net Pay</Text>
          <Text style={{ color: COLOR.gold, fontWeight: 700, fontSize: 14 }}>{formatINR(data.netPay)}</Text>
        </View>

        {data.bank && (
          <View style={{ marginTop: 10, fontSize: 9 }}>
            <Text style={{ color: '#6B7280' }}>Credited to: {data.bank.bankName} — A/C {data.bank.accountNo}, IFSC {data.bank.ifsc}</Text>
          </View>
        )}

        <Text style={{ marginTop: 14, fontSize: 8, color: '#9CA3AF' }}>This is a system-generated salary slip and does not require a signature.</Text>

        <LetterheadFooter />
      </Page>
    </Document>
  );
};

const KV: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <View style={{ flex: 1 }}>
    <Text style={{ fontSize: 8, color: '#6B7280' }}>{label.toUpperCase()}</Text>
    <Text style={{ fontWeight: 600 }}>{value}</Text>
  </View>
);

const Stat: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <View style={{ flex: 1, padding: 6, borderWidth: 1, borderColor: COLOR.rule, alignItems: 'center' }}>
    <Text style={{ fontSize: 8, color: '#6B7280' }}>{label.toUpperCase()}</Text>
    <Text style={{ fontWeight: 700, marginTop: 2 }}>{value}</Text>
  </View>
);

const labels: Record<string, string> = { basic: 'Basic', hra: 'HRA', da: 'DA', conveyance: 'Conveyance', special: 'Special Allowance', pf: 'PF', esi: 'ESI', tds: 'TDS', advance: 'Advance' };
const Side: React.FC<{ title: string; rows: Record<string, number>; total: number; accent?: string }> = ({ title, rows, total, accent = COLOR.blue }) => (
  <View style={{ flex: 1, borderWidth: 1, borderColor: COLOR.rule }}>
    <View style={{ backgroundColor: accent, padding: 6 }}>
      <Text style={{ color: 'white', fontWeight: 700 }}>{title}</Text>
    </View>
    {Object.entries(rows).map(([k, v]) => (
      <View key={k} style={{ flexDirection: 'row', padding: 6, borderTopWidth: 1, borderTopColor: COLOR.rule }}>
        <Text style={{ flex: 1 }}>{labels[k] || k}</Text>
        <Text>{formatINR(v || 0)}</Text>
      </View>
    ))}
    <View style={{ flexDirection: 'row', padding: 6, backgroundColor: COLOR.cream, borderTopWidth: 1, borderTopColor: COLOR.rule }}>
      <Text style={{ flex: 1, fontWeight: 700 }}>Total</Text>
      <Text style={{ fontWeight: 700 }}>{formatINR(total)}</Text>
    </View>
  </View>
);
