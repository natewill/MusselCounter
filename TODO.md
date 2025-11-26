# Mussel Counter - TODO List

## 🔴 Critical Bugs / Issues

### Race Condition in Collection Creation
- **Status**: Currently being debugged
- **Issue**: When clicking "Start New Run", frontend navigates to `/run/[collectionId]` before collection is fully available in database
- **Result**: Backend returns 404 for `GET /api/collections/1`, frontend floods with requests
- **Next Steps**: 
  - Review debugging logs to identify exact timing issue
  - May need to wait for collection creation confirmation before navigation
  - Consider adding retry logic with exponential backoff in React Query

### Clean Up Debugging Logs
- **Status**: In progress
- **Issue**: Extensive debugging logs added throughout codebase for troubleshooting
- **Files affected**:
  - `frontend/app/page.tsx`
  - `frontend/utils/home/collection.js`
  - `frontend/hooks/useBatchData.ts`
  - `frontend/lib/api.ts`
  - `backend/api/routers/collections.py`
  - `backend/utils/collection_utils.py`
- **Action**: Remove or comment out debugging `console.log` and `logger.info` statements once issues are resolved

---

## 🟡 High Priority Features

### Collection Management Pages

#### Collections List Page (`/collections`)
- **Status**: Not implemented
- **Description**: View all previous collections in a list/grid
- **Requirements**:
  - Display collection cards with:
    - Collection name and description
    - Image count
    - Live/dead mussel counts from latest run
    - Creation date
    - Thumbnail preview (first image)
  - Search/filter functionality
  - Sort by date, name, or mussel count
  - Click to navigate to `/collections/[collectionId]`
  - "Create New Collection" button

#### Collection Detail Page (`/collections/[collectionId]`)
- **Status**: Partially implemented (currently `/run/[runId]` serves similar purpose)
- **Description**: View-only page for collection results
- **Requirements**:
  - Display collection metadata (name, description, dates)
  - Show all images in collection with their counts
  - Display latest run results
  - Show run history for this collection
  - "Start New Run" button (creates new run)
  - "Edit Collection" button → navigate to edit page
  - Breadcrumb navigation

#### Collection Edit Page (`/collections/[collectionId]/edit`)
- **Status**: Not implemented
- **Description**: Manage collection and its images
- **Requirements**:
  - Edit collection name and description
  - Add more images to collection
  - Remove images from collection
  - View all images with delete buttons
  - Save/cancel buttons
  - Navigate back to collection view

### Image Detail Page (`/images/[imageId]`)
- **Status**: Partially implemented (API endpoint exists, frontend UI missing)
- **API**: `GET /api/images/{image_id}/results/{run_id}` ✅ Implemented
- **Description**: Full-size image viewer with detection overlays
- **Requirements**:
  - Full-size image display
  - Polygon/bounding box overlays
  - Each detection labeled with:
    - Classification (live/dead)
    - Confidence score
  - Statistics panel:
    - Live/dead counts
    - Percentages
    - Total count
    - Model used
    - Threshold applied
    - Processing timestamp
  - Comparison view: Results from other models/thresholds on same image
  - Collection context breadcrumb navigation
  - Image metadata display
  - Future: Interactive relabeling of detections

---

## 🟢 Medium Priority Features

### Model Management

#### Model Validation on Upload
- **Status**: Basic validation exists
- **Improvements needed**:
  - Verify model file integrity (can PyTorch actually load it?)
  - Better error messages for corrupted model files
  - Display model parameter count and estimated batch size on upload
  - Preview model metadata before confirming upload

#### Model Deletion
- **Status**: Not implemented
- **Requirements**:
  - Delete model endpoint: `DELETE /api/models/{model_id}`
  - UI button in model list/settings
  - Confirmation dialog (prevent accidental deletion)
  - Check if model is used in any runs before allowing deletion
  - Cascade delete or warn about orphaned runs

#### Additional Model Types
- **Status**: Placeholder code exists, not implemented
- **SSD (Single Shot Detector)**:
  - Loader: `backend/utils/model_utils/loader.py` (line 208)
  - Inference: `backend/utils/model_utils/inference.py` (line 336)
- **Custom CNN Detection**:
  - Loader: `backend/utils/model_utils/loader.py` (line 212)
  - Inference: `backend/utils/model_utils/inference.py` (line 341)
- **Action**: Implement if needed, or remove placeholder code

### Run Management

#### Run History View
- **Status**: Data exists in database, no UI
- **Requirements**:
  - Show all runs for a collection
  - Filter by model, threshold, date
  - Compare results between runs
  - Delete old runs
  - Re-run with same configuration

#### Export Results
- **Status**: Not implemented
- **Requirements**:
  - Export run results to CSV/Excel
  - Include image filenames, counts, confidence scores
  - Export polygon coordinates
  - Export summary statistics
  - Download all detection images with overlays as ZIP

---

## 🔵 Low Priority / Polish

### UI/UX Improvements

#### Dark Mode Consistency
- **Status**: Partially implemented
- **Issue**: Some components have dark mode styles, others don't
- **Action**: Audit all components for consistent dark mode support

#### Loading States
- **Status**: Some components have loading spinners, others don't
- **Action**: 
  - Skeleton loaders for image grids
  - Better loading indicators for file uploads
  - Progress bars for model uploads (1GB files)

#### Error Handling
- **Status**: Basic error messages exist
- **Improvements**:
  - Better error messages with actionable advice
  - Toast notifications instead of inline errors
  - Retry buttons for failed operations
  - Error boundary components

#### Accessibility
- **Status**: Not audited
- **Action**:
  - Add ARIA labels
  - Keyboard navigation support
  - Screen reader testing
  - Color contrast compliance

### Performance

#### Image Lazy Loading
- **Status**: Basic lazy loading exists
- **Improvements**:
  - Virtual scrolling for large image lists (1000+ images)
  - Progressive image loading (blur-up technique)
  - Thumbnail generation on backend

#### Database Optimization
- **Status**: Basic indexes exist
- **Improvements**:
  - Add more indexes for common queries
  - Consider connection pooling
  - Query optimization for large collections

### Testing

#### Unit Tests
- **Status**: Minimal/none
- **Priority**: Write tests for:
  - API endpoints (FastAPI test client)
  - Database operations
  - File validation utilities
  - Inference functions (mocked)

#### Integration Tests
- **Status**: None
- **Priority**: Test end-to-end workflows:
  - Collection creation → image upload → run inference → view results
  - Model upload and selection
  - Run cancellation

#### Frontend Tests
- **Status**: None
- **Priority**: 
  - Component unit tests (Jest + React Testing Library)
  - E2E tests (Playwright)

---

## 📝 Documentation Updates

### README Updates Needed
- **Model auto-detection**: README says models are auto-detected from `data/models/`, but this was recently disabled
- **Model upload**: Document the new "Add Model" button functionality
- **Navigation flow**: Update description of "Start New Run" button (doesn't auto-start inference)
- **Quick Process mode**: Update to reflect current navigation behavior

### Code Documentation
- **Add JSDoc comments**: Many React components lack proper documentation
- **API response examples**: Add more example responses in API documentation
- **Architecture diagrams**: Visual representation of data flow

---

## 🚀 Future Enhancements

### Advanced Features

#### Batch Operations
- Select multiple images and delete at once
- Select multiple images and re-run inference
- Bulk edit image metadata

#### Image Annotations
- Manual annotation tool (draw bounding boxes)
- Train new models on annotated data
- Correct/refine model predictions

#### User Management
- Multiple user accounts
- Authentication and authorization
- User-specific collections

#### Cloud Deployment
- Deploy to cloud platform (AWS, Azure, GCP)
- S3/blob storage for images
- PostgreSQL instead of SQLite
- WebSocket support for real-time updates (instead of polling)

#### Mobile Support
- Responsive design for tablets
- Native mobile app (React Native)
- Camera integration for field collection

---

## 📦 Production Readiness

### PyInstaller Bundling
- **Status**: Mentioned in README, not tested recently
- **Requirements**:
  - Test .exe generation
  - Bundle frontend build with backend
  - Auto-open browser on startup
  - Installer/uninstaller
  - Windows/Mac support

### Configuration
- **Status**: Hardcoded values in `config.py`
- **Improvements**:
  - Environment-based configuration
  - Settings UI in frontend
  - Adjustable file size limits
  - Configurable batch sizes

### Logging
- **Status**: Basic logging exists
- **Improvements**:
  - Log rotation
  - Configurable log levels
  - Log file management
  - Error tracking (Sentry integration)

### Security
- **Status**: Basic validation exists
- **Improvements**:
  - Rate limiting on API endpoints
  - CSRF protection
  - Input sanitization audit
  - File upload security review
  - Path traversal prevention (already partially implemented)

---

## ✅ Recently Completed

- ✅ Model upload functionality via UI
- ✅ Add Model button with success/error messages
- ✅ Removed model picker from homepage
- ✅ Changed "Create Collection" to "Start New Run" button
- ✅ Navigate to run page without auto-starting inference
- ✅ Support model files up to 1GB
- ✅ Comprehensive debugging logs for troubleshooting
- ✅ Database version checker for cache invalidation
- ✅ Smart run reuse (only process new images)
- ✅ Real-time progress updates during inference
- ✅ Run cancellation support
- ✅ Image deduplication by hash
- ✅ Dynamic batch size calculation
- ✅ CPU optimization for inference
- ✅ Async file operations

