/**
 * Example demonstrating AIBrowser capabilities with AgentBay SDK.
 * This example shows how to use PageUseAgent to run sudoku game, including:
 * - Create AIBrowser session
 * - Use playwright to connect to AIBrowser instance through CDP protocol
 * - Utilize PageUseAgent to run sudoku game
 */

import { AgentBay, CreateSessionParams,BrowserOption, ExtractOptions, ActOptions } from 'wuying-agentbay-sdk';

import { chromium } from 'playwright';

class SudokuBoard {
  board: number[][] = [];
}

class SudokuSolution {
  solution: number[][] = [];
}

function formatBoardForLlm(board: number[][]): string {
  return board.map(row => `  [${row.join(', ')}]`).join('\n');
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

      const browser = await chromium.connectOverCDP(endpointUrl);
      try {
        const page = await browser.newPage();
        console.log("🌐 Navigating to Sudoku site...");
        const url = "https://widget.websudoku.com/";
        await page.goto(url);
        await page.waitForSelector("#puzzle_grid", { timeout: 10000 });

        // 1. Extract the board
        let success = false;
        let board: number[][] = [];

        while (!success) {
          console.log("📊 Extracting sudoku board...");
          const options: ExtractOptions<SudokuBoard> = {
            instruction: "Extract the current sudoku board as a 9x9 array. Each cell should be a number (1-9) if filled, or 0 if empty.",
            schema: SudokuBoard,
            use_text_extract: false
          };

          const [extractSuccess, boardObjs] = await session.browser.agent.extract(options, page);
          if (extractSuccess && boardObjs.length > 0) {
            success = true;
            board = boardObjs[0].board;
          } else {
            console.log("❌ Failed to extract sudoku board, retry extracting");
            await new Promise(resolve => setTimeout(resolve, 3000));
          }
        }

        console.log("Current Board:\n" + board.map(row => row.join(' ')).join('\n'));
        const originalBoard = board.map(row => [...row]);

        // 2. Solve the sudoku
        const solutionOptions: ExtractOptions<SudokuSolution> = {
          instruction: `You are an expert sudoku solver. Given the following sudoku board as a 9x9 array (0 means empty), solve the sudoku and return the completed 9x9 array as 'solution'.

Sudoku rules:
- Each row must contain the digits 1-9 with no repeats.
- Each column must contain the digits 1-9 with no repeats.
- Each of the nine 3x3 subgrids must contain the digits 1-9 with no repeats.
- Only fill in the cells that are 0.
- The solution must be unique and valid.

board = [
${formatBoardForLlm(board)}
]

Return:
{
  solution: number[][] // 9x9, all filled, valid sudoku
}`,
          schema: SudokuSolution,
          use_text_extract: false
        };

        const [solutionSuccess, solutionObjs] = await session.browser.agent.extract(solutionOptions, page);
        if (!solutionSuccess || solutionObjs.length === 0) {
          console.log("❌ Failed to solve sudoku");
          return;
        }

        const solution = solutionObjs[0].solution;
        console.log("Solved Board:\n" + solution.map((row:any) => row.join(' ')).join('\n'));

        // 3. Fill the solution
        for (let row = 0; row < 9; row++) {
          for (let col = 0; col < 9; col++) {
            if (originalBoard[row][col] === 0) {
              const inputId = `f${col}${row}`;
              console.log(`Type '${solution[row][col]}' into the cell with id '${inputId}'`);

              // Use the act method for natural language action
              const actOptions: ActOptions = {
                action: `Enter '${solution[row][col]}' into the input element where the attribute id is exactly '${inputId}' (for example, if id='f53', you must match the full string 'f53', not just the number 53; do not split or extract numbers from the id)`
              };

              await session.browser.agent.act(actOptions, page);
              await new Promise(resolve => setTimeout(resolve, 500));
            }
          }
        }

        console.log("✅ Finished! The board has been solved and filled in the browser.");

      } catch (error) {
        console.log(`❌ Error in game loop: ${error}`);
      }
    } else {
      console.log("Failed to initialize browser");
    }
  }
}

if (require.main === module) {
  main().catch(console.error);
}
