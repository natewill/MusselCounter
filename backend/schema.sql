-- BATCH: one per analysis group
CREATE TABLE IF NOT EXISTS batch (
  batch_id      TEXT PRIMARY KEY,          -- UUID (Unique Identifier) string
  name          TEXT,
  description   TEXT,
  folder_path   TEXT,                      -- where the folder containing the images is stored
  created_at    TEXT NOT NULL,             -- SQLite uses TEXT for dates (ISO format)
  updated_at    TEXT NOT NULL,
  model_id      TEXT,                      -- Reference to which model was used
  threshold     REAL NOT NULL DEFAULT 50.00,  -- 50.00, UI slider 
  image_count   INTEGER DEFAULT 0,         -- Calculated field, not a foreign key
  current_run_id TEXT,                      -- Reference to the current run's mussel_count
  FOREIGN KEY (model_id) REFERENCES model(model_id),
  FOREIGN KEY (current_run_id) REFERENCES run(run_id)
);

-- IMAGE: one per file in a batch
CREATE TABLE IF NOT EXISTS image (
  image_id    TEXT PRIMARY KEY,           -- UUID
  batch_id    TEXT NOT NULL,
  filename    TEXT NOT NULL,             -- original filename
  stored_path TEXT NOT NULL,             -- where the file is stored
  stored_polygon_path TEXT,             -- where the polygon file is stored
  status      TEXT NOT NULL,             -- 'pending' | 'processing' | 'done' | 'failed'
  width       INTEGER,
  height      INTEGER,
  error_msg   TEXT,                      -- if status = 'failed'
  created_at  TEXT NOT NULL,              -- SQLite uses TEXT for dates (ISO format)
  updated_at  TEXT NOT NULL,
  mussel_count INTEGER,
  FOREIGN KEY (batch_id) REFERENCES batch(batch_id)
);

-- MODEL: one per trained model file, incase we want to use different models in the future
CREATE TABLE IF NOT EXISTS model (
  model_id      TEXT PRIMARY KEY,          -- UUID 
  name          TEXT NOT NULL,             -- "CNN v2 - 2025-11 blah blah"
  type          TEXT NOT NULL,             -- CNN, YOLO, etc.
  weights_path  TEXT NOT NULL,             -- local path to .pt or .pth file
  description   TEXT,
  created_at    TEXT NOT NULL,            -- SQLite uses TEXT for dates (ISO format)
  updated_at    TEXT NOT NULL
);

-- RUN: each inference run on a batch using a specific model
CREATE TABLE IF NOT EXISTS run (
  run_id        TEXT PRIMARY KEY,          -- UUID
  batch_id      TEXT NOT NULL,
  model_id      TEXT NOT NULL,
  started_at    TEXT NOT NULL,            -- SQLite uses TEXT for dates (ISO format)
  finished_at   TEXT,                     -- NULL if still running
  status        TEXT NOT NULL,             -- "pending" | "running" | "done" | "failed"
  error_msg     TEXT,                      -- error if failed
  threshold     REAL NOT NULL,   -- threshold score used for this run
  total_images  INTEGER DEFAULT 0,        -- number of images processed
  mussel_count  INTEGER DEFAULT 0,         -- mussels detected at this threshold
  FOREIGN KEY (batch_id) REFERENCES batch(batch_id),
  FOREIGN KEY (model_id) REFERENCES model(model_id)
);