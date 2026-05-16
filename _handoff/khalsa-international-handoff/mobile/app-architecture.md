# Mobile App Architecture

## Stack
- React Native + Expo SDK 51, TypeScript
- expo-router (file-based routing)
- react-i18next (i18n)
- @tanstack/react-query (server state)
- expo-secure-store (auth tokens)
- expo-notifications (push)

## Navigation
- Stack root: Welcome (unauth) → Tabs (auth)
- Tabs: Home / Timetable / Notices / Fees / Profile
- Modals: Notice detail, Fee receipt PDF preview, Sign-out confirm

## Auth
- Phone OTP. Token stored in SecureStore. Auto-refresh on 401.

## API surface (REST)
- POST `/auth/otp/request` { phone } → { sessionId }
- POST `/auth/otp/verify` { sessionId, code } → { token, user }
- GET  `/me` → user + linked students
- GET  `/students/:id/timetable?date=` → TimetableSlot[]
- GET  `/notices?category=&page=` → { items, nextPage }
- GET  `/students/:id/fees` → { outstanding, dueDate, history: Receipt[] }
- POST `/fees/pay` → Razorpay order
- GET  `/receipts/:id` (PDF) → application/pdf

## State
- Auth context wraps app.
- React Query for all server state. Default `staleTime` 60s, `refetchOnWindowFocus: false`.
- Offline cache: `@tanstack/query-async-storage-persister`.

## Offline
- Cached responses shown with banner "ਤੁਸੀਂ ਆਫ਼ਲਾਈਨ ਹੋ" (`mobile.errors.offline`).
- Fee payment disabled offline.

## Push
- Topics: `notices`, `fees-due`, `exam-schedule`. Subscribed by student class.

## Locale
- Default `pa`. Switchable in Profile. Persisted to SecureStore.
