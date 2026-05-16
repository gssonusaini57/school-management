# Gotchas Archive — Items 7–12 (Frontend conventions, non-surprising)

These are stable frontend conventions that are no longer surprising once
working in the codebase. Kept here for completeness; the active CLAUDE.md
keeps a more recent set inline.

---

7. **TanStack Query staleTime = 30s.** Tweak in [frontend/src/main.tsx](../frontend/src/main.tsx) if data feels stale. SSE invalidation forces an immediate refetch when something actually changes.

8. **shadcn components are in-repo.** Don't `npm install` shadcn. The components under [frontend/src/components/ui/](../frontend/src/components/ui/) are owned source you can edit. Pattern: copy from https://ui.shadcn.com/docs/components/<name> and tweak.

9. **`compressImage()` runs on the client.** PDFs pass through unchanged. Only image files become 900px max JPEG q=0.75. Backend doesn't re-compress.

10. **`LONGBLOB` for documents.** MySQL row size cap doesn't apply to BLOB content (LONGBLOB stores up to 4 GB out-of-row). Schema has byte_size + mime_type for sanity. ~25 MB nginx upload cap is set in [deploy/nginx.school.conf](../deploy/nginx.school.conf).

11. **`Object.assign(window, {...})` traps from old code:** N/A in React. The pattern that crashed the Firebase build (referencing names not defined as `function`) is gone — TS catches this at compile time now.

12. **No-cache headers** are no longer manually injected. Vite emits content-hashed asset filenames so they cache forever via the natural URL change. Only `index.html` needs no-cache and that's handled by `try_files` falling back to it (browsers don't aggressively cache HTML by default).
