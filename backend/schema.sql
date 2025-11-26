-- COLLECTION: one per analysis group
CREATE TABLE IF NOT EXISTS collection (
  collection_id      INTEGER PRIMARY KEY AUTOINCREMENT,
  name          TEXT,
  description   TEXT,
  folder_path   TEXT,                      -- where the folder containing the images is stored
  created_at    TEXT NOT NULL,             -- SQLite uses TEXT for dates (ISO format)
  updated_at    TEXT NOT NULL,
  image_count   INTEGER DEFAULT 0,         -- Calculated field, not a foreign key
  live_mussel_count INTEGER DEFAULT 0    -- From latest run
);

-- IMAGE: unique images (global, not tied to a specific batch)
CREATE TABLE IF NOT EXISTS image (
  image_id    INTEGER PRIMARY KEY AUTOINCREMENT,        
  filename    TEXT NOT NULL,             -- original filename
  stored_path TEXT NOT NULL,             -- where the file is stored
  file_hash   TEXT UNIQUE,               -- MD5 hash for deduplication (UNIQUE ensures no duplicates)
  width       INTEGER,
  height      INTEGER,
  created_at  TEXT NOT NULL,             -- SQLite uses TEXT for dates (ISO format)
  updated_at  TEXT NOT NULL
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

-- Index for faster hash lookups
CREATE INDEX IF NOT EXISTS idx_image_hash ON image(file_hash);

-- MODEL: one per trained model file, incase we want to use different models in the future
CREATE TABLE IF NOT EXISTS model (
  model_id      INTEGER PRIMARY KEY AUTOINCREMENT, 
  name          TEXT NOT NULL,             -- "CNN v2 - 2025-11 blah blah"
  type          TEXT NOT NULL,             -- CNN, YOLO, etc.
  weights_path  TEXT NOT NULL,             -- local path to .pt or .pth file
  description   TEXT,
  optimal_batch_size INTEGER DEFAULT 8,    -- detected optimal batch size for inference
  created_at    TEXT NOT NULL,            -- SQLite uses TEXT for dates (ISO format)
  updated_at    TEXT NOT NULL
);

-- RUN: each inference run on a collection (can use different models)
CREATE TABLE IF NOT EXISTS run (
  run_id        INTEGER PRIMARY KEY AUTOINCREMENT,
  collection_id      INTEGER NOT NULL,
  model_id      INTEGER NOT NULL,         -- Model used for this run
  started_at    TEXT NOT NULL,            -- SQLite uses TEXT for dates (ISO format)
  finished_at   TEXT,                     -- NULL if still running, set when done
  status        TEXT DEFAULT 'pending',   -- 'pending', 'running', 'completed', 'failed'
  error_msg     TEXT,                      -- error if failed
  threshold     REAL NOT NULL,   -- threshold score used for this run
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
  polygon_path TEXT,                      -- path to JSON file with bounding boxes/polygons
  processed_at TEXT NOT NULL,             -- when this image was processed
  error_msg   TEXT,                        -- error if processing failed
  PRIMARY KEY (run_id, image_id),         -- One result per image per run (allows INSERT OR REPLACE)
  FOREIGN KEY (run_id) REFERENCES run(run_id),
  FOREIGN KEY (image_id) REFERENCES image(image_id)
);

-- Index for faster lookups of results by run
CREATE INDEX IF NOT EXISTS idx_image_result_run ON image_result(run_id);
-- Index for faster lookups of results by image
CREATE INDEX IF NOT EXISTS idx_image_result_image ON image_result(image_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_image_hash   ON image(file_hash);
CREATE UNIQUE INDEX IF NOT EXISTS uq_collection_image ON collection_image(collection_id, image_id);

-- Fast "images in a collection, newest first"
CREATE INDEX IF NOT EXISTS idx_collection_image_collection_added ON collection_image(collection_id, added_at DESC);
CREATE INDEX IF NOT EXISTS idx_collection_image_image       ON collection_image(image_id);

-- "Latest result per image in a collection" (your CTE version or the simplified one)
-- Drives WHERE r.collection_id=? and ORDER/LATEST by run_id
CREATE INDEX IF NOT EXISTS idx_run_collection_runid            ON run(collection_id, run_id DESC);
-- If you actually filter by an exact threshold value, use this instead/also:
CREATE INDEX IF NOT EXISTS idx_run_collection_thresh_runid     ON run(collection_id, threshold, run_id DESC);

-- Joins + grouping over image_result
-- Start from image ids, then join to runs by run_id
CREATE INDEX IF NOT EXISTS idx_imageresult_image_run      ON image_result(image_id, run_id);
-- (Optional) if you sometimes start from runs then fan to images:
-- CREATE INDEX IF NOT EXISTS idx_imageresult_run_image   ON image_result(run_id, image_id);

-- Collection listing by time
CREATE INDEX IF NOT EXISTS idx_collection_created              ON collection(created_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS uq_image_hash ON image(file_hash);
CREATE UNIQUE INDEX IF NOT EXISTS uq_collection_image ON collection_image(collection_id, image_id);