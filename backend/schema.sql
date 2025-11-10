-- BATCH: one per analysis group
CREATE TABLE IF NOT EXISTS batch (
  batch_id      TEXT PRIMARY KEY,          -- UUID (Unqiue Identifer) string
  name          TEXT,
  description   TEXT,
  folder_path   TEXT,                      -- where the folder containing the images is stored
  created_at    DATETIME NOT NULL,
  updated_at    DATETIME NOT NULL,
  model_type    TEXT,                      -- CNN, YOLO, etc.
  model_name    TEXT,
  threshold DECIMAL(10, 2) NOT NULL          -- 50.00, UI slider 
  image_count INTEGER,
  muscle_count INTEGER,
  FOREIGN KEY (model_type) REFERENCES model(model_type)
  FOREIGN KEY (image_count) REFERENCES image(image_count)
  FOREIGN KEY (muscle_count) REFERENCES muscle(muscle_count)
  FOREIGN KEY (model_name) REFERENCES model(model_name)
);

-- IMAGE: one per file in a batch
CREATE TABLE IF NOT EXISTS image (
  image_id    TEXT PRIMARY KEY,           -- UUID
  batch_id    TEXT NOT NULL,
  filename    TEXT NOT NULL,             -- original filename
  stored_path TEXT NOT NULL,             -- where YOU stored the file
  stored_polygon_path TEXT,             -- where YOU stored the polygon file
  status      TEXT NOT NULL,             -- 'pending' | 'processing' | 'done' | 'failed'
  width       INTEGER,
  height      INTEGER,
  error_msg   TEXT,                      -- if status = 'failed', what happened?
  created_at  DATETIME NOT NULL,
  updated_at  DATETIME NOT NULL,
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
  created_at    DATETIME NOT NULL,
  updated_at    DATETIME NOT NULL
);

-- RUN: each inference run on a batch using a specific model
CREATE TABLE IF NOT EXISTS run (
  run_id        TEXT PRIMARY KEY,          -- UUID
  batch_id      TEXT NOT NULL,
  model_id      TEXT NOT NULL,
  started_at    DATETIME NOT NULL,
  finished_at   DATETIME,
  status        TEXT NOT NULL,             -- "pending" | "running" | "done" | "failed"
  error_msg     TEXT,                      -- error if failed
  threshold     DECIMAL(10, 2) NOT NULL,             -- threshold score used for this run
  total_images  INTEGER,                   -- number of images processed
  mussel_count INTEGER,                -- muscles detected at this threshold
  FOREIGN KEY (batch_id) REFERENCES batch(batch_id),
  FOREIGN KEY (model_id) REFERENCES model(model_id)
  FOREIGN KEY (threshold) REFERENCES batch(threshold)
);