# Icons

Use **Lucide React** (web) and **lucide-react-native** (mobile) at 24 px default, stroke 1.75. Color via `currentColor` so they inherit from token utilities.

Required icons used across the product:
`Bell`, `Calendar`, `Clock`, `Download`, `FileText`, `Filter`, `Globe`, `Home`, `MapPin`, `Menu`, `Phone`, `Search`, `User`, `Users`, `Wallet`, `X`, `ChevronRight`, `ChevronDown`, `Check`, `AlertCircle`.

Do not import the entire icon set; tree-shake by importing each icon individually:
```ts
import { Bell } from 'lucide-react';
```
