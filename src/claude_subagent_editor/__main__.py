"""CLI entry point for Claude Subagent Editor."""

import argparse
import uvicorn


def main() -> None:
    """Start the Claude Subagent Editor server."""
    parser = argparse.ArgumentParser(
        description="Claude Subagent Editor - Visual editor for agent configurations"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port to bind to (default: 8765)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )
    args = parser.parse_args()

    print(f"Starting Claude Subagent Editor at http://{args.host}:{args.port}")
    uvicorn.run(
        "claude_subagent_editor.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
