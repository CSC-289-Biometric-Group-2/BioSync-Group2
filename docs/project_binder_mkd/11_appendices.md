# Appendices

These appendices are optional. Include only what adds value.

---

## A. Wireframes or Mockups

<!-- TODO: Insert early design artifacts here, especially ones that show how the design evolved. -->

---

## B. Pitch Deck

**Presentation files are available in the repository root:**

- `Bio Sync_ A Biometric Wellness Ecosystem.pptx`
- `GROUP2_Pitch_Presentation_Due25FEB2026.pptx`

---

## C. API Documentation

BioSync exposes the following internal API endpoints (used by the frontend; not a public API):

| Endpoint | Method | Response | Description |
|----------|--------|----------|-------------|
| `/api/notifications/unread-count` | GET | `{ "count": N }` | Number of unread notifications for the current user |
| `/api/export/readings` | GET | CSV download | Single-metric reading export (query param: `metric=heart_rate`) |
| `/api/export/all-readings` | GET | CSV download | All readings for the past 30 days |
| `/api/trends/<metric_name>` | GET | JSON array | Trend data points for a given metric |

---

## D. Meeting Notes / Standup Logs

<!-- TODO: Insert selected standup logs or meeting notes that show team communication. -->

---

## E. CLAUDE.md

The project's AI assistant context file is located at `/workspaces/BioSync-Group2/BioSync/CLAUDE.md` (if present in the repository).

---

## F. Design Assets

<!-- TODO: Insert brand guide, color palette, or other design materials if available. -->
