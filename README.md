# BrickGen - LEGO 3D Printing Generator

BrickGen is a self-hosted web application that generates print-ready STL files for LEGO sets. Search for any set via Rebrickable, and it automatically fetches the parts list with LDraw IDs, converts each brick to STL format using the official LDView tool, and generates a ZIP file with all individual STL files ready for your slicer.

## Features

- **Set Search**: Search LEGO sets by name or number using the Rebrickable API
- **Automatic Part Conversion**: Converts LDraw .dat files to STL using official LDView tool
- **ZIP Download**: All individual STL files packaged for easy import to any slicer
- **Part Numbering**: Duplicate parts numbered (3007_1.stl, 3007_2.stl, etc.)
- **Job Tracking**: Background processing with real-time progress updates
- **Caching**: Aggressive caching of API responses and converted STLs for speed
- **100% Success Rate**: LDView properly handles all LDraw parts including sub-files

## Technology Stack

**Backend:**
- Python 3.11+ with FastAPI
- SQLite for caching and job tracking
- LDView CLI tool for LDraw → STL conversion
- LDraw parts library (10,000+ LEGO parts)
- Key dependencies: `fastapi`, `uvicorn`, `aiohttp`, `sqlalchemy`, `pydantic`, `numpy`, `numpy-stl`

**Frontend:**
- React 18 with Vite
- TailwindCSS for styling
- React Router for navigation

**Infrastructure:**
- Single Docker container (multi-stage build)
- Docker Compose for local deployment
- Kubernetes-ready with health checks

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Rebrickable API key from: [Rebrickable](https://rebrickable.com/api/)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd brickgen
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your Rebrickable API key
   ```

3. **Build and run with Docker Compose**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   
   Open your browser to http://localhost:8000

### First Run

On first startup, the application will automatically download the LDraw parts library (~100MB). This may take a few minutes. You can monitor progress in the logs:

```bash
docker-compose logs -f brickgen
```

## Usage

1. **Search for a LEGO set** by name or number
2. **Select a set** from the search results
3. **Configure build plate dimensions** (defaults to 220x220mm)
4. **Click "Generate 3MF File"** and wait for processing
5. **Download** the generated 3MF file when complete
6. **Slice** the 3MF file in your preferred slicer (PrusaSlicer, Cura, etc.)
7. **Print!**

### 3MF and slicers

- **Multiple build plates**: If parts don’t fit on one plate, Brickgen adds more logical plates (stacked in Y) in the same 3MF so everything is packed.
- **Colors**: Part colors from Rebrickable are written into the 3MF (Materials Extension) so slicers can show colored parts.
- **Bambu Studio**: When you open a 3MF that wasn’t created by Bambu Lab, Bambu may show “load geometry data and color data only” and can ignore placement, so parts may appear stacked in the center. Use the slicer’s own “Arrange” or placement tools if needed. Other slicers that support 3MF Core (e.g. PrusaSlicer, Cura) should respect the packed placement.

## Configuration

### Build Plate Defaults

Edit `.env` file or use the Settings page in the UI:

```env
DEFAULT_PLATE_WIDTH=220    # mm
DEFAULT_PLATE_DEPTH=220    # mm
DEFAULT_PLATE_HEIGHT=250   # mm
PART_SPACING=2             # mm spacing between parts
```

### Common Printer Presets


- **Bambu Lab X1 Carbon**: 250mm^3
- **Bambu Lab A1 Mini**: 180mm^3

## Development

### Running Locally (without Docker)

**Prerequisites:**
```bash
# Install pipenv if not already installed
pip install --user pipenv
```

**Backend:** (run from project root so the `backend` package resolves)
```bash
cd backend
pipenv install --dev
cd ..
pipenv run --path backend uvicorn backend.main:app --reload
```

Or activate the virtual environment from project root:
```bash
pipenv shell --path backend
# from project root (brickgen/)
uvicorn backend.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### Project Structure

```
brickgen/
├── backend/
│   ├── api/
│   │   ├── integrations/    # API clients (Rebrickable, LDraw)
│   │   └── routes/          # FastAPI routes
│   ├── core/                # Core processing logic
│   │   ├── ldview_converter.py
│   │   ├── stl_processing.py
│   │   ├── stl_orientation.py
│   │   ├── stl_render.py
│   │   └── threemf_generator.py
│   ├── models/              # Pydantic schemas
│   ├── config.py            # Configuration
│   ├── database.py          # SQLAlchemy models
│   └── main.py              # FastAPI app
├── frontend/
│   └── src/
│       ├── components/      # React components
│       ├── pages/           # Page components
│       └── App.jsx
├── Dockerfile               # Multi-stage build
├── docker-compose.yml
└── README.md
```

## API Endpoints

- `GET /api/search?query={name}` - Search LEGO sets
- `GET /api/sets/{set_num}` - Get set details
- `POST /api/generate` - Generate 3MF/STL (legacy)
- `GET /api/projects` - List projects
- `POST /api/projects` - Create project
- `GET /api/projects/{project_id}/jobs` - List jobs for a project
- `POST /api/projects/{project_id}/jobs` - Create job (generate 3MF/STL)
- `GET /api/jobs/{job_id}` - Check job status
- `GET /api/download/{job_id}` - Download 3MF or ZIP file
- `GET /api/settings` - Get settings
- `POST /api/settings` - Update settings
- `GET /health` - Health check

## Troubleshooting

### LDraw Library Download Fails

The application automatically downloads the LDraw library on first run. If it fails:

1. Check your internet connection
2. Manually download from https://library.ldraw.org/library/updates/complete.zip
3. Extract to `./data/ldraw/` directory
4. Restart the application

### No Parts Found for Set

Some sets may not be available in Rebrickable's database. Try:

1. Ensuring the set number is correct (e.g., "75192-1")
2. Checking if the set exists on https://rebrickable.com

### STL Conversion Failures

Not all LDraw parts may convert successfully. The application will:

1. Log warnings for failed conversions
2. Continue processing available parts
3. Generate 3MF with successfully converted parts

## Roadmap

### Phase 1 - Initial MVP (Done)
- Provide a simple web interface that can be used to go from Rebrickable set to a zip file containing part STLs and/or 3mf file with part color info and bin packed placement.

### Phase 2 - Enhancements
- Allow the import of full LDraw mpd files.

- Support external postgres database.

- Quick import of users saved MOCs, Sets and Parts from Rebrickable.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

MIT License - see LICENSE file for details

## Acknowledgments

- [LDraw](https://www.ldraw.org/) - LEGO CAD parts library
- [LDView](https://github.com/tcobbs/ldview) - LDraw viewer and STL export (included under its MIT license option)
- [Rebrickable](https://rebrickable.com/) - LEGO set search and parts inventory
- [lib3mf](https://github.com/3MFConsortium/lib3mf) - 3MF file format library

## Disclaimer

LEGO® is a trademark of the LEGO Group, which does not sponsor, authorize, or endorse this application. This tool is for personal use only. Please respect LEGO's intellectual property rights.
