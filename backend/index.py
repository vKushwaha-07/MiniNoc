"""
Vercel Serverless Function Entrypoint.
This file is the entry point for Vercel's Python runtime (@vercel/python).
It simply exposes the FastAPI application as 'app'.
"""

from main import app

# Vercel looks for this 'app' variable
# No changes needed - FastAPI is ASGI-compatible and Vercel handles it.
