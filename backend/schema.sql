-- COLLECTION: one per analysis group
CREATE TABLE IF NOT EXISTS collection (
  collection_id      INTEGER PRIMARY KEY AUTOINCREMENT,
  name          TEXT,
  created_at    TEXT NOT NULL              -- SQLite uses TEXT for dates (ISO format)
);

-- IMAGE: unique images (global, not tied to a specific batch)
CREATE TABLE IF NOT EXISTS image (
  image_id    INTEGER PRIMARY KEY AUTOINCREMENT,        
  filename    TEXT NOT NULL,             -- original filename
  stored_path TEXT NOT NULL,             -- where the file is stored
  file_hash   TEXT UNIQUE                -- MD5 hash for deduplication (UNIQUE ensures no duplicates)
);

-- COLLECTION_IMAGE: junction table linking collections to images (many-to-many)
CREATE TABLE IF NOT EXISTS collection_image (
  collection_id      INTEGER NOT NULL,
  image_id      INTEGER NOT NULL,
  added_at      TEXT NOT NULL,            -- When this image was added to this collection
  PRIMARY KEY (collection_id, image_id),
  FOREIGN KEY (collection_id) REFERENCES collection(collection_id),
  FOREIGN KEY (image_id) REFERENCES image(image_id)
);

-- MODEL: one per trained model file, incase we want to use different models in the future
CREATE TABLE IF NOT EXISTS model (
  model_id      INTEGER PRIMARY KEY AUTOINCREMENT, 
  name          TEXT NOT NULL,             -- "CNN v2 - 2025-11 blah blah"
  type          TEXT NOT NULL CHECK(type IN ('FASTRCNN', 'YOLO')),  -- canonical model type
  weights_path  TEXT NOT NULL             -- local path to .pt or .pth file
);

-- RUN: each inference run on a collection (can use different models)
CREATE TABLE IF NOT EXISTS run (
  run_id        INTEGER PRIMARY KEY AUTOINCREMENT,
  collection_id      INTEGER NOT NULL,
  model_id      INTEGER NOT NULL,         -- Model used for this run
  started_at    TEXT NOT NULL,            -- SQLite uses TEXT for dates (ISO format)
  finished_at   TEXT,                     -- NULL if still running, set when done
  status        TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'running', 'completed', 'failed', 'cancelled', 'completed_with_errors')),
  error_msg     TEXT,                      -- error if failed
  threshold     REAL NOT NULL CHECK(threshold >= 0.0 AND threshold <= 1.0),   -- threshold score used for this run
  total_images  INTEGER DEFAULT 0,        -- number of images to process
  processed_count INTEGER DEFAULT 0,      -- number of images processed so far (for progress tracking)
  live_mussel_count INTEGER DEFAULT 0,    -- total live mussels detected in this run
  FOREIGN KEY (collection_id) REFERENCES collection(collection_id),
  FOREIGN KEY (model_id) REFERENCES model(model_id)
);

-- IMAGE_RESULT: stores inference results for each image in each run
-- This allows us to track run-specific results and skip already-processed images
CREATE TABLE IF NOT EXISTS image_result (
  run_id      INTEGER NOT NULL,
  image_id    INTEGER NOT NULL,
  live_mussel_count INTEGER DEFAULT 0,
  dead_mussel_count INTEGER DEFAULT 0,
  processed_at TEXT NOT NULL,             -- when this image was processed
  error_msg   TEXT,                        -- error if processing failed
  PRIMARY KEY (run_id, image_id),         -- One result per image per run (allows INSERT OR REPLACE)
  FOREIGN KEY (run_id) REFERENCES run(run_id),
  FOREIGN KEY (image_id) REFERENCES image(image_id)
);

-- DETECTION: stores individual mussel detections with confidence scores
-- Enables threshold recalculation without re-running model
CREATE TABLE IF NOT EXISTS detection (
  detection_id    INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id          INTEGER NOT NULL,
  image_id        INTEGER NOT NULL,
  confidence      REAL NOT NULL,                     -- Model confidence score (0.0 - 1.0)
  class           TEXT NOT NULL CHECK(class IN ('live', 'dead', 'edit_live', 'edit_dead')),
  bbox            TEXT NOT NULL,                     -- JSON array: [x1, y1, x2, y2]
  FOREIGN KEY (run_id) REFERENCES run(run_id) ON DELETE CASCADE,
  FOREIGN KEY (image_id) REFERENCES image(image_id) ON DELETE CASCADE
);
