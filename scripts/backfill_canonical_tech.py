#!/usr/bin/env python3
"""Merge duplicate technology aliases onto canonical keys."""

import asyncio
import sys

from app.db import async_session
from app.scoring.canonical_backfill import backfill_canonical_technologies


async def main() -> int:
    async with async_session() as session:
        stats = await backfill_canonical_technologies(session)
        await session.commit()
    print("Canonical tech backfill complete:", stats)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
