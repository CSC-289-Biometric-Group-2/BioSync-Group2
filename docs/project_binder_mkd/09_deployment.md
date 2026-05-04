# Deployment

## Current Status

BioSync has not yet been deployed to a production hosting platform. The application runs in a local development environment. This section documents the current development setup and outlines what would be needed for a production deployment.

---

## Development Setup

### Hosting

Not yet deployed. The application runs locally via the Flask development server (`flask run`), binding to `http://127.0.0.1:5000`.

### Database

SQLite file stored at `instance/flaskr.sqlite`. The database is initialized by running:

```bash
flask init-db
```

This command reads `schema.sql` and creates all tables. There is no migration framework (e.g., Alembic), so schema changes require manual intervention.

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `FLASK_APP` | Yes | Must be set to `__init__` for Flask to locate the app factory |
| `SECRET_KEY` | Yes (production) | Session signing key. Currently hardcoded as `'dev'` — **must be changed before any public deployment** |

## Production Deployment (Not Yet Completed)

To deploy BioSync on a platform such as Render or Railway, the following changes and steps would be required:

1. **Replace the `SECRET_KEY`** — Set a strong, randomly generated secret key via an environment variable rather than the hardcoded `'dev'` value.

2. **Switch the database** — SQLite is not suitable for multi-process production deployments. Migrating to PostgreSQL would require updating the `db.py` connection logic and translating `schema.sql` to PostgreSQL-compatible syntax.

3. **Add a `Procfile` or equivalent** — A deployment platform needs a process declaration, for example:
   ```
   web: gunicorn "__init__:create_app()"
   ```

4. **Configure file upload storage** — Currently uploaded documents are stored on the local filesystem at `instance/uploads/`. In a cloud deployment, this path would not persist across restarts. Files would need to be stored in an object storage service (e.g., AWS S3, Cloudflare R2).

5. **Set environment variables on the platform** — At minimum: `SECRET_KEY`, `FLASK_APP`, and any database connection string.

### Known Gotchas

- The `instance/` folder is not committed to the repository. It is created at runtime. If the folder does not exist when a user uploads a document, the upload will fail with a file-not-found error.
- `flask init-db` must be run once before the application can serve any requests, or all database queries will fail.
- The `requirements.txt` in the repository only includes core Flask dependencies. `pdfplumber`, `python-docx`, `numpy`, and `pandas` must be installed separately (see SETUP.md).
