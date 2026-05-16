# Print Templates

Each template has three artifacts:

1. `schemas/<name>.schema.json` — JSON Schema for input data
2. `templates/<Name>.tsx` — React-PDF component
3. `samples/<name>-sample.pdf` — rendered PDF with mock data from the brand book

## Rendering

```ts
import { renderToFile } from '@react-pdf/renderer';
import { ReportCard } from './templates/ReportCard';
import data from './samples/report-card.json';

await renderToFile(<ReportCard data={data} />, 'samples/report-card-sample.pdf');
```

A render script at `render.ts` reads each schema's accompanying `samples/<name>.json` mock and writes the corresponding PDF.

## Validation

`pnpm validate:samples` validates every sample JSON against its schema using Ajv. CI fails on schema mismatch.

## Bilingual rule

Bilingual fields (`{en, pa}`) render English first; Punjabi appears beneath in `fontFamily.gurmukhi`. The `<BilingualText>` print primitive enforces this.

## Currency rule

All amounts pass through `formatINR()` (Indian numbering grouping, ₹ prefix, two decimals). No raw `toFixed(2)` allowed.
