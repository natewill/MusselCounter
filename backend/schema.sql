-- BATCH: one per analysis group
CREATE TABLE IF NOT EXISTS batch (
  batch_id      INTEGER PRIMARY KEY AUTOINCREMENT,
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
  stored_polygon_path TEXT,             -- where the polygon file is stored
  file_hash   TEXT UNIQUE,               -- MD5 hash for deduplication (UNIQUE ensures no duplicates)
  width       INTEGER,
  height      INTEGER,
  error_msg   TEXT,                      -- if processing failed
  created_at  TEXT NOT NULL,             -- SQLite uses TEXT for dates (ISO format)
  updated_at  TEXT NOT NULL,
  live_mussel_count INTEGER,
  dead_mussel_count INTEGER
);

-- BATCH_IMAGE: junction table linking batches to images (many-to-many)
CREATE TABLE IF NOT EXISTS batch_image (
  batch_id    INTEGER NOT NULL,
  image_id    INTEGER NOT NULL,
  added_at    TEXT NOT NULL,            -- When this image was added to this batch
  PRIMARY KEY (batch_id, image_id),
  FOREIGN KEY (batch_id) REFERENCES batch(batch_id),
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
  created_at    TEXT NOT NULL,            -- SQLite uses TEXT for dates (ISO format)
  updated_at    TEXT NOT NULL
);

-- RUN: each inference run on a batch (can use different models)
CREATE TABLE IF NOT EXISTS run (
  run_id        INTEGER PRIMARY KEY AUTOINCREMENT,
  batch_id      INTEGER NOT NULL,
  model_id      INTEGER NOT NULL,         -- Model used for this run
  started_at    TEXT NOT NULL,            -- SQLite uses TEXT for dates (ISO format)
  finished_at   TEXT,                     -- NULL if still running, set when done
  status        TEXT DEFAULT 'pending',   -- 'pending', 'running', 'completed', 'failed'
  error_msg     TEXT,                      -- error if failed
  threshold     REAL NOT NULL,   -- threshold score used for this run
  total_images  INTEGER DEFAULT 0,        -- number of images processed
  live_mussel_count INTEGER DEFAULT 0,    -- total live mussels detected in this run
  FOREIGN KEY (batch_id) REFERENCES batch(batch_id),
  FOREIGN KEY (model_id) REFERENCES model(model_id)
);