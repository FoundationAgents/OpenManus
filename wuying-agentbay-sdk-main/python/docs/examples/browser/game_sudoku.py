"""
示例：数独（提取 + 输入框填写）
提取 9×9 棋盘
使用本地算法求解，在页面逐格回填
重点：复杂结构提取；输入框填写
"""

import os
import asyncio
from typing import List, Optional, Tuple

from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams
from agentbay.browser.browser import BrowserOption
from agentbay.browser.browser_agent import ExtractOptions, ActOptions

from playwright.async_api import async_playwright
from pydantic import BaseModel, Field

class SudokuBoard(BaseModel):
    board: List[List[int]] = Field(..., description="9x9 sudoku board, 0 for empty")

class SudokuSolution(BaseModel):
    solution: List[List[int]] = Field(..., description="9x9 solved sudoku board")

def format_board_for_llm(board: List[List[int]]) -> str:
    return "\n".join(["  [" + ", ".join(map(str, row)) + "]" for row in board])

async def main():
    # Get API key from environment variable
    api_key = os.getenv("AGENTBAY_API_KEY")
    if not api_key:
        print("Error: AGENTBAY_API_KEY environment variable not set")
        return

    # Initialize AgentBay client
    print("Initializing AgentBay client...")
    agent_bay = AgentBay(api_key=api_key)

    # Create a session
    print("Creating a new session...")
    params = CreateSessionParams(
        image_id="browser_latest",  # Specify the image ID
    )
    session_result = agent_bay.create(params)

    if session_result.success:
        session = session_result.session
        print(f"Session created with ID: {session.session_id}")

        if await session.browser.initialize_async(BrowserOption()):
            print("Browser initialized successfully")
            endpoint_url = session.browser.get_endpoint_url()
            print("endpoint_url =", endpoint_url)

            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(endpoint_url)
                try:
                    page = await browser.new_page()
                    print("🌐 Navigating to Sudoku site...")
                    url = "https://widget.websudoku.com/"
                    await page.goto(url)
                    await page.wait_for_selector("#puzzle_grid", timeout=10000)

                    # 1. Extract the board
                    success = False
                    while not success:
                        print("📊 Extracting sudoku board...")
                        options = ExtractOptions(
                            instruction="""
Extract the current sudoku board as a 9x9 array. 
Each cell should be a number (1-9) if filled, or 0 if empty.
""",
                            schema=SudokuBoard,
                            use_text_extract=False,
                        )
                        success, board_obj = await session.browser.agent.extract_async(options=options, page=page)
                        if not success:
                            print("❌ Failed to extract sudoku board, retry extracting")
                            await asyncio.sleep(3)
                    board = board_obj.board
                    print(
                        "Current Board:\n" + "\n".join([" ".join(map(str, row)) for row in board])
                    )
                    original_board = [row[:] for row in board]

                    # 2. Solve the sudoku
                    print("🧠 Solving sudoku...")
                    solver = SudokuSolver(board)
                    if solver.solve():
                        solution = solver.get_solution_board()
                        filled_cells = solver.get_filled_cells()
                        print(
                            "Solved Board:\n"
                            + "\n".join([" ".join(map(str, row)) for row in solution])
                        )
                        print(f"Number of cells to fill: {len(filled_cells)}")
                    else:
                        print(
                            "No solution found for this Sudoku puzzle by the local algorithm."
                        )
                        return

                    # 3. Fill the solution (only first row for demo)
                    for row in range(9):
                        for col in range(9):
                            if board[row][col] == 0:
                                input_id = f"f{col}{row}"
                                print(f"Type '{solution[row][col]}' into the cell with id '{input_id}'")
                                input_element = page.locator(f"#f{col}{row}")
                                await input_element.fill(str(solution[row][col]))
                                await asyncio.sleep(0.5)

                    print("✅ Finished! The board has been solved and filled in the browser.")

                except Exception as error:
                    print(f"❌ Error in game loop: {error}")
        else:
            print("Failed to initialize browser")

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

if __name__ == "__main__":
    asyncio.run(main())