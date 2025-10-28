from typing import List, Tuple, Optional


class SudokuSolver:
    def __init__(self, board: List[List[int]]):
        self.board = [row[:] for row in board]
        self.original_board_state = [row[:] for row in board]

    def _find_empty(self) -> Optional[Tuple[int, int]]:
        """Finds the next empty cell (represented by 0) on the board."""
        for r in range(9):
            for c in range(9):
                if self.board[r][c] == 0:
                    return (r, c)
        return None

    def _is_valid(self, num: int, pos: Tuple[int, int]) -> bool:
        """
        Checks if placing 'num' at 'pos' (row, col) is valid according to Sudoku rules.
        """
        row, col = pos

        for c in range(9):
            if self.board[row][c] == num and col != c:
                return False

        for r in range(9):
            if self.board[r][col] == num and row != r:
                return False

        box_row_start = (row // 3) * 3
        box_col_start = (col // 3) * 3
        for r in range(box_row_start, box_row_start + 3):
            for c in range(box_col_start, box_col_start + 3):
                if self.board[r][c] == num and (r, c) != pos:
                    return False
        return True

    def solve(self) -> bool:
        """
        Solves the Sudoku puzzle using backtracking.
        Returns True if a solution is found, False otherwise.
        The solution is stored in self.board.
        """
        find = self._find_empty()
        if not find:
            return True
        else:
            row, col = find

        for num in range(1, 10):
            if self._is_valid(num, (row, col)):
                self.board[row][col] = num

                if self.solve():
                    return True

                self.board[row][col] = 0
        return False

    def get_solution_board(self) -> List[List[int]]:
        return self.board

    def get_filled_cells(self) -> List[Tuple[int, int, int]]:
        """
        Returns a list of (row, col, value) for cells that were originally empty
        and have now been filled by the solver.
        """
        filled_cells = []
        for r in range(9):
            for c in range(9):
                if self.original_board_state[r][c] == 0 and self.board[r][c] != 0:
                    filled_cells.append((r, c, self.board[r][c]))
        return filled_cells
