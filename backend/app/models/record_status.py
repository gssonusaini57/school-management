"""Soft-delete status enum shared by Student and Staff models.

Three states:
- `active`         — normal record; visible in all default listings.
- `pending_delete` — admin requested deletion; visible to everyone with a badge,
                     awaiting super-admin approval.
- `deleted`        — super-admin approved; hidden from normal listings, present
                     in the super-admin deletion-requests queue only.

Hard-delete (with FK CASCADE to documents/attendance/marks/fees/staff_classes)
happens only when super-admin explicitly purges from the queue.
"""
import enum


class RecordStatus(str, enum.Enum):
    active = "active"
    pending_delete = "pending_delete"
    deleted = "deleted"


def _status_values(obj):
    return [e.value for e in obj]
