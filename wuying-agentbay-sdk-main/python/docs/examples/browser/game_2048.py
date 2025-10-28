"""
示例：2048（提取）
提取棋盘状态
以极小极大算法决策下一步并循环执行
重点：提取与策略结合；按键动作
"""

import os
import asyncio
from typing import List, Literal, Optional, Tuple, Deque
from collections import deque
import random

from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams
from agentbay.browser.browser import BrowserOption
from agentbay.browser.browser_agent import ExtractOptions

from playwright.async_api import async_playwright
from pydantic import BaseModel, Field


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
            page = None

            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(endpoint_url)
                try:
                    page = await browser.new_page()
                    print("🌐 Navigating to 2048...")
                    await page.goto(
                        "https://ovolve.github.io/2048-AI/",
                        wait_until="domcontentloaded",
                        timeout=180000,
                    )
                    print("🌐 Navigated to 2048 done")
                    await page.wait_for_selector(".grid-container", timeout=10000)

                    helper = MiniMax()
                    move_history: Deque[MoveHistoryEntry] = deque(maxlen=3)
                    last_grid_state = None
                    moves_map = {0: "left", 1: "up", 2: "right", 3: "down"}
                    all_possible_moves = ["left", "up", "right", "down"]

                    while True:
                        print("🔄 Game loop iteration...")
                        await asyncio.sleep(0.3)

                        # Get current game state
                        print("📊 Extracting game state...")
                        options = ExtractOptions(
                            instruction="""
Extract the current game state:
1. Score from the score counter
2. All tile values and their positions in the 4x4 grid must be extracted. 
    Each tile's value and position can be obtained from the tile-position-x-y class, where x (1 to 4) is the column and y (1 to 4) is the row.
    For example, tile-position-4-1 means the tile is in column 4, row 1.
    The value of the tile is given by the number in the tile's class.
    For example, <div class='tile tile-2 tile-position-1-4 tile-new'>2</div> means a tile with value 2 at column 1, row 4;
    and <div class='tile tile-2 tile-position-4-1 tile-new'>2</div> means a tile with value 2 at column 4, row 1.
    Empty spaces should be represented as 0 in the grid.
    For instance, if the only tiles present are the two above, the grid should be:[[0, 0, 0, 2], [0, 0, 0, 0], [0, 0, 0, 0], [2, 0, 0, 0]]
3. Highest tile value present
""",
                            schema=GameState,
                            use_text_extract=False,
                        )
                        # Calculate time cost， average time cost, min & max time cost
                        success, gameState = await session.browser.agent.extract_async(
                            options=options, page=page
                        )
                        if success:
                            transposed_grid = transpose_grid(gameState.grid)
                            print(f"transposed grid: {transposed_grid}")
                            print("🤔 Analyzing board for next move...")
                            current_grid_flat = tuple(
                                tile for row in transposed_grid for tile in row
                            )

                            if (
                                last_grid_state is not None
                                and current_grid_flat == last_grid_state
                            ):
                                print(
                                    "Grid has not changed from the last iteration. This might indicate a stuck state."
                                )
                            last_grid_state = current_grid_flat

                            helper.grid = [
                                tile for row in transposed_grid for tile in row
                            ]
                            helper.StartSearch()

                            moves_map = {0: "left", 1: "up", 2: "right", 3: "down"}
                            best_move_str = moves_map.get(
                                helper.best_operation, "no_move"
                            )
                            selected_move = best_move_str
                            print(
                                f"Calculated mini max move: {best_move_str} (explored {helper.node} nodes, max_depth={helper.max_depth})."
                            )
                            current_grid_tuple = tuple(
                                tuple(row) for row in gameState.grid
                            )

                            move_history.append((current_grid_tuple, best_move_str))

                            if len(move_history) == 3:
                                recent_combinations = list(move_history)
                                is_cycling = False
                                if (
                                    all(
                                        item == recent_combinations[0]
                                        for item in recent_combinations
                                    )
                                    and best_move_str != "no_move"
                                ):
                                    is_cycling = True
                                    print(
                                        f"Detected a continuous cycle! The pattern {recent_combinations[0]} repeated {3} times."
                                    )

                                if is_cycling:
                                    print(
                                        "Breaking out of cycle with alternative moves!"
                                    )
                                    move_history.clear()

                                    available_moves = [
                                        m
                                        for m in all_possible_moves
                                        if m != best_move_str and m != "no_move"
                                    ]
                                    if available_moves:
                                        selected_move = random.choice(available_moves)

                            move_key = {
                                "up": "ArrowUp",
                                "down": "ArrowDown",
                                "left": "ArrowLeft",
                                "right": "ArrowRight",
                                "no_move": "Escape",
                            }[selected_move]
                            # }[analysis.move]

                            await page.keyboard.press(move_key)
                        else:
                            print("❌ Failed to extract game state, retry observing")

                except Exception as error:
                    print(f"❌ Error in game loop: {error}")
                    try:
                        if page is not None:
                            is_game_over = await page.evaluate(
                                "() => document.querySelector('.game-over') !== null"
                            )
                            if is_game_over:
                                print("🏁 Game Over!")
                                return

                    except Exception as inner_e:
                        print(f"Could not check game over status: {inner_e}")
                    raise
        else:
            print("Failed to initialize browser")


class GameState(BaseModel):
    score: Optional[int] = Field(
        None, description="Current score from the score counter."
    )
    highestTile: Optional[int] = Field(
        None, description="Highest tile value currently present on the board."
    )
    grid: List[List[int]] = Field(
        ..., description="4x4 grid of tile values (empty spaces as 0)."
    )


class MoveAnalysis(BaseModel):
    move: Literal["up", "down", "left", "right"] = Field(
        ..., description="The best move to make (up/down/left/right)."
    )
    confidence: float = Field(
        ..., description="Confidence score for the recommended move (0.0 to 1.0)."
    )
    reasoning: str = Field(..., description="Detailed reasoning for the chosen move.")


MoveHistoryEntry = Tuple[Tuple[Tuple[int, ...], ...], str]


def transpose_grid(grid: List[List[int]]) -> List[List[int]]:
    if not grid:
        return []

    return list(map(list, zip(*grid)))


def format_grid_for_llm_instruction(grid_data: List[List[int]]) -> str:
    formatted_rows = []
    for i, row in enumerate(grid_data):
        formatted_rows.append(f"row{i+1}: {row}")
    return "\n".join(formatted_rows)


def format_original_grid_for_llm_instruction(grid_data: List[List[int]]) -> str:
    lines = []
    for i, row in enumerate(grid_data):
        lines.append(f"             row{i + 1}: {', '.join(map(str, row))}")
    return "\n".join(lines)


class MiniMax:
    def __init__(self):
        self.best_operation: int = -1
        self.grid: List[int] = [0] * 16
        self.node: int = 0
        self.max_depth: int = 3

    def _move_row_left_single(self, row_in: List[int]) -> Tuple[List[int], int]:
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
        self.node += 1
        if self.node >= 10000 or depth >= self.max_depth:
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
        self.grid[x + y * 4] = v

    def StartSearch(self):
        self.node = 0
        self.max_depth = 3

        while True:
            self.node = 0
            self.Search(self.grid, 0)
            if self.node >= 10000 or self.max_depth >= 8:
                break
            self.max_depth += 1


if __name__ == "__main__":
    asyncio.run(main())
