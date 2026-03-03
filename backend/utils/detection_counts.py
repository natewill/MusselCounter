"""
Shared detection counting queries.
"""

import aiosqlite


async def get_counts_for_run_image(
    db: aiosqlite.Connection,
    run_id: int,
    run_image_id: int,
    threshold: float,
) -> tuple[int, int]:
    """
    Return (live_count, dead_count) for one run_image at the given threshold.

    Manual edits always count regardless of confidence.
    """
    cursor = await db.execute(
        """
        SELECT
            SUM(CASE
                WHEN class = 'live' AND (manually_edited = 1 OR confidence >= ?) THEN 1
                ELSE 0
            END) AS live_count,
            SUM(CASE
                WHEN class = 'dead' AND (manually_edited = 1 OR confidence >= ?) THEN 1
                ELSE 0
            END) AS dead_count
        FROM detection
        WHERE run_id = ? AND run_image_id = ?
        """,
        (threshold, threshold, run_id, run_image_id),
    )
    row = await cursor.fetchone()
    if not row:
        return (0, 0)
    return (row[0] or 0, row[1] or 0)


async def get_counts_by_run_image_for_run(
    db: aiosqlite.Connection,
    run_id: int,
    threshold: float,
) -> list[tuple[int, int, int]]:
    """
    Return rows as (run_image_id, live_count, dead_count) for a run.
    """
    cursor = await db.execute(
        """
        SELECT
            run_image_id,
            SUM(CASE
                WHEN class = 'live' AND (manually_edited = 1 OR confidence >= ?) THEN 1
                ELSE 0
            END) AS live_count,
            SUM(CASE
                WHEN class = 'dead' AND (manually_edited = 1 OR confidence >= ?) THEN 1
                ELSE 0
            END) AS dead_count
        FROM detection
        WHERE run_id = ?
        GROUP BY run_image_id
        """,
        (threshold, threshold, run_id),
    )
    rows = await cursor.fetchall()
    return [(row[0], row[1] or 0, row[2] or 0) for row in rows]
