# Component Library

26 specs total — atoms, molecules, organisms, print primitives.

## Index

### Atoms (12)
Button, IconButton, Input, Textarea, Select, Checkbox, Radio, Switch, Badge, Pill, Avatar, Tag

### Molecules (13)
Card, StatTile, NoticeCard, TimetableSlot, SubjectRow, FeeRow, TestimonialCard, ProgramCard, HouseTag, BilingualHeading, BilingualBody, CategoryBadge, StatusPill

### Organisms (12)
SiteHeader, SiteFooter, HeroBlock, StatsStrip, ProgramGrid, PrincipalLetter, GalleryStrip, VoicesGrid, NoticeBoard, AdmissionsCTA, MobileTabBar, MobileTopBar, WeekStrip

### Print primitives (6)
LetterheadHeader, LetterheadHeaderModern, LetterheadFooter, SealStamp, SignatureBlock, PdfTable

## Conventions

- Each spec is a single `.md` file in `specs/`.
- Anatomy diagrams are ASCII — they communicate intent, not pixel positions.
- Every styling reference is a **token reference**, never a raw value.
- Variants and props are exhaustive — implement all of them, not a subset.
- States: every component supports the relevant subset of `default / hover / focus-visible / active / disabled / loading / error / empty` from `interactions/states.md`.

## Storybook

Implement one story file per component. Required stories:
- Each variant
- Each size
- All interaction states (hover via `pseudo`, focus, disabled, loading)
- Long content (truncation behavior)
- Both `en` and `pa` content
