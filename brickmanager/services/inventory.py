class InventoryService:
    def __init__(self, database):
        self.database = database

    def assign_brick(self, brick_id):
        raise NotImplementedError("Inventarzuordnung kommt in v0.7.")
