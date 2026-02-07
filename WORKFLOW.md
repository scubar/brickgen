# BrickGen Workflow Guide

This document explains the complete workflow from searching a LEGO set to printing your bricks.

## End-to-End User Journey

```
┌──────────────────────────────────────────────────────────────┐
│                     BrickGen Workflow                         │
└──────────────────────────────────────────────────────────────┘

1. SEARCH & SELECT
   ┌────────────────────────┐
   │  User searches for     │
   │  "Millennium Falcon"   │
   └───────────┬────────────┘
               │
               ▼
   ┌────────────────────────┐
   │ Rebrickable API returns│
   │  matching sets         │
   └───────────┬────────────┘
               │
               ▼
   ┌────────────────────────┐
   │  User selects set      │
   │  "75192-1"             │
   └───────────┬────────────┘
               │
               ▼

2. CONFIGURE
   ┌────────────────────────┐
   │  Set build plate size  │
   │  220mm × 220mm         │
   └───────────┬────────────┘
               │
               ▼
   ┌────────────────────────┐
   │  Click "Generate 3MF"  │
   └───────────┬────────────┘
               │
               ▼

3. PROCESSING (Background)
   ┌────────────────────────┐
   │  Create job in DB      │
   │  Status: pending       │
   └───────────┬────────────┘
               │
               ▼
   ┌────────────────────────┐
   │  Fetch parts list      │
   │  Rebrickable API       │
   │  (~500 parts found)    │
   └───────────┬────────────┘
               │
               ▼
   ┌────────────────────────┐
   │  Convert parts to STL  │
   │  Progress: 0-70%       │
   │                        │
   │  For each part:        │
   │  ├─ Find .dat file     │
   │  ├─ Parse geometry     │
   │  ├─ Create mesh        │
   │  └─ Save STL           │
   └───────────┬────────────┘
               │
               ▼
   ┌────────────────────────┐
   │  Arrange on plate      │
   │  Progress: 70-85%      │
   │                        │
   │  ├─ Calculate sizes    │
   │  ├─ Sort by area       │
   │  ├─ Pack parts         │
   │  └─ Optimize layout    │
   └───────────┬────────────┘
               │
               ▼
   ┌────────────────────────┐
   │  Generate 3MF file     │
   │  Progress: 85-100%     │
   │                        │
   │  ├─ Combine meshes     │
   │  ├─ Create 3MF doc     │
   │  └─ Save file          │
   └───────────┬────────────┘
               │
               ▼

4. DOWNLOAD
   ┌────────────────────────┐
   │  Job complete!         │
   │  Status: completed     │
   └───────────┬────────────┘
               │
               ▼
   ┌────────────────────────┐
   │  User downloads        │
   │  75192-1.3mf           │
   └───────────┬────────────┘
               │
               ▼

5. PRINT
   ┌────────────────────────┐
   │  Open in slicer        │
   │  (PrusaSlicer/Cura)    │
   └───────────┬────────────┘
               │
               ▼
   ┌────────────────────────┐
   │  Slice with settings   │
   │  ├─ Layer height       │
   │  ├─ Infill %           │
   │  └─ Supports           │
   └───────────┬────────────┘
               │
               ▼
   ┌────────────────────────┐
   │  Export G-code         │
   └───────────┬────────────┘
               │
               ▼
   ┌────────────────────────┐
   │  Send to printer       │
   │  START PRINTING!       │
   └────────────────────────┘
```

## Detailed Processing Steps

### Step 1: Set Search

**What Happens:**
1. User enters search query
2. Frontend sends GET request to `/api/search?query={term}`
3. Backend checks SQLite cache
4. If not cached, queries Rebrickable API `/lego/sets/?search={term}`
5. Results cached and returned
6. Frontend displays set cards with images

**Time:** ~1-2 seconds

**Cached:** Yes (indefinitely)

### Step 2: Set Details

**What Happens:**
1. User clicks on a set
2. Frontend navigates to `/set/{set_num}`
3. Backend fetches detailed info
4. Rebrickable API called for parts count
5. Set metadata displayed

**Time:** ~1-2 seconds

**Cached:** Yes

### Step 3: Configuration

**What Happens:**
1. User sees build plate form
2. Default values loaded from settings
3. User adjusts dimensions if needed
4. Validation ensures 100-500mm range

**Time:** User-controlled

### Step 4: Job Creation

**What Happens:**
1. User clicks "Generate 3MF"
2. POST request to `/api/generate`
3. Job UUID created
4. Job saved to DB (status: pending)
5. Background task started
6. Job ID returned to frontend

**Time:** <1 second

### Step 5: Parts Fetching (Progress: 0-20%)

**What Happens:**
1. Query Rebrickable API: `/lego/sets/{set_num}/parts`
2. Paginate through all parts
3. Filter out spare parts
4. Cache parts list in DB
5. Example: 500 parts found

**Time:** 5-30 seconds (depending on set size)

**API Calls:** 1-5 (paginated)

### Step 6: STL Conversion (Progress: 20-70%)

**What Happens:**
1. For each unique LDraw ID:
   - Check STL cache
   - If cached: Use cached file ✅
   - If not cached:
     - Find LDraw .dat file
     - Run LDView CLI with xvfb
     - LDView resolves sub-files and primitives
     - Exports complete geometry to STL
     - Save to cache
2. Duplicate parts reference same STL
3. Progress updates every ~10 parts

**Time:** 
- Cached: seconds
- Uncached: 1-5 minutes (LDView is fast)

**Files Created:** ~50-500 STL files (proper geometry, 1-10MB each)

### Step 7: ZIP File Creation (Progress: 75-95%)

**What Happens:**
1. Create ZIP archive
2. For each STL file + quantity:
   - Track part counter
   - Add file to ZIP with numbered name
   - Example: `3005_1.stl`, `3005_2.stl`, `3005_3.stl`
3. Write final ZIP file

**Time:** 10-30 seconds

**File Size:** 10MB - 200MB (depending on part count)

**Output:** ZIP file with all individual STL files ready to import

### Step 9: Job Completion

**What Happens:**
1. Update job status: completed
2. Set progress: 100%
3. Save output filename
4. Update timestamp

**Frontend Polling:**
- Checks job status every 2 seconds
- Displays progress bar
- Shows completion notification

### Step 10: Download

**What Happens:**
1. User clicks "Download"
2. GET request to `/api/download/{job_id}`
3. Backend validates job exists and is complete
4. Serves file with proper headers
5. Browser downloads file

**File Name:** `{set_num}.3mf`

## Data Flow Diagram

```
User Browser
     │
     ├─ search → Cache → Brickset API
     │
     ├─ details → Cache → Rebrickable API
     │
     └─ generate
          │
          ├─ Job Queue (SQLite)
          │
          ├─ Parts Fetch → Rebrickable
          │        ↓
          │   Parts Cache (SQLite)
          │
          ├─ STL Convert → LDraw Files
          │        ↓
          │   STL Cache (disk)
          │
          ├─ Arrange → Bin Packing Algorithm
          │
          ├─ 3MF Gen → lib3mf
          │        ↓
          │   Output File (disk)
          │
          └─ Download ← Output File
```

## Caching Strategy

### What's Cached:

1. **Brickset Searches**
   - Location: SQLite `cached_sets`
   - Lifetime: Indefinite
   - Benefit: Instant search results

2. **Set Details**
   - Location: SQLite `cached_sets`
   - Lifetime: Indefinite
   - Benefit: Instant set info

3. **Parts Lists**
   - Location: SQLite `cached_parts`
   - Lifetime: Indefinite
   - Benefit: Skip API calls

4. **STL Files**
   - Location: Disk `cache/stl_cache/`
   - Lifetime: Indefinite
   - Benefit: Skip conversion (90% time savings)

5. **Output 3MF Files**
   - Location: Disk `cache/outputs/`
   - Lifetime: 24 hours
   - Benefit: Allow re-download

### Cache Performance:

**First Generation (No Cache):**
```
Small set (50 parts):    2-3 minutes
Medium set (200 parts):  5-10 minutes
Large set (1000 parts):  15-30 minutes
```

**Subsequent Generations (Cached STLs):**
```
Small set (50 parts):    30 seconds
Medium set (200 parts):  1-2 minutes
Large set (1000 parts):  3-5 minutes
```

## Error Handling

### Possible Failures:

1. **Set Not Found**
   - Cause: Invalid set number or not in Brickset
   - Handled: 404 error returned
   - User Action: Try different set

2. **Parts Not Available**
   - Cause: Set not in Rebrickable database
   - Handled: Error message shown
   - User Action: Try different set

3. **LDraw Part Missing**
   - Cause: Part not in LDraw library
   - Handled: Warning logged, part skipped
   - User Action: None (continues with available parts)

4. **STL Conversion Failed**
   - Cause: Malformed .dat file
   - Handled: Part skipped
   - User Action: None

5. **3MF Generation Failed**
   - Cause: Out of memory, disk space
   - Handled: Job marked as failed
   - User Action: Try smaller set or free space

6. **API Rate Limit**
   - Cause: Too many requests
   - Handled: Error returned
   - User Action: Wait or use cache

## Best Practices

### For Users:

1. **Start Small**
   - Try a small set first (50-100 pieces)
   - Verify your printer settings work
   - Then move to larger sets

2. **Check Your Plate Size**
   - Measure your printer's build plate
   - Account for clips/margins
   - Enter accurate dimensions

3. **Be Patient**
   - Large sets take time (15+ minutes)
   - Don't close browser tab
   - Progress bar shows status

4. **Monitor First Run**
   - LDraw download takes time
   - Check logs: `docker-compose logs -f`
   - Wait for "library downloaded" message

### For Developers:

1. **Cache Everything**
   - Don't re-fetch cached data
   - Use database for API responses
   - Store converted STLs

2. **Handle Errors Gracefully**
   - Log but don't crash
   - Skip problematic parts
   - Provide user feedback

3. **Update Progress**
   - Users want to see progress
   - Update every ~5-10 items
   - Show percentage and step

4. **Clean Up**
   - Delete temp files
   - Archive old jobs
   - Manage cache size

## Troubleshooting Workflow

```
Problem: Generation Failed
    │
    ├─ Check Logs
    │   └─ docker-compose logs brickgen
    │
    ├─ Verify API Keys
    │   └─ cat .env
    │
    ├─ Check Disk Space
    │   └─ df -h
    │
    ├─ Test APIs Manually
    │   ├─ curl Brickset
    │   └─ curl Rebrickable
    │
    └─ Try Different Set
        └─ Start with small set
```

## Performance Optimization

### Tips:
1. Run on SSD for faster file I/O
2. Allocate more RAM for large sets
3. Use cached results when possible
4. Consider CSV download for Rebrickable data
5. Increase Docker memory limit if needed

---

**Ready to start?** See [QUICKSTART.md](QUICKSTART.md)

**Need help?** See [README.md](README.md) troubleshooting section
