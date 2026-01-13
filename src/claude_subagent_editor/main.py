"""FastAPI application for Claude Subagent Editor."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from claude_subagent_editor.api.routes import router

app = FastAPI(
    title="Claude Subagent Editor",
    description="Visual editor for Claude Code agent configurations",
    version="0.1.0",
)

# CORS configuration for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8765",
        "http://127.0.0.1:8765",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)

# Static file serving
static_dir = Path(__file__).parent / "static"


@app.get("/", response_class=HTMLResponse)
async def serve_spa():
    """Serve the React SPA."""
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return HTMLResponse(
        content="""
        <html>
        <head><title>Claude Subagent Editor</title></head>
        <body style="background:#0a0a0a;color:#fafafa;font-family:system-ui;display:flex;align-items:center;justify-content:center;height:100vh;margin:0">
            <div style="text-align:center">
                <h1>Claude Subagent Editor</h1>
                <p style="color:#71717a">Frontend not built. Run: cd frontend && npm run build</p>
            </div>
        </body>
        </html>
        """,
        status_code=200,
    )


# Mount static assets if directory exists
if static_dir.exists() and (static_dir / "assets").exists():
    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")
