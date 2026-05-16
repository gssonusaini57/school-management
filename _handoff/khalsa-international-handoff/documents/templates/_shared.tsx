import React from 'react';
import { Document, Page, View, Text, StyleSheet, Image, Font } from '@react-pdf/renderer';
import tokens from '../../design-tokens/tokens.json';

// Register fonts (paths are relative to project that consumes this package)
Font.register({ family: 'Playfair Display', src: 'fonts/PlayfairDisplay-Regular.ttf', fonts: [
  { src: 'fonts/PlayfairDisplay-Regular.ttf' },
  { src: 'fonts/PlayfairDisplay-Bold.ttf', fontWeight: 700 },
]});
Font.register({ family: 'Cinzel', src: 'fonts/Cinzel-Regular.ttf', fonts: [
  { src: 'fonts/Cinzel-Regular.ttf' },
  { src: 'fonts/Cinzel-Bold.ttf', fontWeight: 700 },
]});
Font.register({ family: 'Manrope', src: 'fonts/Manrope-Regular.ttf', fonts: [
  { src: 'fonts/Manrope-Regular.ttf' },
  { src: 'fonts/Manrope-Medium.ttf', fontWeight: 500 },
  { src: 'fonts/Manrope-SemiBold.ttf', fontWeight: 600 },
  { src: 'fonts/Manrope-Bold.ttf', fontWeight: 700 },
]});
Font.register({ family: 'Noto Sans Gurmukhi', src: 'fonts/NotoSansGurmukhi-Regular.ttf', fonts: [
  { src: 'fonts/NotoSansGurmukhi-Regular.ttf' },
  { src: 'fonts/NotoSansGurmukhi-Bold.ttf', fontWeight: 700 },
]});

export const COLOR = {
  blue: tokens.color.khalsaBlue.value,
  gold: tokens.color.royalGold.value,
  red: tokens.color.sangatRed.value,
  cream: tokens.color.vasantCream.value,
  indigo: tokens.color.deepIndigo.value,
  ink: tokens.color.ink.value,
  paper: '#FFFFFF',
  rule: '#E5E7EB',
};

export const formatINR = (n: number) => {
  const [int, dec] = n.toFixed(2).split('.');
  // Indian numbering grouping: 12,34,567
  const last3 = int.slice(-3);
  const rest = int.slice(0, -3);
  const grouped = rest ? rest.replace(/\\B(?=(\\d{2})+(?!\\d))/g, ',') + ',' + last3 : last3;
  return '₹ ' + grouped + '.' + dec;
};

export const formatDateLong = (iso: string) => {
  const d = new Date(iso);
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
};
export const formatDateShort = (iso: string) => {
  const d = new Date(iso);
  const dd = String(d.getDate()).padStart(2, '0');
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  return `${dd}-${mm}-${d.getFullYear()}`;
};

const sharedStyles = StyleSheet.create({
  page: { padding: 36, fontFamily: 'Manrope', fontSize: 10, color: COLOR.ink, backgroundColor: COLOR.paper },
  bilingualEn: { fontFamily: 'Manrope', fontSize: 10 },
  bilingualPa: { fontFamily: 'Noto Sans Gurmukhi', fontSize: 9, color: '#374151', marginTop: 1 },
  hr: { borderBottomWidth: 1, borderBottomColor: COLOR.rule, marginVertical: 8 },
  goldBar: { height: 3, backgroundColor: COLOR.gold },
  redBar: { height: 3, backgroundColor: COLOR.red },
});
export const s = sharedStyles;

export const BilingualText: React.FC<{ value: { en: string; pa: string } }> = ({ value }) => (
  <View>
    <Text style={s.bilingualEn}>{value.en}</Text>
    <Text style={s.bilingualPa}>{value.pa}</Text>
  </View>
);

// LetterheadHeader (Format A — classic centered)
export const LetterheadHeaderA: React.FC = () => (
  <View style={{ marginBottom: 18 }}>
    <View style={{ alignItems: 'center', paddingBottom: 12 }}>
      <Image src="brand/crest.png" style={{ width: 60, height: 60 }} />
      <Text style={{ fontFamily: 'Playfair Display', fontSize: 22, color: COLOR.blue, marginTop: 6 }}>Khalsa International</Text>
      <Text style={{ fontFamily: 'Cinzel', fontSize: 9, letterSpacing: 3, color: COLOR.ink, marginTop: 2 }}>SENIOR · SECONDARY · SCHOOL</Text>
      <Text style={{ fontFamily: 'Noto Sans Gurmukhi', fontSize: 10, color: COLOR.indigo, marginTop: 4 }}>ਖ਼ਾਲਸਾ ਇੰਟਰਨੈਸ਼ਨਲ ਸੀਨੀਅਰ ਸੈਕੰਡਰੀ ਸਕੂਲ</Text>
      <Text style={{ fontSize: 8, color: '#4B5563', marginTop: 4 }}>Jalalabad, District Patiala, Punjab — 147001  ·  PSEB Aff. No. 4906  ·  Est. 2005</Text>
    </View>
    <View style={s.goldBar} />
  </View>
);

// LetterheadHeader (Format B — modern asymmetric)
export const LetterheadHeaderB: React.FC = () => (
  <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 18, paddingBottom: 12, borderBottomWidth: 2, borderBottomColor: COLOR.blue }}>
    <Image src="brand/crest.png" style={{ width: 48, height: 48, marginRight: 14 }} />
    <View style={{ flex: 1 }}>
      <Text style={{ fontFamily: 'Playfair Display', fontSize: 18, color: COLOR.blue }}>Khalsa International</Text>
      <Text style={{ fontFamily: 'Cinzel', fontSize: 8, letterSpacing: 2.5, color: COLOR.ink, marginTop: 2 }}>SR · SEC · SCHOOL</Text>
      <Text style={{ fontFamily: 'Noto Sans Gurmukhi', fontSize: 9, color: COLOR.indigo, marginTop: 2 }}>ਖ਼ਾਲਸਾ ਇੰਟਰਨੈਸ਼ਨਲ ਸੀਨੀਅਰ ਸੈਕੰਡਰੀ ਸਕੂਲ</Text>
    </View>
    <View style={{ alignItems: 'flex-end' }}>
      <Text style={{ fontSize: 8, color: '#4B5563' }}>PSEB 4906</Text>
      <Text style={{ fontSize: 8, color: '#4B5563' }}>Est. 2005</Text>
    </View>
  </View>
);

export const LetterheadFooter: React.FC = () => (
  <View style={{ position: 'absolute', bottom: 24, left: 36, right: 36 }}>
    <View style={s.goldBar} />
    <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginTop: 6 }}>
      <Text style={{ fontFamily: 'Cinzel', fontSize: 8, letterSpacing: 2.5, color: COLOR.indigo }}>VIDYA · VICHAR · SEVA</Text>
      <Text style={{ fontSize: 8, color: '#4B5563' }}>+91 93563 31762  ·  info@khalsainternational.in  ·  www.khalsainternational.in</Text>
      <Text style={{ fontFamily: 'Cinzel', fontSize: 8, letterSpacing: 2.5, color: COLOR.indigo }}>EST. 2005</Text>
    </View>
  </View>
);

export const SignatureBlock: React.FC<{ name: string; role: string }> = ({ name, role }) => (
  <View style={{ marginTop: 36, alignItems: 'flex-start' }}>
    <View style={{ width: 140, borderBottomWidth: 1, borderBottomColor: COLOR.ink, marginBottom: 4 }} />
    <Text style={{ fontWeight: 700, fontSize: 10 }}>{name}</Text>
    <Text style={{ fontSize: 9, color: '#4B5563' }}>{role}</Text>
  </View>
);

export { Document, Page, View, Text, Image, StyleSheet };
