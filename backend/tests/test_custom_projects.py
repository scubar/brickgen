"""Tests for custom projects: project parts management and LDraw part index."""
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture()
def db_session():
    """In-memory SQLite session with the full schema created via Alembic."""
    # Use the conftest-configured DATABASE_PATH (temp dir) so init_db() works
    from backend.database import init_db, SessionLocal, Base, engine as default_engine
    init_db()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class TestLDrawPartIndex:
    """Tests for LDraw part indexing and search helpers."""

    def test_parse_dat_description_returns_description(self, tmp_path):
        from backend.api.integrations.ldraw import _parse_dat_description
        dat = tmp_path / "3001.dat"
        dat.write_text("0 Brick  2 x  4\n1 16 0 0 0 1 0 0 0 1 0 0 0 1 stud.dat\n")
        assert _parse_dat_description(dat) == "Brick  2 x  4"

    def test_parse_dat_description_skips_blank_lines(self, tmp_path):
        from backend.api.integrations.ldraw import _parse_dat_description
        dat = tmp_path / "x.dat"
        dat.write_text("\n0 A Nice Part\n")
        assert _parse_dat_description(dat) == "A Nice Part"

    def test_parse_dat_description_returns_none_on_empty(self, tmp_path):
        from backend.api.integrations.ldraw import _parse_dat_description
        dat = tmp_path / "empty.dat"
        dat.write_text("")
        assert _parse_dat_description(dat) is None

    def test_build_and_search_index(self, tmp_path, db_session):
        from backend.api.integrations.ldraw import build_ldraw_part_index, search_ldraw_part_index

        # Create a mini parts directory
        parts_dir = tmp_path / "parts"
        parts_dir.mkdir()
        (parts_dir / "3001.dat").write_text("0 Brick  2 x  4\n")
        (parts_dir / "3002.dat").write_text("0 Brick  2 x  3\n")
        (parts_dir / "3003.dat").write_text("0 Brick  2 x  2\n")

        count = build_ldraw_part_index(db_session, parts_dir=parts_dir)
        assert count == 3

        results = search_ldraw_part_index(db_session, "brick", limit=10)
        assert len(results) == 3
        part_nums = {r["part_num"] for r in results}
        assert "3001" in part_nums

    def test_search_by_part_num(self, tmp_path, db_session):
        from backend.api.integrations.ldraw import build_ldraw_part_index, search_ldraw_part_index

        parts_dir = tmp_path / "parts"
        parts_dir.mkdir()
        (parts_dir / "3001.dat").write_text("0 Brick  2 x  4\n")
        (parts_dir / "99999.dat").write_text("0 Technic Axle 3\n")

        build_ldraw_part_index(db_session, parts_dir=parts_dir)

        results = search_ldraw_part_index(db_session, "3001", limit=10)
        assert len(results) == 1
        assert results[0]["part_num"] == "3001"

    def test_search_empty_query_returns_empty(self, db_session):
        from backend.api.integrations.ldraw import search_ldraw_part_index
        assert search_ldraw_part_index(db_session, "") == []

    def test_search_no_match(self, tmp_path, db_session):
        from backend.api.integrations.ldraw import build_ldraw_part_index, search_ldraw_part_index

        parts_dir = tmp_path / "parts"
        parts_dir.mkdir()
        (parts_dir / "3001.dat").write_text("0 Brick  2 x  4\n")
        build_ldraw_part_index(db_session, parts_dir=parts_dir)

        results = search_ldraw_part_index(db_session, "zzznomatch", limit=10)
        assert results == []


class TestCustomProjectCRUD:
    """Tests for custom project creation and part management (DB layer)."""

    def test_create_custom_project(self, db_session):
        import uuid
        from backend.database import Project

        project = Project(
            id=str(uuid.uuid4()),
            name="My Custom Build",
            is_custom=True,
        )
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        assert project.is_custom is True
        assert project.set_num is None

    def test_add_and_list_project_parts(self, db_session):
        import uuid
        from backend.database import Project, ProjectPart

        project = Project(
            id=str(uuid.uuid4()),
            name="Custom",
            is_custom=True,
        )
        db_session.add(project)
        db_session.commit()

        pp = ProjectPart(
            id=str(uuid.uuid4()),
            project_id=project.id,
            part_num="3001",
            quantity=4,
            color="Red",
            color_rgb="FF0000",
        )
        db_session.add(pp)
        db_session.commit()

        parts = db_session.query(ProjectPart).filter(ProjectPart.project_id == project.id).all()
        assert len(parts) == 1
        assert parts[0].part_num == "3001"
        assert parts[0].quantity == 4

    def test_remove_project_part(self, db_session):
        import uuid
        from backend.database import Project, ProjectPart

        project = Project(id=str(uuid.uuid4()), name="Custom", is_custom=True)
        db_session.add(project)
        db_session.commit()

        pp = ProjectPart(id=str(uuid.uuid4()), project_id=project.id, part_num="3002", quantity=2)
        db_session.add(pp)
        db_session.commit()
        part_id = pp.id

        db_session.delete(pp)
        db_session.commit()

        result = db_session.query(ProjectPart).filter(ProjectPart.id == part_id).first()
        assert result is None

    def test_update_part_quantity(self, db_session):
        import uuid
        from backend.database import Project, ProjectPart

        project = Project(id=str(uuid.uuid4()), name="Custom", is_custom=True)
        db_session.add(project)
        db_session.commit()

        pp = ProjectPart(id=str(uuid.uuid4()), project_id=project.id, part_num="3003", quantity=1)
        db_session.add(pp)
        db_session.commit()

        pp.quantity = 5
        db_session.commit()
        db_session.refresh(pp)
        assert pp.quantity == 5
