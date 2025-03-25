import asyncio
import time
from app.agent.manus import Manus
from app.logger import logger


class MainRunner:
    async def run_main(self, prompt):
        agent = Manus()
        try:
            if prompt.strip().isspace() or not prompt:
                logger.warning("Empty prompt provided.")
                return None

            logger.warning("Processing your request...")

            try:

                start_time = time.time()
                result = await agent.run(prompt)
                logger.info("Request processing completed.")
                elapsed_time = time.time() - start_time
                logger.info(f"Request processed in {elapsed_time:.2f} seconds")
                return result

            except asyncio.TimeoutError:
                logger.error("Request processing timed out after 1 hour")
                logger.info(
                    "Operation terminated due to timeout. Please try a simpler request."
                )
                return None

        except KeyboardInterrupt:
            logger.warning("Operation interrupted.")
            return None
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return None

if __name__ == "__main__":
    runner = MainRunner()
    prompt = "Where is the capital of France?"  # Replace with actual prompt or loop through dataset
    result = asyncio.run(runner.run_main(prompt))
    if result is not None:
        print("***********Result:*************", result)
    else:
        print("------reuslt is none -----");
