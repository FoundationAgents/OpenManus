from typing import List, Tuple


class MiniMax:
    def __init__(self):
        self.best_operation: int = -1
        self.grid: List[int] = [0] * 16
        self.node: int = 0
        self.max_depth: int = 3

    def _move_row_left_single(self, row_in: List[int]) -> Tuple[List[int], int]:
        """
        Helper function to simulate moving a single 1D row (4 elements) to the left.
        Handles compaction and merging.
        Returns the new row and the score obtained from merges.
        """
        row = row_in[:]
        compacted_row = []
        for val in row:
            if val != 0:
                compacted_row.append(val)

        processed_row = []
        score = 0
        idx_compacted = 0

        while idx_compacted < len(compacted_row):
            current_val = compacted_row[idx_compacted]
            if (
                idx_compacted + 1 < len(compacted_row)
                and current_val == compacted_row[idx_compacted + 1]
            ):
                processed_row.append(current_val * 2)
                score += current_val * 2
                idx_compacted += 2
            else:
                processed_row.append(current_val)
                idx_compacted += 1

        while len(processed_row) < 4:
            processed_row.append(0)

        return processed_row, score

    def MoveLeft(self, s_in: List[int]) -> Tuple[List[int], int]:
        """
        Simulates the 'Move Left' operation on the 1D grid.
        Returns the new 1D grid and the total score from merges.
        """
        s = s_in[:]
        total_score = 0
        new_grid_1d = [0] * 16

        for row_idx in range(4):
            start_idx = row_idx * 4
            row_slice = s[start_idx : start_idx + 4]

            moved_row, row_score = self._move_row_left_single(row_slice)

            for i in range(4):
                new_grid_1d[start_idx + i] = moved_row[i]
            total_score += row_score

        return [new_grid_1d, total_score]

    def Rotate(self, s: List[int]) -> List[int]:
        """
        Rotates the 1D grid 90 degrees clockwise.
        This is crucial because MoveLeft is only implemented for one direction.
        """
        return [
            s[12],
            s[8],
            s[4],
            s[0],
            s[13],
            s[9],
            s[5],
            s[1],
            s[14],
            s[10],
            s[6],
            s[2],
            s[15],
            s[11],
            s[7],
            s[3],
        ]

    def Estimate(self, s: List[int]) -> float:
        """
        Heuristic function to estimate the value of a grid state.
        Calculates smoothness (differences between adjacent tiles) and sum.
        """
        diff = 0
        total_sum = 0
        for i in range(16):
            total_sum += s[i]
            if i % 4 != 3:
                diff += abs(s[i] - s[i + 1])
            if i < 12:
                diff += abs(s[i] - s[i + 4])
        return (total_sum * 4 - diff) * 2.0

    def Search(self, s_in: List[int], depth: int) -> float:
        """
        The core recursive minimax search function.
        Explores possible moves and new tile placements.
        """
        self.node += 1
        if depth >= self.max_depth:
            return self.Estimate(s_in)

        best_score = -float("inf")

        s_current_direction = s_in[:]

        for i in range(4):
            moved_grid, move_score = self.MoveLeft(s_current_direction)

            grid_changed = False
            for j in range(16):
                if moved_grid[j] != s_current_direction[j]:
                    grid_changed = True
                    break

            if grid_changed:
                temp_expected_value = 0.0
                empty_slots_indices = [
                    idx for idx, val in enumerate(moved_grid) if val == 0
                ]

                if empty_slots_indices:
                    for slot_idx in empty_slots_indices:
                        moved_grid[slot_idx] = 2
                        temp_expected_value += self.Search(moved_grid, depth + 1) * 0.9

                        moved_grid[slot_idx] = 4
                        temp_expected_value += self.Search(moved_grid, depth + 1) * 0.1

                        moved_grid[slot_idx] = 0
                    temp_expected_value /= len(empty_slots_indices)
                else:
                    temp_expected_value = -1e20

                current_move_total_value = move_score + temp_expected_value

                if current_move_total_value > best_score:
                    best_score = current_move_total_value
                    if depth == 0:
                        self.best_operation = i
            else:
                if depth == 0:
                    current_move_total_value = -1e20
                    if current_move_total_value > best_score:
                        best_score = current_move_total_value
                        self.best_operation = i

            if i != 3:
                s_current_direction = self.Rotate(s_current_direction)

        return best_score if best_score != -float("inf") else -1e20

    def SetTile(self, x: int, y: int, v: int):
        """Sets a tile value in the 1D grid representation."""
        # x is column (0-3), y is row (0-3)
        self.grid[x + y * 4] = v

    def StartSearch(self):
        """
        Initiates the search for the best move.
        Dynamically increases search depth until a certain node count is reached.
        """
        self.node = 0
        self.max_depth = 3

        while True:
            self.node = 0
            self.Search(self.grid, 0)

            # Check termination conditions
            if self.node >= 10000 or self.max_depth >= 8:
                break

            self.max_depth += 1
