# Run Table Removal Refactor Plan

## Overview

This document outlines a major architectural refactor to simplify the codebase by removing the `run` table and replacing it with a `collection_model` table that tracks processing state per collection+model combination.

**Last Updated**: 2025-11-26

---

## Why This Refactor?

### Problems with Current Architecture
- **Over-engineered for use case**: The `run` table was designed to track historical runs, but we don't need run history
- **Threshold history is irrelevant**: Threshold recalculation makes tracking different thresholds unnecessary
- **Complex run reuse logic**: Checking if `(collection_id, model_id, threshold)` combo exists adds complexity
- **run_id everywhere**: run_id gets passed through 15+ files, adding indirection

### Benefits of New Architecture
- ✅ **Simpler mental model**: "Collection + Model" instead of "Runs"
- ✅ **Less code**: Estimate ~300-500 lines deleted, ~700 lines modified
- ✅ **Cleaner API**: More intuitive endpoints (`/collections/{id}/process` vs `/runs/{id}`)
- ✅ **Better for use case**: Support multiple models per collection without run history complexity
- ✅ **Easier to extend**: Adding features will be simpler with less indirection

### Trade-offs
- ❌ **Big migration effort**: ~13-17 hours of work
- ❌ **Risky**: Touching core architecture
- ❌ **Lose run history**: Can't see past runs (acceptable for this use case)
- ❌ **Breaking change**: Requires data migration

---

## New Schema Design

### New Table: `collection_model`

Tracks processing state per collection+model combination (replaces `run` table):

```sql
CREATE TABLE collection_model (
  collection_id INTEGER NOT NULL,
  model_id INTEGER NOT NULL,
  threshold REAL NOT NULL DEFAULT 0.5,
  status TEXT DEFAULT 'idle',  -- 'idle', 'running', 'completed', 'failed'
  error_msg TEXT,
  total_images INTEGER DEFAULT 0,
  processed_count INTEGER DEFAULT 0,
  live_mussel_count INTEGER DEFAULT 0,
  dead_mussel_count INTEGER DEFAULT 0,
  started_at TEXT,
  finished_at TEXT,
  PRIMARY KEY (collection_id, model_id),
  FOREIGN KEY (collection_id) REFERENCES collection(collection_id),
  FOREIGN KEY (model_id) REFERENCES model(model_id)
);
```

### Modified Table: `image_result`

Now keyed by `(collection_id, model_id, image_id)` instead of `(run_id, image_id)`:

```sql
CREATE TABLE image_result (
  collection_id INTEGER NOT NULL,
  model_id INTEGER NOT NULL,
  image_id INTEGER NOT NULL,
  live_mussel_count INTEGER DEFAULT 0,
  dead_mussel_count INTEGER DEFAULT 0,
  polygon_path TEXT,
  processed_at TEXT NOT NULL,
  error_msg TEXT,
  PRIMARY KEY (collection_id, model_id, image_id),
  FOREIGN KEY (collection_id) REFERENCES collection(collection_id),
  FOREIGN KEY (model_id) REFERENCES model(model_id),
  FOREIGN KEY (image_id) REFERENCES image(image_id)
);

CREATE INDEX idx_image_result_collection_model ON image_result(collection_id, model_id);
```

### Modified Table: `detection`

Replace `run_id` with `collection_id` + `model_id`:

```sql
CREATE TABLE detection (
  detection_id INTEGER PRIMARY KEY AUTOINCREMENT,
  collection_id INTEGER NOT NULL,
  model_id INTEGER NOT NULL,
  image_id INTEGER NOT NULL,
  confidence REAL NOT NULL,
  original_class TEXT NOT NULL CHECK(original_class IN ('live', 'dead')),
  class TEXT CHECK(class IN ('live', 'dead')),
  bbox_x1 REAL,
  bbox_y1 REAL,
  bbox_x2 REAL,
  bbox_y2 REAL,
  polygon_coords TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (collection_id) REFERENCES collection(collection_id),
  FOREIGN KEY (model_id) REFERENCES model(model_id),
  FOREIGN KEY (image_id) REFERENCES image(image_id)
);

CREATE INDEX idx_detection_collection_model_image ON detection(collection_id, model_id, image_id);
```

### Removed Table

```sql
DROP TABLE IF EXISTS run;
```

---

## Backend Changes

### Files to DELETE
- `backend/api/routers/runs.py` - Entire file removed
- Functions in `backend/utils/run_utils/db.py`: `get_or_create_run()`, `get_run()`, `update_run_status()`

### Files to CREATE
- `backend/utils/collection_model_utils.py` - New utility functions:
  - `async def get_or_create_collection_model(db, collection_id, model_id)`
  - `async def update_collection_model_status(db, collection_id, model_id, status, ...)`
  - `async def get_collection_model(db, collection_id, model_id)`
  - `async def get_collection_models(db, collection_id)` - Get all models used on a collection
- `backend/migrate_to_collection_model.py` - One-time migration script

### Files to MODIFY

#### 1. `backend/schema.sql` ✏️
- Drop `run` table
- Add `collection_model` table
- Update `image_result` primary key and foreign keys
- Update `detection` to replace `run_id` with `collection_id` + `model_id`

#### 2. `backend/api/schemas.py` ✏️
- **Remove**: `RunResponse`, `StartRunRequest`
- **Add**:
  ```python
  class CollectionModelResponse(BaseModel):
      collection_id: int
      model_id: int
      threshold: float
      status: str
      error_msg: Optional[str] = None
      total_images: int = 0
      processed_count: int = 0
      live_mussel_count: int = 0
      dead_mussel_count: int = 0
      started_at: Optional[str] = None
      finished_at: Optional[str] = None

  class StartProcessingRequest(BaseModel):
      model_id: int
      threshold: Optional[float] = 0.5
  ```

#### 3. `backend/api/routers/collections.py` ✏️
- **Change endpoint**: `POST /api/collections/{collection_id}/run` → `/api/collections/{collection_id}/process`
- **Update handler**:
  - Replace `get_or_create_run()` with `get_or_create_collection_model()`
  - Return `CollectionModelResponse` instead of `RunResponse`
  - Update background task signature: `process_collection(db, collection_id, model_id)` instead of `process_collection_run(db, run_id)`
- **Add new endpoint**: `GET /api/collections/{collection_id}/models` - List all models that have been used on this collection with their statuses
- **Add new endpoint**: `POST /api/collections/{collection_id}/process/stop?model_id={model_id}` - Stop processing for specific model

#### 4. `backend/api/routers/images.py` ✏️
- **Change endpoint**: `GET /api/images/{image_id}/results/{run_id}` → `GET /api/images/{image_id}/results`
- **Add query params**: `?collection_id={}&model_id={}`
- **Update queries**: Use `(collection_id, model_id, image_id)` to fetch results instead of `(run_id, image_id)`

#### 5. `backend/utils/run_utils/collection_processor.py` ✏️ (MAJOR CHANGES)
- **Change function signature**:
  ```python
  # OLD
  async def process_collection_run(db: aiosqlite.Connection, run_id: int)

  # NEW
  async def process_collection(db: aiosqlite.Connection, collection_id: int, model_id: int)
  ```
- **Update all queries**:
  - Replace `run_id` with `(collection_id, model_id)`
  - Query `collection_model` table instead of `run` table
  - Update status using `update_collection_model_status()`
- **Update incremental processing logic**:
  ```python
  # Check which images haven't been processed yet for this collection+model
  cursor = await db.execute(
      """SELECT ci.image_id
         FROM collection_image ci
         LEFT JOIN image_result ir
           ON ci.image_id = ir.image_id
           AND ir.collection_id = ?
           AND ir.model_id = ?
         WHERE ci.collection_id = ?
           AND ir.image_id IS NULL""",
      (collection_id, model_id, collection_id)
  )
  ```

#### 6. `backend/utils/run_utils/image_processor.py` ✏️
- **Update function signature**:
  ```python
  # OLD
  async def process_image_batch(db, run_id, model, images, threshold)

  # NEW
  async def process_image_batch(db, collection_id, model_id, model, images, threshold)
  ```
- **Update `image_result` inserts**:
  ```python
  await db.execute(
      """INSERT OR REPLACE INTO image_result
         (collection_id, model_id, image_id, live_mussel_count, dead_mussel_count, polygon_path, processed_at)
         VALUES (?, ?, ?, ?, ?, ?, ?)""",
      (collection_id, model_id, image_id, live_count, dead_count, polygon_path, now)
  )
  ```
- **Update `detection` inserts**: Add `collection_id` and `model_id` columns

#### 7. `backend/utils/collection_utils.py` ✏️
- **Update `get_collection_details()`**:
  - Join with `collection_model` table to get model statuses
  - Return list of models that have been run on this collection
  - Remove `latest_run` field from response
  - Add `models` field:
    ```python
    {
      "collection": {...},
      "images": [...],
      "models": [
        {
          "model_id": 1,
          "model_name": "YOLOv8n",
          "status": "completed",
          "threshold": 0.5,
          "live_mussel_count": 150,
          ...
        },
        ...
      ]
    }
    ```

#### 8. `backend/main.py` ✏️
- Remove `runs` router import and registration:
  ```python
  # REMOVE
  from api.routers import collections, models, runs, system, images
  app.include_router(runs.router)

  # KEEP
  from api.routers import collections, models, system, images
  ```

---

## Frontend Changes

### Files to RENAME
- `frontend/hooks/useStartRun.ts` → `frontend/hooks/useStartProcessing.ts`
- `frontend/hooks/useStopRun.ts` → `frontend/hooks/useStopProcessing.ts`

### Files to MODIFY

#### 1. `frontend/lib/api.ts` ✏️

**Changes**:
```typescript
// OLD
export const startRun = async (collectionId: number, modelId: number, threshold?: number) => {
  const response = await apiClient.post(`/api/collections/${collectionId}/run`, {
    model_id: modelId,
    threshold
  });
  return response.data; // Returns { run_id, status, ... }
};

export const getRun = async (runId: number) => {
  const response = await apiClient.get(`/api/runs/${runId}`);
  return response.data;
};

export const stopRun = async (runId: number) => {
  const response = await apiClient.post(`/api/runs/${runId}/stop`);
  return response.data;
};

// NEW
export const startProcessing = async (collectionId: number, modelId: number, threshold?: number) => {
  const response = await apiClient.post(`/api/collections/${collectionId}/process`, {
    model_id: modelId,
    threshold
  });
  return response.data; // Returns { collection_id, model_id, status, ... }
};

export const getCollectionModelStatus = async (collectionId: number, modelId: number) => {
  const response = await apiClient.get(`/api/collections/${collectionId}/models/${modelId}`);
  return response.data;
};

export const stopProcessing = async (collectionId: number, modelId: number) => {
  const response = await apiClient.post(`/api/collections/${collectionId}/process/stop`, null, {
    params: { model_id: modelId }
  });
  return response.data;
};

// Update image results endpoint
export const getImageResults = async (imageId: number, collectionId: number, modelId: number) => {
  const response = await apiClient.get(`/api/images/${imageId}/results`, {
    params: { collection_id: collectionId, model_id: modelId }
  });
  return response.data;
};

// New: Get all models used on a collection
export const getCollectionModels = async (collectionId: number) => {
  const response = await apiClient.get(`/api/collections/${collectionId}/models`);
  return response.data;
};
```

#### 2. `frontend/hooks/useCollectionData.ts` ✏️

**Changes**:
```typescript
// OLD interface
interface CollectionData {
  images: Image[];
  latest_run: {
    run_id: number;
    status: string;
    model_id: number;
    threshold: number;
  } | null;
}

// NEW interface
interface CollectionData {
  images: Image[];
  models: Array<{
    model_id: number;
    model_name: string;
    status: string;
    threshold: number;
    live_mussel_count: number;
    dead_mussel_count: number;
    processed_count: number;
    total_images: number;
  }>;
}

// Update hook to track selected model
export function useCollectionData(collectionId: number, selectedModelId: number | null) {
  // ... fetch collection data
  // Find the selected model's status
  const selectedModelStatus = data?.models?.find(m => m.model_id === selectedModelId);

  return {
    collectionData: data,
    selectedModelStatus,
    isLoading,
    error
  };
}
```

#### 3. `frontend/hooks/useStartProcessing.ts` (renamed from useStartRun.ts) ✏️

**Major simplification** - no more run_id tracking:

```typescript
// OLD
export function useStartRun() {
  const [runId, setRunId] = useState<number | null>(null);
  // ... complex state management
}

// NEW
export function useStartProcessing() {
  const mutation = useMutation({
    mutationFn: ({ collectionId, modelId, threshold }: StartProcessingParams) =>
      startProcessing(collectionId, modelId, threshold),
    onSuccess: (data) => {
      // No run_id to track, just trigger refetch
      queryClient.invalidateQueries(['collection', data.collection_id]);
    }
  });

  return {
    startProcessing: mutation.mutate,
    isStarting: mutation.isPending
  };
}
```

#### 4. `frontend/hooks/useStopProcessing.ts` (renamed from useStopRun.ts) ✏️

```typescript
// OLD
export function useStopRun(runId: number) {
  // ...
}

// NEW
export function useStopProcessing(collectionId: number, modelId: number) {
  const mutation = useMutation({
    mutationFn: () => stopProcessing(collectionId, modelId),
    // ...
  });
}
```

#### 5. `frontend/hooks/useRunState.ts` ✏️ (MAJOR SIMPLIFICATION)

**Estimate: 50% less code**

Remove:
- All `run_id` tracking
- `previousRunId` state
- Run reuse detection logic

Simplify to just track:
- Processing status for selected model
- Flash animations for newly processed images

```typescript
// Key simplifications:
// - No more run_id comparison
// - Just check if selectedModelStatus changed
// - Simpler state management

export function useRunState(
  collectionData: CollectionData | undefined,
  selectedModelId: number | null,
  recentlyUploadedImageIds: Set<number>
) {
  const selectedModelStatus = collectionData?.models?.find(m => m.model_id === selectedModelId);

  // Much simpler logic - just track status changes
  // Remove complex run reuse detection
  // ...
}
```

#### 6. `frontend/hooks/useThresholdRecalculation.ts` ✏️

```typescript
// OLD
export function useThresholdRecalculation(runId: number) {
  const recalculate = async (newThreshold: number) => {
    await api.recalculateRunThreshold(runId, newThreshold);
  };
}

// NEW
export function useThresholdRecalculation(collectionId: number, modelId: number) {
  const recalculate = async (newThreshold: number) => {
    await api.recalculateThreshold(collectionId, modelId, newThreshold);
  };
}
```

#### 7. `frontend/components/run/RunStatus.jsx` ✏️

**Changes**:
```typescript
// OLD props
interface RunStatusProps {
  runId: number;
  status: string;
}

// NEW props (simpler)
interface RunStatusProps {
  status: string;
  modelName: string;
  processedCount: number;
  totalImages: number;
}

// Component no longer needs to fetch run details, just displays what's passed in
```

#### 8. `frontend/app/collection/[collectionId]/page.tsx` ✏️

**Add model selector/tabs**:
```typescript
export default function CollectionPage({ params }: { params: { collectionId: string } }) {
  const collectionId = parseInt(params.collectionId);
  const [selectedModelId, setSelectedModelId] = useState<number | null>(null);

  const { collectionData, selectedModelStatus } = useCollectionData(collectionId, selectedModelId);

  return (
    <div>
      {/* Model selector tabs */}
      <div className="model-tabs">
        {collectionData?.models?.map(model => (
          <button
            key={model.model_id}
            onClick={() => setSelectedModelId(model.model_id)}
            className={selectedModelId === model.model_id ? 'active' : ''}
          >
            {model.model_name}
          </button>
        ))}
      </div>

      {/* Status display */}
      {selectedModelStatus && (
        <RunStatus
          status={selectedModelStatus.status}
          modelName={selectedModelStatus.model_name}
          processedCount={selectedModelStatus.processed_count}
          totalImages={selectedModelStatus.total_images}
        />
      )}

      {/* Image list filtered/styled by selected model */}
    </div>
  );
}
```

#### 9. `frontend/app/edit/[imageId]/page.tsx` ✏️

**Change URL params**:
```typescript
// OLD
// URL: /edit/123?runId=45
const searchParams = useSearchParams();
const runId = searchParams.get('runId');
const imageResults = await getImageResults(imageId, runId);

// NEW
// URL: /edit/123?collectionId=10&modelId=2
const searchParams = useSearchParams();
const collectionId = searchParams.get('collectionId');
const modelId = searchParams.get('modelId');
const imageResults = await getImageResults(imageId, collectionId, modelId);
```

---

## Step-by-Step Implementation Plan

### Phase 1: Schema Migration (1-2 hours)

**Step 1.1: Backup Database**
```bash
cp backend/mussel_counter.db backend/mussel_counter.db.backup
```

**Step 1.2: Create Migration Script**

Create `backend/migrate_to_collection_model.py`:

```python
"""
One-time migration script to convert from run-based to collection_model-based schema.
Run this ONCE before deploying the refactored code.
"""
import aiosqlite
import asyncio
from pathlib import Path

async def migrate():
    db_path = Path(__file__).parent / "mussel_counter.db"

    async with aiosqlite.connect(db_path) as db:
        print("Starting migration...")

        # Step 1: Create new collection_model table
        print("Creating collection_model table...")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS collection_model (
              collection_id INTEGER NOT NULL,
              model_id INTEGER NOT NULL,
              threshold REAL NOT NULL DEFAULT 0.5,
              status TEXT DEFAULT 'idle',
              error_msg TEXT,
              total_images INTEGER DEFAULT 0,
              processed_count INTEGER DEFAULT 0,
              live_mussel_count INTEGER DEFAULT 0,
              dead_mussel_count INTEGER DEFAULT 0,
              started_at TEXT,
              finished_at TEXT,
              PRIMARY KEY (collection_id, model_id),
              FOREIGN KEY (collection_id) REFERENCES collection(collection_id),
              FOREIGN KEY (model_id) REFERENCES model(model_id)
            )
        """)

        # Step 2: Migrate data from run table to collection_model
        # For each unique (collection_id, model_id), take the latest run
        print("Migrating run data to collection_model...")
        await db.execute("""
            INSERT INTO collection_model
              (collection_id, model_id, threshold, status, error_msg,
               total_images, processed_count, live_mussel_count, dead_mussel_count,
               started_at, finished_at)
            SELECT
              collection_id,
              model_id,
              threshold,
              status,
              error_msg,
              total_images,
              processed_count,
              live_mussel_count,
              0 as dead_mussel_count,  -- Add if column exists
              started_at,
              finished_at
            FROM run r1
            WHERE run_id IN (
              SELECT MAX(run_id)
              FROM run r2
              WHERE r2.collection_id = r1.collection_id
                AND r2.model_id = r1.model_id
              GROUP BY collection_id, model_id
            )
        """)

        # Step 3: Add collection_id and model_id to image_result
        print("Updating image_result table...")
        await db.execute("ALTER TABLE image_result ADD COLUMN collection_id INTEGER")
        await db.execute("ALTER TABLE image_result ADD COLUMN model_id INTEGER")

        # Populate collection_id and model_id from run table
        await db.execute("""
            UPDATE image_result
            SET collection_id = (SELECT collection_id FROM run WHERE run.run_id = image_result.run_id),
                model_id = (SELECT model_id FROM run WHERE run.run_id = image_result.run_id)
        """)

        # Step 4: Update detection table similarly
        print("Updating detection table...")
        await db.execute("ALTER TABLE detection ADD COLUMN collection_id INTEGER")
        await db.execute("ALTER TABLE detection ADD COLUMN model_id INTEGER")

        await db.execute("""
            UPDATE detection
            SET collection_id = (SELECT collection_id FROM run WHERE run.run_id = detection.run_id),
                model_id = (SELECT model_id FROM run WHERE run.run_id = detection.run_id)
        """)

        await db.commit()

        # Step 5: Create new tables with updated schema
        print("Recreating tables with new schema...")

        # Backup old tables
        await db.execute("ALTER TABLE image_result RENAME TO image_result_old")
        await db.execute("ALTER TABLE detection RENAME TO detection_old")

        # Create new tables
        await db.execute("""
            CREATE TABLE image_result (
              collection_id INTEGER NOT NULL,
              model_id INTEGER NOT NULL,
              image_id INTEGER NOT NULL,
              live_mussel_count INTEGER DEFAULT 0,
              dead_mussel_count INTEGER DEFAULT 0,
              polygon_path TEXT,
              processed_at TEXT NOT NULL,
              error_msg TEXT,
              PRIMARY KEY (collection_id, model_id, image_id),
              FOREIGN KEY (collection_id) REFERENCES collection(collection_id),
              FOREIGN KEY (model_id) REFERENCES model(model_id),
              FOREIGN KEY (image_id) REFERENCES image(image_id)
            )
        """)

        await db.execute("""
            CREATE TABLE detection (
              detection_id INTEGER PRIMARY KEY AUTOINCREMENT,
              collection_id INTEGER NOT NULL,
              model_id INTEGER NOT NULL,
              image_id INTEGER NOT NULL,
              confidence REAL NOT NULL,
              original_class TEXT NOT NULL CHECK(original_class IN ('live', 'dead')),
              class TEXT CHECK(class IN ('live', 'dead')),
              bbox_x1 REAL,
              bbox_y1 REAL,
              bbox_x2 REAL,
              bbox_y2 REAL,
              polygon_coords TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY (collection_id) REFERENCES collection(collection_id),
              FOREIGN KEY (model_id) REFERENCES model(model_id),
              FOREIGN KEY (image_id) REFERENCES image(image_id)
            )
        """)

        # Copy data
        await db.execute("""
            INSERT INTO image_result
            SELECT collection_id, model_id, image_id, live_mussel_count,
                   dead_mussel_count, polygon_path, processed_at, error_msg
            FROM image_result_old
            WHERE collection_id IS NOT NULL AND model_id IS NOT NULL
        """)

        await db.execute("""
            INSERT INTO detection
            SELECT detection_id, collection_id, model_id, image_id, confidence,
                   original_class, class, bbox_x1, bbox_y1, bbox_x2, bbox_y2,
                   polygon_coords, created_at, updated_at
            FROM detection_old
            WHERE collection_id IS NOT NULL AND model_id IS NOT NULL
        """)

        # Create indexes
        print("Creating indexes...")
        await db.execute("CREATE INDEX idx_image_result_collection_model ON image_result(collection_id, model_id)")
        await db.execute("CREATE INDEX idx_detection_collection_model_image ON detection(collection_id, model_id, image_id)")

        await db.commit()

        # Step 6: Drop old tables (optional - keep for safety initially)
        # await db.execute("DROP TABLE image_result_old")
        # await db.execute("DROP TABLE detection_old")
        # await db.execute("DROP TABLE run")

        print("Migration complete!")
        print("Old tables preserved as *_old for safety. Drop them manually after verification.")

if __name__ == "__main__":
    asyncio.run(migrate())
```

**Step 1.3: Run Migration**
```bash
cd backend
source venv/bin/activate
python migrate_to_collection_model.py
```

**Step 1.4: Verify Migration**
```bash
sqlite3 mussel_counter.db
.tables  # Should show collection_model table
SELECT * FROM collection_model LIMIT 5;
.quit
```

---

### Phase 2: Backend Core Changes (3-4 hours)

**Step 2.1: Create `backend/utils/collection_model_utils.py`**

[See detailed function implementations in backend changes section]

**Step 2.2: Update `backend/utils/run_utils/collection_processor.py`**

Key changes:
- Change function signature to take `(collection_id, model_id)` instead of `run_id`
- Replace all run table queries with collection_model table
- Update all database queries to use new schema

**Step 2.3: Update `backend/utils/run_utils/image_processor.py`**

Update batch processing functions to use new keys.

**Step 2.4: Update `backend/utils/collection_utils.py`**

Modify `get_collection_details()` to return model statuses.

---

### Phase 3: Backend API Changes (2-3 hours)

**Step 3.1: Update `backend/api/schemas.py`**

Remove old schemas, add new ones.

**Step 3.2: Update `backend/api/routers/collections.py`**

Change endpoints and handlers.

**Step 3.3: Update `backend/api/routers/images.py`**

Update image results endpoint.

**Step 3.4: Delete `backend/api/routers/runs.py`**

**Step 3.5: Update `backend/main.py`**

Remove runs router.

**Step 3.6: Test Backend**

```bash
# Start backend
cd backend
source venv/bin/activate
uvicorn main:app --reload

# Test with curl
curl http://127.0.0.1:8000/api/collections
curl -X POST http://127.0.0.1:8000/api/collections/1/process \
  -H "Content-Type: application/json" \
  -d '{"model_id": 1, "threshold": 0.5}'
```

---

### Phase 4: Frontend API Client (1 hour)

**Step 4.1: Update `frontend/lib/api.ts`**

[See detailed changes in frontend section]

**Step 4.2: Test in Browser Console**

```javascript
// Test new API functions
import * as api from './lib/api';
await api.getCollectionModels(1);
await api.startProcessing(1, 1, 0.5);
```

---

### Phase 5: Frontend Hooks (2-3 hours)

**Step 5.1-5.6: Update all hooks**

[See detailed changes for each hook in frontend section]

---

### Phase 6: Frontend Components (2 hours)

**Step 6.1-6.4: Update all components**

[See detailed changes for each component in frontend section]

---

### Phase 7: Testing & Documentation (2 hours)

**Step 7.1: Manual Testing Checklist**

- [ ] Upload images to new collection
- [ ] Start processing with Model A
- [ ] Verify progress updates work
- [ ] Wait for completion
- [ ] Verify results display correctly
- [ ] Start processing with Model B on same collection
- [ ] View both Model A and Model B results side-by-side
- [ ] Add more images to collection
- [ ] Restart processing (verify only new images processed)
- [ ] Change threshold via slider
- [ ] Verify threshold recalculation works
- [ ] Stop processing mid-run
- [ ] Verify cancel works correctly
- [ ] Test error handling (invalid model, etc.)
- [ ] Test image detail page with new URL params
- [ ] Verify polygon editing still works

**Step 7.2: Update Documentation**

- [ ] Update `README.md` - API endpoints section
- [ ] Update `CLAUDE.md` - Architecture section
- [ ] Update `BACKEND_GUIDE.md` - Remove run references
- [ ] Update `COLLECTION_PROCESSOR_EXPLAINED.md` - Update with new flow
- [ ] Delete or update `AGENTS.md` if it references runs

**Step 7.3: Code Cleanup**

- [ ] Remove commented-out code
- [ ] Clean up imports
- [ ] Run linters (backend: black, isort, flake8; frontend: eslint)
- [ ] Drop old database tables after verification:
  ```bash
  sqlite3 backend/mussel_counter.db
  DROP TABLE IF EXISTS image_result_old;
  DROP TABLE IF EXISTS detection_old;
  DROP TABLE IF EXISTS run;
  .quit
  ```

---

## Effort Estimate

| Phase | Time | Complexity | Risk Level |
|-------|------|-----------|-----------|
| 1. Schema Migration | 1-2h | Medium | High |
| 2. Backend Core | 3-4h | High | High |
| 3. Backend API | 2-3h | Medium | Medium |
| 4. Frontend API Client | 1h | Low | Low |
| 5. Frontend Hooks | 2-3h | Medium | Medium |
| 6. Frontend Components | 2h | Low | Low |
| 7. Testing & Docs | 2h | Low | Medium |
| **TOTAL** | **13-17 hours** | **High** | **High** |

---

## Alternative: "Soft" Refactor

If the full refactor is too risky or time-consuming, consider this **lighter approach** (4-5 hours):

### What to Keep
- Keep the `run` table in database
- Keep backend run-based architecture

### What to Change
1. **Add UNIQUE constraint**: `(collection_id, model_id, threshold)` on `run` table
2. **Hide run_id from frontend**:
   - Frontend only tracks `selectedModelId`
   - API adds endpoint: `GET /api/collections/{id}/latest-run?model_id={modelId}`
   - Returns latest run for that collection+model combo
3. **Simplify frontend state**: Remove run_id tracking from hooks
4. **Auto-reuse runs**: Backend already does this, just make it transparent

### Benefits
- 70% of the simplification benefits
- 30% of the effort
- Much lower risk
- Easier to revert

---

## Decision Checklist

Before starting, consider:

- [ ] **Do you have active users?** If yes, plan maintenance window
- [ ] **Do you have data you care about?** Make backups!
- [ ] **Do you have time for 15+ hours of work?** Block out the time
- [ ] **Are you comfortable with database migrations?** Test on backup first
- [ ] **Do you want run history?** If yes, DON'T do this refactor

---

## Rollback Plan

If something goes wrong:

1. **Database rollback**:
   ```bash
   cp backend/mussel_counter.db.backup backend/mussel_counter.db
   ```

2. **Code rollback**:
   ```bash
   git checkout main  # or your pre-refactor branch
   ```

3. **Verify old version works**:
   - Test upload, processing, results display
   - Check that no data was lost

---

## Next Steps

1. **Review this plan** - Make sure you understand each step
2. **Make decision** - Full refactor vs soft refactor vs no refactor
3. **Create feature branch**: `git checkout -b refactor-remove-runs`
4. **Start with Phase 1** - Schema migration (safest to test first)
5. **Test each phase** before moving to next
6. **Commit frequently** with clear messages

**Want to get started?** Let me know and I can help with:
- Writing the migration script
- Updating specific files
- Testing strategies
- Anything else!
