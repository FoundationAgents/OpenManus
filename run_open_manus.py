import asyncio
import time

from app.agent.manus import Manus
from app.flow.base import FlowType
from app.flow.flow_factory import FlowFactory
from app.logger import logger


class FlowRunner:
    async def run_flow(self, prompt):
        agents = {
            "manus": Manus(),
        }

        try:
            if prompt.strip().isspace() or not prompt:
                logger.warning("Empty prompt provided.")
                return None

            flow = FlowFactory.create_flow(
                flow_type=FlowType.PLANNING,
                agents=agents,
            )
            logger.warning("Processing your request...")

            try:
                start_time = time.time()
                result = await asyncio.wait_for(
                    flow.execute(prompt),
                    timeout=3600,  # 60 minute timeout for the entire execution
                )
                elapsed_time = time.time() - start_time
                logger.info(f"Request processed in {elapsed_time:.2f} seconds")
                logger.info(result)
                return result
            except asyncio.TimeoutError:
                logger.error("Request processing timed out after 1 hour")
                logger.info(
                    "Operation terminated due to timeout. Please try a simpler request."
                )
                return None

        except KeyboardInterrupt:
            logger.info("Operation cancelled by user.")
            return None
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return None


if __name__ == "__main__":
    runner = FlowRunner()
    prompt = "Where is the capital of France?"  # Replace with actual prompt or loop through dataset
    result = asyncio.run(runner.run_flow(prompt))
    if result is not None:
        print("***********Result:*************", result)
    else:
        print("------reuslt is none -----");
