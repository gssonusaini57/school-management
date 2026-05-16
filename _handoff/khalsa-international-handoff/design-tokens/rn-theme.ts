/** Khalsa International — React Native theme
 *  Generated from design-tokens/tokens.json. Consume via a ThemeProvider.
 */
export const palette = {
  khalsaBlue:  '#0E2F8E',
  royalGold:   '#F5C518',
  sangatRed:   '#E11D2C',
  vasantCream: '#FFF6CC',
  deepIndigo:  '#08205C',
  ink:         '#1A1A1A',
  white:       '#FFFFFF',
} as const;

export const neutral = {
  50: '#F8F8F9', 100: '#EEEEF0', 200: '#D9D9DD', 300: '#BCBCC2',
  400: '#8E8E96', 500: '#6B6B72', 600: '#4F4F55', 700: '#3A3A3F',
  800: '#27272B', 900: '#1A1A1A', 950: '#0E0E10',
} as const;

export const semantic = {
  success: '#15803D',
  warning: '#B45309',
  error:   palette.sangatRed,
  info:    palette.khalsaBlue,
} as const;

export const surface = {
  page:        palette.white,
  raised:      neutral[50],
  sunken:      neutral[100],
  brand:       palette.khalsaBlue,
  brandSoft:   palette.vasantCream,
} as const;

export const text = {
  primary:   palette.ink,
  secondary: neutral[600],
  muted:     neutral[400],
  onBrand:   palette.white,
  onAccent:  palette.deepIndigo,
} as const;

export const fontFamily = {
  display:   'PlayfairDisplay-Bold',
  crestCaps: 'Cinzel-SemiBold',
  body:      'Manrope-Regular',
  bodyMedium:'Manrope-Medium',
  bodyBold:  'Manrope-Bold',
  gurmukhi:  'NotoSansGurmukhi-Regular',
  gurmukhiBold: 'NotoSansGurmukhi-Bold',
  mono:      'Menlo',
} as const;

export const typography = {
  display:    { fontFamily: fontFamily.display,    fontSize: 40, lineHeight: 44, letterSpacing: -0.6 },
  headingXl:  { fontFamily: fontFamily.display,    fontSize: 32, lineHeight: 36 },
  headingLg:  { fontFamily: fontFamily.display,    fontSize: 24, lineHeight: 28 },
  headingMd:  { fontFamily: fontFamily.bodyBold,   fontSize: 20, lineHeight: 26 },
  headingSm:  { fontFamily: fontFamily.bodyBold,   fontSize: 17, lineHeight: 22 },
  body:       { fontFamily: fontFamily.body,       fontSize: 15, lineHeight: 21 },
  bodySmall:  { fontFamily: fontFamily.body,       fontSize: 13, lineHeight: 18 },
  caption:    { fontFamily: fontFamily.bodyMedium, fontSize: 11, lineHeight: 14, letterSpacing: 0.2 },
  button:     { fontFamily: fontFamily.bodyBold,   fontSize: 15, lineHeight: 18 },
  // Punjabi variants — taller line-height
  bodyPa:     { fontFamily: fontFamily.gurmukhi,     fontSize: 15, lineHeight: 23 },
  headingPa:  { fontFamily: fontFamily.gurmukhiBold, fontSize: 22, lineHeight: 33 },
} as const;

export const spacing = {
  0: 0, 1: 4, 2: 8, 3: 12, 4: 16, 5: 20, 6: 24, 8: 32,
  10: 40, 12: 48, 16: 64, 20: 80, 24: 96, 32: 128,
} as const;

export const radius = { none: 0, sm: 4, md: 8, lg: 12, xl: 16, full: 9999 } as const;

export const motion = {
  duration: { fast: 120, base: 200, slow: 320 },
  // RN uses Easing module — these are the bezier coefficients
  easing: {
    standard:   [0.2, 0, 0, 1],
    decelerate: [0, 0, 0, 1],
    accelerate: [0.3, 0, 1, 1],
  },
} as const;

export const theme = {
  palette, neutral, semantic, surface, text,
  fontFamily, typography, spacing, radius, motion,
} as const;
export type Theme = typeof theme;
export default theme;
