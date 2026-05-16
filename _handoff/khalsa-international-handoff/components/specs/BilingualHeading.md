# BilingualHeading

> **Kind:** Molecule
> Token-only styling. No raw hex / px / font-family literals.


Renders `{en, pa}` content with the correct font + line-height per script. Props `level` (`xl | lg | md | sm`), `primary` (`'en' | 'pa'`), `alignment`. Punjabi line is `color.text.secondary` when secondary; same as English when stacked equally.

Hard rule: must call `<span lang="pa">` (web) or set `fontFamily: theme.fontFamily.gurmukhi` (RN). The component handles this — never hand-write the lang attr in pages.

