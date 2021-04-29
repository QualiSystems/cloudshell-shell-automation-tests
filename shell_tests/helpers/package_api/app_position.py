import random


class AppPositionOnBlueprint:
    DEFAULT_POSITIONS = (
        (600, 240),
        (600, 340),
        (1100, 340),
        (1100, 340),
    )
    MAX_X = 1200
    MAX_Y = 500
    STEP = 20

    def __init__(self):
        self._app_num = 1
        self._used_positions = set()

    def _generate_random(self) -> tuple[int, int]:
        x = random.randrange(0, self.MAX_X, self.STEP)
        y = random.randrange(0, self.MAX_Y, self.STEP)
        return x, y

    def get_random_position(self) -> tuple[int, int]:
        while (position := self._generate_random()) in self._used_positions:
            continue
        return position

    def get_new_position(self) -> tuple[int, int]:
        try:
            position = self.DEFAULT_POSITIONS[self._app_num]
        except IndexError:
            position = self.get_random_position()
        self._used_positions.add(position)
        self._app_num += 1
        return position
