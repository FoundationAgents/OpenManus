/**
 * Example demonstrating AIBrowser capabilities with AgentBay SDK.
 * This example shows how to use PageUseAgent to run 2048 game, including:
 * - Create AIBrowser session
 * - Use playwright to connect to AIBrowser instance through CDP protocol
 * - Utilize PageUseAgent to run 2048 game
 */

import { AgentBay, CreateSessionParams } from '../../../../typescript/src/agent-bay';
import { BrowserOption, ExtractOptions, ActOptions } from '../../../../typescript/src/browser';
// import { chromium } from 'playwright';

class GameState {
  score?: number;
  highestTile?: number;
  grid: number[][] = [];
}

class MoveAnalysis {
  move?: number;
  confidence: number = 0;
  reasoning: string = "";
}

function transposeGrid(grid: number[][]): number[][] {
  if (!grid || grid.length === 0) {
    return [];
  }
  return grid[0].map((_, colIndex) => grid.map(row => row[colIndex]));
}

function formatGridForLlmInstruction(gridData: number[][]): string {
  const formattedRows: string[] = [];
  for (let i = 0; i < gridData.length; i++) {
    formattedRows.push(`row${i + 1}: [${gridData[i].join(', ')}]`);
  }
  return formattedRows.join('\n');
}

async function main() {
  // Get API key from environment variable
  const apiKey = process.env.AGENTBAY_API_KEY;
  if (!apiKey) {
    console.log("Error: AGENTBAY_API_KEY environment variable not set");
    return;
  }

  // Initialize AgentBay client
  console.log("Initializing AgentBay client...");
  const agentBay = new AgentBay({ apiKey });

  // Create a session
  console.log("Creating a new session...");
  const params: CreateSessionParams = {
    imageId: "browser_latest",
  };
  const sessionResult = await agentBay.create(params);

  if (sessionResult.success) {
    const session = sessionResult.session;
    console.log(`Session created with ID: ${session.sessionId}`);

    if (await session.browser.initializeAsync({} as BrowserOption)) {
      console.log("Browser initialized successfully");
      const endpointUrl = await session.browser.getEndpointUrl();
      console.log("endpoint_url =", endpointUrl);

      // Note: Install playwright with: npm install playwright
      const { chromium } = require('playwright');
      const browser = await chromium.connectOverCDP(endpointUrl);
      let page = null;

      try {
        page = await browser.newPage();
        console.log("🌐 Navigating to 2048...");
        await page.goto("https://ovolve.github.io/2048-AI/", {
          waitUntil: "domcontentloaded",
          timeout: 180000
        });
        console.log("🌐 Navigated to 2048 done");
        await page.waitForSelector(".grid-container", { timeout: 10000 });

        let lastTransposedGrid: number[][] | null = null;
        let transposedGridNotChangedTimes = 0;
        let lastMoveHistory: number[] = [];

        while (true) {
          console.log("🔄 Game loop iteration...");
          await new Promise(resolve => setTimeout(resolve, 300));

          // Get current game state
          console.log("📊 Extracting game state...");
          const gameStateOptions: ExtractOptions<GameState> = {
            instruction: `
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
            `,
            schema: GameState,
            use_text_extract: false

          };

          const [success, gameStates] = await session.browser.agent.extract(gameStateOptions, page);
          if (success && gameStates.length > 0) {
            const gameState = gameStates[0];
            const transposedGrid = transposeGrid(gameState.grid);
            console.log(`transposed grid: ${JSON.stringify(transposedGrid)}`);
            console.log(`gameState: ${JSON.stringify(gameState)}`);
            const gridInstruction = formatGridForLlmInstruction(transposedGrid);

            if (lastTransposedGrid !== null && JSON.stringify(transposedGrid) === JSON.stringify(lastTransposedGrid)) {
              transposedGridNotChangedTimes += 1;
            } else {
              transposedGridNotChangedTimes = 0;
              lastMoveHistory = [];
            }
            lastTransposedGrid = transposedGrid;

            let instructionStr = `
              Based on the current game state:
              - Score: ${gameState.score}
              - Highest tile: ${gameState.highestTile}
              - Grid: This is a 4x4 matrix ordered by row (top to bottom) and column (left to right). The rows are stacked vertically, and tiles can move vertically between rows or horizontally between columns:${gridInstruction}
              What is the best move (up/down/left/right)? Consider:
              1. Keeping high value tiles in corners (bottom left, bottom right, top left, top right)
              2. Maintaining a clear path to merge tiles
              3. Avoiding moves that could block merges
              4. Avoiding moves that merge no blocks as possible
              5. Only adjacent tiles of the same value can merge
              6. Making a move will move all tiles in that direction until they hit a tile of a different value or the edge of the board
              7. Tiles cannot move past the edge of the board
              8. Each move must move at least one tile
            `;

            if (transposedGridNotChangedTimes >= 1) {
              instructionStr += `
                9. Do not generate move value in ${JSON.stringify(lastMoveHistory)}
                10. If last move value ${lastMoveHistory[lastMoveHistory.length - 1]} moves up or down, then generate move value with left or right direction, otherwise generate move value with up or down direction
              `;
            }

            const nextMoveOptions: ExtractOptions<MoveAnalysis> = {
              instruction: instructionStr,
              schema: MoveAnalysis,
              use_text_extract: false
            };

            const [moveSuccess, nextMove] = await session.browser.agent.extract(nextMoveOptions, page);
            let selectedMove = 4; // Default to no move

            if (moveSuccess && nextMove.length > 0) {
              selectedMove = nextMove[0].move ?? 4;
            } else {
              console.log("❌ Failed to extract next move, retry observing");
              continue;
            }

            lastMoveHistory.push(selectedMove);

            const moveKeyMap: { [key: number]: string } = {
              0: "ArrowUp",
              1: "ArrowDown",
              2: "ArrowLeft",
              3: "ArrowRight",
              4: "Escape",
            };

            const moveKey = moveKeyMap[selectedMove];
            await page.keyboard.press(moveKey);
          } else {
            console.log("❌ Failed to extract game state, retry observing");
          }
        }
      } catch (error) {
        console.log(`❌ Error in game loop: ${error}`);
        try {
          if (page !== null) {
            const isGameOver = await page.evaluate(
              "() => document.querySelector('.game-over') !== null"
            );
            if (isGameOver) {
              console.log("🏁 Game Over!");
              return;
            }
          }
        } catch (innerError) {
          console.log(`Could not check game over status: ${innerError}`);
        }
        throw error;
      }
    } else {
      console.log("Failed to initialize browser");
    }
  }
}

if (require.main === module) {
  main().catch(console.error);
}
