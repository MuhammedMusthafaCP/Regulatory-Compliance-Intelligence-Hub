import os

# Settings need a URL at import time; the engine connects lazily, so tests never touch a database.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ["SEARCH_ENABLED"] = "false"   # the lifespan must never load real models in tests
