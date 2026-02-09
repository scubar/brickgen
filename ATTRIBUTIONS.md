# Attributions

BrickGen uses the following third-party software, data, and services. This file is the canonical list for license compliance and attribution.

## External services and data

- **LDraw** — LEGO part library and file format. Parts library downloaded from [library.ldraw.org](https://library.ldraw.org/). Used under the [Creative Commons Attribution License (CCAL)](https://ldraw.org/docs-main/licenses/legal-info.html). Attribution required when redistributing LDraw parts.

- **LDView** — LDraw viewer and STL export (CLI invoked by BrickGen). [https://github.com/tcobbs/ldview](https://github.com/tcobbs/ldview). Dual-licensed under GPL-2.0 or MIT; BrickGen distributes LDView under its **MIT license option**. Copyright and license remain with LDView’s authors.

- **Rebrickable API** — LEGO set search and parts inventory data. [https://rebrickable.com/api/](https://rebrickable.com/api/). Use subject to [Rebrickable’s API terms](https://rebrickable.com/api/).

## Key software dependencies

### Backend (Python)

| Project     | URL / description                    | License |
|------------|---------------------------------------|--------|
| FastAPI    | https://fastapi.tiangolo.com/         | MIT    |
| Uvicorn    | https://www.uvicorn.org/              | BSD    |
| Pydantic   | https://docs.pydantic.dev/            | MIT    |
| SQLAlchemy | https://www.sqlalchemy.org/           | MIT    |
| aiohttp    | https://docs.aiohttp.org/             | Apache-2.0 |
| NumPy      | https://numpy.org/                    | BSD    |
| Matplotlib | https://matplotlib.org/               | PSF-based |
| numpy-stl   | https://github.com/WoLpH/numpy-stl    | BSD    |

### Frontend

| Project     | URL / description           | License |
|------------|-----------------------------|--------|
| React      | https://react.dev/          | MIT    |
| React Router | https://reactrouter.com/  | MIT    |
| Vite       | https://vitejs.dev/         | MIT    |
| TailwindCSS | https://tailwindcss.com/   | MIT    |

For the full list of dependencies and versions, see `backend/Pipfile` (and `Pipfile.lock`) and `frontend/package.json`.
