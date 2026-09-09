from brickmanager.database.database import Database

def test_database_initialization(tmp_path):
    db = Database(tmp_path / "test.db")
    db.initialize()
    assert db.scalar("SELECT COUNT(*) FROM manufacturers") >= 1
    db.close()
