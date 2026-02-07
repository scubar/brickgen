# BrickGen Architecture

This document describes the architecture and design decisions for BrickGen.

## System Overview

BrickGen is a full-stack web application that converts LEGO sets into 3D-printable files.

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │ HTTP
       ▼
┌─────────────────────────────────────┐
│        React Frontend (SPA)         │
│  - Search UI                        │
│  - Set Detail                       │
│  - Job Status Tracking              │
└──────┬──────────────────────────────┘
       │ REST API
       ▼
┌─────────────────────────────────────┐
│       FastAPI Backend               │
│  ┌─────────────────────────────┐   │
│  │  API Routes Layer           │   │
│  │  - Search, Generate, etc.   │   │
│  └────┬────────────────────────┘   │
│       │                             │
│  ┌────▼─────────────────────────┐  │
│  │  Integration Layer           │  │
│  │  - Rebrickable Client        │  │
│  │  - LDraw Manager             │  │
│  └────┬─────────────────────────┘  │
│       │                             │
│  ┌────▼─────────────────────────┐  │
│  │  Core Processing             │  │
│  │  - LDView CLI Wrapper        │  │
│  │  - STL Caching               │  │
│  │  - ZIP Generator             │  │
│  └──────────────────────────────┘  │
│                                     │
│  ┌──────────────────────────────┐  │
│  │  Data Layer                  │  │
│  │  - SQLite (cache, jobs)      │  │
│  │  - File Storage (STL, ZIP)   │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
       │                    
       ▼                    
┌─────────────┐      
│ Rebrickable │      
│     API     │      
└─────────────┘
```

## Component Architecture

### Frontend (React)

**Technology**: React 18 + Vite + TailwindCSS

**Structure**:
```
frontend/src/
├── components/
│   └── Header.jsx          # Navigation header
├── pages/
│   ├── SearchPage.jsx      # Set search (Rebrickable)
│   ├── SetDetailPage.jsx   # Set details & ZIP generation
│   └── SettingsPage.jsx    # Printer presets
├── App.jsx                 # Router configuration
└── main.jsx               # Entry point
```

**Key Features**:
- Client-side routing with React Router
- Real-time job status polling
- Responsive design with TailwindCSS
- Form validation and error handling

### Backend (FastAPI)

**Technology**: Python 3.11 + FastAPI + SQLAlchemy

**Structure**:
```
backend/
├── api/
│   ├── integrations/       # External API clients
│   │   ├── rebrickable.py # Rebrickable API wrapper (search + parts)
│   │   └── ldraw.py       # LDraw library manager
│   └── routes/            # REST endpoints
│       ├── search.py      # Set search (Rebrickable)
│       ├── generate.py    # ZIP generation
│       ├── download.py    # File download
│       └── settings.py    # Configuration
├── core/                  # Business logic
│   ├── ldview_converter.py # LDView CLI wrapper
│   └── stl_processing.py  # STL caching
├── models/
│   └── schemas.py         # Pydantic models
├── config.py              # Configuration management
├── database.py            # SQLAlchemy models
└── main.py               # FastAPI application
```

## Data Flow

### 1. Set Search Flow

```
User Input
    ↓
Search API
    ↓
Brickset API ──→ Cache (SQLite)
    ↓
Return Results
```

### 2. 3MF Generation Flow

```
Generate Request
    ↓
Create Job (SQLite)
    ↓
Background Task Started
    │
    ├─→ Download LDraw Library (first run)
    │
    ├─→ Fetch Parts List (Rebrickable)
    │       ↓
    │   Cache in SQLite
    │
    ├─→ Convert Parts to STL
    │       ├─→ Check STL Cache
    │       ├─→ Parse LDraw .dat files
    │       ├─→ Convert to STL mesh
    │       └─→ Cache STL files
    │
    ├─→ Arrange on Build Plate
    │       ├─→ Calculate part dimensions
    │       ├─→ Run bin-packing algorithm
    │       └─→ Position parts
    │
    └─→ Generate 3MF File
            ├─→ Combine meshes
            ├─→ Create 3MF document
            └─→ Save to output directory
                    ↓
            Update Job Status
                    ↓
            User Downloads File
```

## Database Schema

### SQLite Tables

**cached_sets**
- `id` (PK)
- `set_num` (unique)
- `name`, `year`, `theme`, `subtheme`, `pieces`
- `image_url`
- `data` (JSON blob)
- `created_at`, `updated_at`

**cached_parts**
- `id` (PK)
- `set_num` (index)
- `parts_data` (JSON blob)
- `created_at`, `updated_at`

**jobs**
- `id` (PK, UUID)
- `set_num`
- `status` (pending, processing, completed, failed)
- `progress` (0-100)
- `plate_width`, `plate_depth`
- `error_message`
- `output_file`
- `created_at`, `updated_at`

**stl_cache**
- `id` (PK)
- `part_num` (unique)
- `file_path`
- `file_size`
- `created_at`

## Algorithms

### LDraw to STL Conversion

**Input**: LDraw .dat file (text format with geometry commands)

**Process**:
1. Parse file line by line
2. Extract triangle (type 3) and quad (type 4) definitions
3. Convert quads to triangles
4. Create vertex and face arrays
5. Scale from LDraw units (LDU) to millimeters (0.4mm/LDU)
6. Create trimesh object
7. Clean mesh (remove duplicates, degenerate faces)
8. Export to STL format

**Output**: Binary STL file

### Build Plate Arrangement (Bin Packing)

**Algorithm**: Greedy 2D bin packing

**Input**: 
- List of STL meshes
- Build plate dimensions (width × depth)
- Part spacing

**Process**:
1. Calculate 2D footprint (XY bounds) for each part
2. Sort parts by area (largest first)
3. For each part:
   - Try positions on a grid (5mm spacing)
   - Check if position is within plate bounds
   - Check for collisions with placed parts
   - Place part at first valid position
   - Mark area as occupied
4. Return list of placed parts with positions

**Output**: List of (mesh, position) tuples

**Optimization**: 
- Grid search is fast but not optimal
- Future: Use more sophisticated algorithms (guillotine, skyline, etc.)

### 3MF File Generation

**Input**: List of positioned meshes

**Process**:
1. Create 3MF model object (lib3mf)
2. For each placed part:
   - Export mesh to temporary STL
   - Add to 3MF model
   - Apply position transformation
3. Write 3MF file

**Fallback**: If lib3mf unavailable, combine meshes into single STL

## Caching Strategy

### API Response Caching

- **Brickset** searches: Cache indefinitely (sets don't change)
- **Rebrickable** parts: Cache indefinitely
- **Purpose**: Reduce API calls, improve performance

### STL File Caching

- **Location**: `cache/stl_cache/`
- **Key**: Part number
- **Lifetime**: Indefinite (LDraw parts don't change)
- **Size**: ~1-5MB per part
- **Purpose**: Avoid re-parsing LDraw files

### Job Results Caching

- **Location**: `cache/outputs/`
- **Lifetime**: 24 hours (configurable)
- **Purpose**: Allow multiple downloads, debugging

## Performance Considerations

### Bottlenecks

1. **LDraw Library Download**: ~100MB, one-time
2. **STL Conversion**: CPU-intensive, cached
3. **Large Sets**: 1000+ parts can take 10-15 minutes

### Optimizations

1. **Aggressive Caching**: All conversions cached
2. **Background Processing**: Non-blocking job queue
3. **Progress Updates**: Real-time status for user feedback
4. **Parallel Conversion**: Future enhancement

## Deployment

### Single Container Architecture

**Multi-stage Build**:
1. **Stage 1**: Build React frontend → static files
2. **Stage 2**: Python runtime + static files

**Advantages**:
- Simple deployment (one container)
- FastAPI serves both API and frontend
- Reduced resource usage
- Easy to scale

### Volume Mounts

- **ldraw-data**: LDraw parts library (read-mostly)
- **stl-cache**: Converted STL files (read-write)
- **database**: SQLite database (read-write)

### Health Checks

**Endpoint**: `GET /health`

**Checks**:
- Application is running
- LDraw library is available
- Database is accessible

**Used by**:
- Docker healthcheck
- Kubernetes liveness/readiness probes
- Load balancers

## Security Considerations

### API Keys

- Stored in environment variables
- Never committed to Git
- Validated on startup

### Input Validation

- Pydantic schemas validate all inputs
- Build plate dimensions: 100-500mm
- Part spacing: 1-10mm
- Set numbers: alphanumeric only

### File System Access

- All file operations within mounted volumes
- No user-provided file paths
- Output files served with safe filenames

## Future Enhancements

### Phase 2
- Better STL quality (high-res LDraw primitives)
- Improved arrangement (advanced algorithms)
- Error recovery and retry logic

### Phase 3
- 3D preview (Three.js)
- Multi-plate support
- Color information
- Print time estimation

### Phase 4
- Kubernetes manifests
- Horizontal scaling (PostgreSQL + Redis)
- WebSocket for real-time updates
- User authentication

## Technology Decisions

### Why FastAPI?
- Modern, fast, async-capable
- Automatic API documentation
- Great type support
- Easy background tasks

### Why React?
- Component reusability
- Rich ecosystem
- Good performance
- Simple state management

### Why SQLite?
- No separate database server
- Perfect for single-user
- Easy backup
- Fast for reads

### Why lib3mf?
- Industry standard
- Official 3MF Consortium library
- Proper metadata support
- Better than manual XML

### Why Single Container?
- Simpler deployment
- Lower resource usage
- Easier to manage
- Still scales with K8s

## Monitoring and Debugging

### Logs

**Access logs**:
```bash
docker-compose logs -f brickgen
```

**Log Levels**:
- INFO: Normal operations
- WARNING: Non-critical issues
- ERROR: Failures, exceptions

### Metrics to Monitor

- Job success/failure rate
- Average processing time per part
- Cache hit rate
- API error rate
- Disk usage (STL cache)

### Common Issues

1. **Out of disk space**: Clean old cache files
2. **API rate limits**: Reduce requests, use CSV data
3. **Missing parts**: Not all parts in LDraw library
4. **Memory usage**: Large sets use more RAM

## Testing Strategy

### Unit Tests
- Core algorithms (parsing, packing)
- API clients (mocked responses)
- Data models (validation)

### Integration Tests
- Full generation workflow
- API endpoints
- Database operations

### End-to-End Tests
- Browser automation
- Complete user workflows
- Error scenarios

## References

- [LDraw File Format](https://www.ldraw.org/article/218.html)
- [3MF Specification](https://3mf.io/specification/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Trimesh Documentation](https://trimsh.org/)
