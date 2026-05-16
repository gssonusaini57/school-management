# Notices (`/notices`)


Filterable list. Filter pills: All, Exam, Fees, Admission, Event, Result, Sports. Default: All.

12 `NoticeCard`s per page; pagination prev/next.

Single notice route `/notices/[slug]` renders title, date, category badge, full body in both languages, optional attachment download (PDF).

Empty state when filter returns 0 results: bilingual "No notices in this category yet" + reset button.

