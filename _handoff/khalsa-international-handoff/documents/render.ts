import { renderToFile } from '@react-pdf/renderer';
import React from 'react';
import { LetterheadFormatA } from './templates/LetterheadFormatA';
import { LetterheadFormatB } from './templates/LetterheadFormatB';
import { FeeReceipt } from './templates/FeeReceipt';
import { ReportCard } from './templates/ReportCard';
import { SalarySlip } from './templates/SalarySlip';
import { PsebAdmitCard } from './templates/PsebAdmitCard';
import lhA from './samples/letterhead-A.json';
import lhB from './samples/letterhead-B.json';
import fr from './samples/fee-receipt.json';
import rc from './samples/report-card.json';
import ss from './samples/salary-slip.json';
import ac from './samples/pseb-admit-card.json';

async function main() {
  await renderToFile(React.createElement(LetterheadFormatA, { data: lhA as any }), 'documents/samples/letterhead-A-sample.pdf');
  await renderToFile(React.createElement(LetterheadFormatB, { data: lhB as any }), 'documents/samples/letterhead-B-sample.pdf');
  await renderToFile(React.createElement(FeeReceipt,        { data: fr as any }), 'documents/samples/fee-receipt-sample.pdf');
  await renderToFile(React.createElement(ReportCard,        { data: rc as any }), 'documents/samples/report-card-sample.pdf');
  await renderToFile(React.createElement(SalarySlip,        { data: ss as any }), 'documents/samples/salary-slip-sample.pdf');
  await renderToFile(React.createElement(PsebAdmitCard,     { data: ac as any }), 'documents/samples/pseb-admit-card-sample.pdf');
  console.log('All sample PDFs rendered.');
}
main();
