-- COLLECTION: one per analysis group
CREATE TABLE IF NOT EXISTS collection (
  collection_id      INTEGER PRIMARY KEY AUTOINCREMENT,
  name          TEXT,
  description   TEXT,
  folder_path   TEXT,                      -- where the folder containing the images is stored
  created_at    TEXT NOT NULL,             -- SQLite uses TEXT for dates (ISO format)
  updated_at    TEXT NOT NULL,
  image_count   INTEGER DEFAULT 0,         -- Calculated field, not a foreign key
  live_mussel_count INTEGER DEFAULT 0    -- From latest processing
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

-- COLLECTION_MODEL: tracks processing state per collection+model combination (REPLACES RUN TABLE)
CREATE TABLE IF NOT EXISTS collection_model (
  collection_id INTEGER NOT NULL,
  model_id INTEGER NOT NULL,
  threshold REAL NOT NULL DEFAULT 0.5,
  status TEXT DEFAULT 'idle',              -- 'idle', 'running', 'completed', 'failed', 'cancelled'
  error_msg TEXT,
  total_images INTEGER DEFAULT 0,
  processed_count INTEGER DEFAULT 0,
  live_mussel_count INTEGER DEFAULT 0,
  dead_mussel_count INTEGER DEFAULT 0,
  started_at TEXT,
  finished_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (collection_id, model_id),
  FOREIGN KEY (collection_id) REFERENCES collection(collection_id) ON DELETE CASCADE,
  FOREIGN KEY (model_id) REFERENCES model(model_id) ON DELETE CASCADE
);

-- IMAGE_RESULT: stores inference results for each image in each collection+model combination
-- Keyed by (collection_id, model_id, image_id) instead of (run_id, image_id)
CREATE TABLE IF NOT EXISTS image_result (
  collection_id INTEGER NOT NULL,
  model_id INTEGER NOT NULL,
  image_id INTEGER NOT NULL,
  live_mussel_count INTEGER DEFAULT 0,
  dead_mussel_count INTEGER DEFAULT 0,
  polygon_path TEXT,                      -- path to JSON file with bounding boxes/polygons
  processed_at TEXT NOT NULL,             -- when this image was processed
  error_msg TEXT,                          -- error if processing failed
  PRIMARY KEY (collection_id, model_id, image_id),
  FOREIGN KEY (collection_id) REFERENCES collection(collection_id) ON DELETE CASCADE,
  FOREIGN KEY (model_id) REFERENCES model(model_id) ON DELETE CASCADE,
  FOREIGN KEY (image_id) REFERENCES image(image_id) ON DELETE CASCADE
);

-- Index for faster lookups of results by collection+model
CREATE INDEX IF NOT EXISTS idx_image_result_collection_model ON image_result(collection_id, model_id);
-- Index for faster lookups of results by image
CREATE INDEX IF NOT EXISTS idx_image_result_image ON image_result(image_id);

-- DETECTION: stores individual mussel detections with confidence scores
-- Enables threshold recalculation without re-running model
-- Now keyed by (collection_id, model_id) instead of run_id
CREATE TABLE IF NOT EXISTS detection (
  detection_id    INTEGER PRIMARY KEY AUTOINCREMENT,
  collection_id   INTEGER NOT NULL,
  model_id        INTEGER NOT NULL,
  image_id        INTEGER NOT NULL,
  confidence      REAL NOT NULL,                     -- Model confidence score (0.0 - 1.0)
  original_class  TEXT NOT NULL CHECK(original_class IN ('live', 'dead')), -- Model's original prediction
  class           TEXT CHECK(class IN ('live', 'dead')),  -- NULL = auto mode, 'live'/'dead' = manual override
  bbox_x1         REAL,                              -- Bounding box top-left x
  bbox_y1         REAL,                              -- Bounding box top-left y
  bbox_x2         REAL,                              -- Bounding box bottom-right x
  bbox_y2         REAL,                              -- Bounding box bottom-right y
  polygon_coords  TEXT,                              -- JSON array of polygon coordinates
  created_at      TEXT NOT NULL,                     -- When detection was created
  updated_at      TEXT NOT NULL,                     -- When detection was last updated
  FOREIGN KEY (collection_id) REFERENCES collection(collection_id) ON DELETE CASCADE,
  FOREIGN KEY (model_id) REFERENCES model(model_id) ON DELETE CASCADE,
  FOREIGN KEY (image_id) REFERENCES image(image_id) ON DELETE CASCADE
);

-- Index for faster lookups of detections by collection+model+image
CREATE INDEX IF NOT EXISTS idx_detection_collection_model_image ON detection(collection_id, model_id, image_id);
-- Index for faster lookups by image
CREATE INDEX IF NOT EXISTS idx_detection_image ON detection(image_id);
-- Index for confidence-based filtering (used in threshold recalculation)
CREATE INDEX IF NOT EXISTS idx_detection_confidence ON detection(confidence);

CREATE UNIQUE INDEX IF NOT EXISTS uq_image_hash   ON image(file_hash);
CREATE UNIQUE INDEX IF NOT EXISTS uq_collection_image ON collection_image(collection_id, image_id);

-- Fast "images in a collection, newest first"
CREATE INDEX IF NOT EXISTS idx_collection_image_collection_added ON collection_image(collection_id, added_at DESC);
CREATE INDEX IF NOT EXISTS idx_collection_image_image       ON collection_image(image_id);

-- Collection listing by time
CREATE INDEX IF NOT EXISTS idx_collection_created              ON collection(created_at DESC);

-- IMPORTANT: The 'run' table has been REMOVED and replaced with 'collection_model'
-- All references to run_id should be replaced with (collection_id, model_id)
