from brickmanager.database.database import Database
from brickmanager.services.set_inventory import (
    PartAssignmentService,
    RebrickableSetClient,
    SetInventoryService,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSetSession:
    def __init__(self):
        self.calls = []

    def get(self, url, *args, **kwargs):
        self.calls.append((url, kwargs))
        if url.endswith("sets/10303-1/"):
            return FakeResponse({"set_num": "10303-1", "name": "Loop Coaster"})
        if url.endswith("parts/"):
            return FakeResponse(
                {
                    "results": [
                        {
                            "part": {
                                "part_num": "3001",
                                "part_img_url": "https://example.invalid/3001.jpg",
                                "external_ids": {"LEGO": ["3001"]},
                            },
                            "color": {"id": 4, "name": "Red"},
                            "element_id": "300121",
                            "quantity": 4,
                        }
                    ],
                    "next": "https://example.invalid/next-page",
                }
            )
        return FakeResponse(
            {
                "results": [
                    {
                        "part": {"part_num": "3001"},
                        "color": {"id": 7, "name": "Blue"},
                        "quantity": 2,
                    }
                ],
                "next": None,
            }
        )


def test_rebrickable_set_import_loads_paginated_part_color_inventory(tmp_path):
    database = Database(tmp_path / "sets.db")
    database.initialize()
    session = FakeSetSession()
    service = SetInventoryService(
        database, client=RebrickableSetClient(session=session)
    )

    result = service.add_set("10303", api_key="secret")

    assert result["added"] is True
    assert [
        (item["part_num"], item["color_id"])
        for item in service.get_inventory("10303-1")
    ] == [
        ("3001", 4),
        ("3001", 7),
    ]
    assert session.calls[0][1]["headers"] == {"Authorization": "key secret"}
    database.close()


def test_add_set_persists_each_part_color_variant(tmp_path):
    database = Database(tmp_path / "sets.db")
    database.initialize()
    service = SetInventoryService(database)

    added = service.store_set(
        {
            "set_num": "10303-1",
            "name": "Loop Coaster",
            "set_img_url": "https://example.invalid/set.jpg",
        },
        [
            {
                "part_num": "3001",
                "color_id": 4,
                "color_name": "Red",
                "quantity": 4,
                "part_image": "https://example.invalid/red.jpg",
            },
            {
                "part_num": "3001",
                "color_id": 7,
                "color_name": "Blue",
                "quantity": 2,
            },
        ],
    )

    assert added["added"] is True
    assert service.store_set({"set_num": "10303-1", "name": "Loop Coaster"}, []) == {
        "added": False,
        "reason": "duplicate",
    }
    stored_set = service.list_sets()[0]
    assert (stored_set["quantity_required"], stored_set["quantity_found"]) == (6, 0)
    inventory = service.get_inventory("10303-1")
    assert [(item["part_num"], item["color_id"]) for item in inventory] == [
        ("3001", 4),
        ("3001", 7),
    ]
    database.close()


def test_assignment_uses_stored_priority_and_part_color_pair(tmp_path):
    database = Database(tmp_path / "sets.db")
    database.initialize()
    inventory = SetInventoryService(database)
    inventory.store_set(
        {"set_num": "A-1", "name": "Set A"},
        [{"part_num": "3001", "color_id": 4, "color_name": "Red", "quantity": 1}],
    )
    inventory.store_set(
        {"set_num": "B-1", "name": "Set B"},
        [{"part_num": "3001", "color_id": 4, "color_name": "Red", "quantity": 2}],
    )
    assignments = PartAssignmentService(database)

    first = assignments.assign_part("3001", 4)
    second = assignments.assign_part("3001", 4)
    wrong_color = assignments.assign_part("3001", 7)

    assert first["set_num"] == "A-1"
    assert second["set_num"] == "B-1"
    assert wrong_color == {"assigned": False, "set_id": None, "reason": "no_demand"}
    assert inventory.get_inventory("B-1")[0]["quantity_found"] == 1
    database.close()


def test_reorder_and_undo_assignment_are_persistent(tmp_path):
    path = tmp_path / "sets.db"
    database = Database(path)
    database.initialize()
    inventory = SetInventoryService(database)
    for set_num in ("A-1", "B-1", "C-1"):
        inventory.store_set(
            {"set_num": set_num, "name": set_num},
            [{"part_num": "3001", "color_id": 4, "color_name": "Red", "quantity": 1}],
        )
    inventory.set_priority_order(["C-1", "A-1", "B-1"])
    assignment = PartAssignmentService(database).assign_part("3001", 4)

    assert assignment["set_num"] == "C-1"
    assert PartAssignmentService(database).undo_last_assignment()["undone"] is True
    database.close()

    restarted = Database(path)
    restarted.initialize()
    assert [item["set_num"] for item in SetInventoryService(restarted).list_sets()] == [
        "C-1",
        "A-1",
        "B-1",
    ]
    assert SetInventoryService(restarted).get_inventory("C-1")[0]["quantity_found"] == 0
    restarted.close()


def test_inventory_is_sorted_by_color_and_found_quantity_can_be_adjusted(tmp_path):
    database = Database(tmp_path / "sets.db")
    database.initialize()
    service = SetInventoryService(database)
    service.store_set(
        {"set_num": "A-1", "name": "Set A"},
        [
            {"part_num": "3002", "color_id": 7, "color_name": "Blue", "quantity": 1},
            {"part_num": "3001", "color_id": 4, "color_name": "Red", "quantity": 2},
        ],
    )

    items = service.get_inventory("A-1")
    increased = service.adjust_quantity_found(items[0]["id"], 1)
    capped = service.adjust_quantity_found(items[0]["id"], 5)
    decreased = service.adjust_quantity_found(items[0]["id"], -1)

    assert [item["color_id"] for item in items] == [4, 7]
    assert increased["quantity_found"] == 1
    assert capped["quantity_found"] == 2
    assert decreased["quantity_found"] == 1
    database.close()


def test_delete_set_removes_its_inventory(tmp_path):
    database = Database(tmp_path / "sets.db")
    database.initialize()
    service = SetInventoryService(database)
    service.store_set(
        {"set_num": "A-1", "name": "Set A"},
        [{"part_num": "3001", "color_id": 4, "color_name": "Red", "quantity": 1}],
    )

    assert service.delete_set("A-1") == {"deleted": True}
    assert service.list_sets() == []
    assert service.get_inventory("A-1") == []
    database.close()
