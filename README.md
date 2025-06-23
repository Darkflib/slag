# SLAG Commenting System (ULID-based, Flat-File Storage)

SLAG is a lightweight commenting system that stores each comment as a standalone JSON-LD file, indexed by [ULID](https://github.com/ulid/spec)-based filenames for natural sortability. It is designed to run without a database — ideal for edge devices, offline use, or simple deployments.

## 🔧 Overview

- Comments are saved to disk using their ULID as the filename (e.g. `slag-data/comments/01HX...jsonld`).
- Page-level indexes map target pages (e.g. articles) to lists of ULIDs.
- Comments use [ActivityStreams 2.0](https://www.w3.org/TR/activitystreams-core/) `Note` format for future interoperability.
- Moderation metadata (e.g. hidden/reported) is stored in separate `.flags.json` files.
- Robust error handling for file operations with appropriate HTTP responses.

## 📂 File Structure

```text
slag-data/
├── comments/               # Individual comments as JSON-LD files
│   └── 01HX...jsonld
├── targets/                # Page-specific index files
│   └── example-article.index.json
├── flags/                  # Moderation overlays per comment
│   └── 01HX...flags.json
└── snapshot.json           # Combined export of all index and flag data
```

## 📘 JSON Schema Summary

Each comment follows the AS2 `Note` format:

```json
{
  "@context": "https://www.w3.org/ns/activitystreams",
  "type": "Note",
  "id": "https://slag.example.com/comments/01HX...",
  "content": "This is great!",
  "published": "2025-06-22T18:00:00Z",
  "attributedTo": {
    "id": "https://slag.example.com/users/alice",
    "type": "Person",
    "name": "Alice"
  },
  "target": "https://example.com/article",
  "inReplyTo": "https://slag.example.com/comments/01HX..." (optional)
}
```

---

## 🧪 API Endpoints (FastAPI)

### Comments

| Method | Path                                  | Description                            |
|--------|---------------------------------------|----------------------------------------|
| `GET`  | `/comments/{target_id}`               | List all comment IDs for a page        |
| `POST` | `/comments/{target_id}`               | Submit a top-level comment             |
| `GET`  | `/comment/{ulid}`                     | Get a full comment by ULID             |
| `PATCH`| `/comment/{ulid}`                     | Edit comment content                   |
| `POST` | `/comment/{ulid}/reply`               | Reply to an existing comment           |

### Moderation

| Method | Path                                  | Description                            |
|--------|---------------------------------------|----------------------------------------|
| `GET`  | `/comment/{ulid}/flags`               | Fetch moderation flags                 |
| `PATCH`| `/comment/{ulid}/flags`               | Update moderation flags                |

### Admin

| Method | Path                                  | Description                            |
|--------|---------------------------------------|----------------------------------------|
| `POST` | `/admin/rebuild-index`                | Rebuild indexes from stored comments   |
| `POST` | `/admin/snapshot`                     | Export all index/flag state to snapshot|

### Error Handling

All endpoints that perform file operations include robust error handling:

- `404 Not Found`: When a requested comment, flag, or resource doesn't exist
- `500 Internal Server Error`: For file I/O errors or JSON parsing issues, with descriptive error messages

---

## ⚙️ Configuration

Configuration is handled via environment variables or a `.env` file:

```bash
# Base URL for comments (no trailing slash)
COMMENTS_BASE_URL=https://slag.example.com/comments
# Base URL for target resources (no trailing slash)
TARGET_BASE_URL=https://example.com
```

An example configuration file is provided as `.env.example`.

---

## 🚀 Running the App

```bash
# Setup environment (Python 3.11+ recommended)
uv venv
. .venv/bin/activate
uv pip install -e .

# Start the dev server
uvicorn main:app --reload

# Visit: http://127.0.0.1:8000/docs
```

---

## ✅ Benefits

- No database — works on Pi Zero or offline setups
- Deterministic snapshot (`snapshot.json`) for easy backup or rsync
- ActivityStreams-compatible for future federation
- Simple JSON files = easy to read, test, and debug

---

## 🧠 Future Directions

- Signature support (Linked Data Proofs)
- Rate limiting at proxy level
- Background task to compress or rotate snapshots

---

## 🦝 Philosophy
>
> *Sometimes you just want to slag someone off.*

SLAG is fast, flat, and slightly feral — like a raccoon on a Raspberry Pi.

---

MIT Licensed. Contributions welcome.
