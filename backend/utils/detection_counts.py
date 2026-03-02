"""
Shared detection counting queries used by threshold recalculation paths.
"""

import aiosqlite


async def get_counts_for_image(
    db: aiosqlite.Connection,
    run_id: int,
    image_id: int,
    threshold: float,
) -> tuple[int, int]:
    """
    Return (live_count, dead_count) for one image in a run at a threshold.
    """
    cursor = await db.execute(
        """SELECT
               SUM(CASE
                   WHEN class = 'edit_live' THEN 1
                   WHEN class = 'live' AND confidence >= ? THEN 1
                   ELSE 0
               END) AS live_count,
               SUM(CASE
                   WHEN class = 'edit_dead' THEN 1
                   WHEN class = 'dead' AND confidence >= ? THEN 1
                   ELSE 0
               END) AS dead_count
           FROM detection
           WHERE run_id = ? AND image_id = ?""",
        (threshold, threshold, run_id, image_id),
    )
    row = await cursor.fetchone()
    if not row:
        return (0, 0)
    return (row[0] or 0, row[1] or 0)


async def get_counts_by_image_for_run(
    db: aiosqlite.Connection,
    run_id: int,
    threshold: float,
) -> list[tuple[int, int, int]]:
    """
    Return per-image counts as (image_id, live_count, dead_count) for a run.
    """
    cursor = await db.execute(
        """SELECT
               image_id,
               SUM(CASE
                   WHEN class = 'edit_live' THEN 1
                   WHEN class = 'live' AND confidence >= ? THEN 1
                   ELSE 0
               END) AS live_count,
               SUM(CASE
                   WHEN class = 'edit_dead' THEN 1
                   WHEN class = 'dead' AND confidence >= ? THEN 1
                   ELSE 0
               END) AS dead_count
           FROM detection
           WHERE run_id = ?
           GROUP BY image_id""",
        (threshold, threshold, run_id),
    )
    rows = await cursor.fetchall()
    return [(row[0], row[1] or 0, row[2] or 0) for row in rows]
