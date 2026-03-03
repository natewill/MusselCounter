-- RUN: each inference run.
CREATE TABLE IF NOT EXISTS run (
  run_id        INTEGER PRIMARY KEY AUTOINCREMENT,
  model_id      INTEGER NOT NULL,
  model_name    TEXT NOT NULL,
  model_type    TEXT NOT NULL CHECK(model_type IN ('FASTRCNN', 'YOLO')),
  weights_path  TEXT NOT NULL,
  threshold     REAL NOT NULL CHECK(threshold >= 0.0 AND threshold <= 1.0),
  created_at    TEXT NOT NULL,
  total_images  INTEGER NOT NULL DEFAULT 0,
  processed_count INTEGER NOT NULL DEFAULT 0,
  live_mussel_count INTEGER NOT NULL DEFAULT 0,
  error_msg     TEXT
);

-- RUN_IMAGE: images uploaded for a run.
CREATE TABLE IF NOT EXISTS run_image (
  run_image_id   INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id         INTEGER NOT NULL,
  stored_path    TEXT NOT NULL,
  live_mussel_count INTEGER NOT NULL DEFAULT 0,
  dead_mussel_count INTEGER NOT NULL DEFAULT 0,
  processed_at   TEXT,
  error_msg      TEXT,
  FOREIGN KEY (run_id) REFERENCES run(run_id)
);

-- DETECTION: stores individual detections for threshold recalculation + manual edits.
CREATE TABLE IF NOT EXISTS detection (
  detection_id    INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id          INTEGER NOT NULL,
  run_image_id    INTEGER NOT NULL,
  confidence      REAL NOT NULL,
  class           TEXT NOT NULL CHECK(class IN ('live', 'dead')),
  bbox_x1         REAL NOT NULL,
  bbox_y1         REAL NOT NULL,
  bbox_x2         REAL NOT NULL,
  bbox_y2         REAL NOT NULL,
  manually_edited INTEGER NOT NULL DEFAULT 0 CHECK(manually_edited IN (0, 1)),
  FOREIGN KEY (run_id) REFERENCES run(run_id) ON DELETE CASCADE,
  FOREIGN KEY (run_image_id) REFERENCES run_image(run_image_id) ON DELETE CASCADE
);
