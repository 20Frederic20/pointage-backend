"""Workspace routes. ``GET/PATCH /directories/me`` joins this router together
with the auth context's guards in a later slice."""

from fastapi import APIRouter

router = APIRouter(prefix="/directories", tags=["directories"])