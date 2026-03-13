import os

# ============================================================
# SERVER
# ============================================================
API_PORT = int(os.getenv("API_PORT", 8000))

# ============================================================
# OPENROUTER
# ============================================================
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "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")
OPENROUTER_URL     = os.getenv("OPENROUTER_URL",     "https://openrouter.ai/api/v1")
MODEL_ID           = os.getenv("MODEL_ID",           "google/gemini-2.0-flash-001")

# ============================================================
# NEO4J (hozircha ishlatilmayapti)
# ============================================================
NEO4J_URI      = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
NEO4J_USER     = os.getenv("NEO4J_USER",     "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")