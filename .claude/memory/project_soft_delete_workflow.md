---
name: soft-delete-workflow
description: Two-tier soft-delete + super-admin approval workflow on Students and Staff. Status state machine + new super_admin role.
metadata: 
  node_type: memory
  type: project
  originSessionId: 54def71b-6fc2-4765-be47-339a6860ef84
---

Students and Staff use a 3-state lifecycle instead of hard delete:

- **active** — visible to everyone
- **pending_delete** — admin/staff requested deletion, still visible with yellow "Deletion requested" badge, awaiting super-admin approval
- **deleted** — super-admin approved, hidden from normal lists; can be Restored or Purged (hard-delete with FK cascade)

**Role tiers (3 instead of 2):**
- `staff` — request student deletion within their class scope only
- `admin` — request student or staff deletion
- `super_admin` (new, singleton like admin_auth) — archive directly, approve, restore, purge. Default `superadmin / super123` from env `SUPER_ADMIN_DEFAULT_PASSWORD`. `require_admin` accepts both admin + super_admin.

**Endpoints** at `/api/admin/deletion-requests`: GET (list), POST `{kind}/{id}/approve` (super-admin), POST `{kind}/{id}/restore` (admin OR super-admin), DELETE `{kind}/{id}` (super-admin AND status must be `deleted` — forces two-step). Frontend page at `/deletion-requests` (super-admin only).

**Why:** one-click hard-delete on the Trash icon was destroying student documents/attendance/marks/fees via FK CASCADE with no recovery path. Two-tier approval prevents accidental obliteration; super-admin restore brings the row back to `active` with all audit fields cleared.

**How to apply:** when adding any new "user/staff/student" record type, follow the same pattern — `status` ENUM column + 5 audit columns (`delete_requested_at/by`, `delete_reason`, `deleted_at/by`) + soft-delete handlers. Tables: see migration [0003_soft_delete_workflow](../backend/alembic/versions/0003_soft_delete_workflow.py). Shared enum: [backend/app/models/record_status.py](../backend/app/models/record_status.py). Related: [[school-management-deployed]].
