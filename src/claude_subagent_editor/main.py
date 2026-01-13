"""FastAPI application for Claude Subagent Editor."""

from fastapi import FastAPI

app = FastAPI(
    title="Claude Subagent Editor",
    description="Visual editor for Claude Code agent configurations",
    version="0.1.0",
)


@app.get("/api/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}
