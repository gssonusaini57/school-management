# Accessibility Checklist (WCAG 2.2 AA)

## Color & contrast
- [ ] All text meets 4.5:1 (normal) / 3:1 (large) — see `color-contrast-report.md`
- [ ] Focus indicators meet 3:1 against adjacent colors
- [ ] No information conveyed by color alone (status pills carry text labels)

## Keyboard
- [ ] Every interactive element reachable by Tab in logical order
- [ ] `:focus-visible` styling on every interactive
- [ ] Skip link to main content on every page
- [ ] Modals trap focus; Esc closes; focus returns to trigger
- [ ] Custom widgets (filter pills, language switcher) follow ARIA Authoring Practices

## Screen readers
- [ ] Every `<img>` has alt text in the active locale
- [ ] Decorative images use `alt=""`
- [ ] Form controls have associated `<label>`
- [ ] Error messages tied to inputs via `aria-describedby`
- [ ] Status messages use `role="status"` (toast) or `role="alert"` (errors)
- [ ] Live regions for fee-payment progress

## Punjabi-script considerations
- [ ] `<html lang="pa">` set when locale is `pa`
- [ ] Bilingual headings use `<span lang="pa">` around Gurmukhi
- [ ] Line-height bumped to 1.5 for Gurmukhi blocks
- [ ] No transliteration as substitute for the script
- [ ] Screen-reader pronunciations tested with VoiceOver (iOS) and TalkBack (Android) using a Punjabi voice; English fallback if unsupported

## Motion
- [ ] `prefers-reduced-motion` honored across web + mobile
- [ ] No auto-playing video with sound
- [ ] No flashing > 3 Hz

## Forms
- [ ] All required fields announced
- [ ] Inline validation announced via `aria-live="polite"`
- [ ] Submit button reflects loading via `aria-busy`

## Documents (PDF)
- [ ] Tagged PDFs (`@react-pdf/renderer` produces tagged output by default — verify)
- [ ] Reading order matches visual order
- [ ] Tables have header rows declared
