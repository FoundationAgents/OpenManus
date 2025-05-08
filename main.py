import asyncio

from app.agent.ppt import FixedToolCallAgent
from app.logger import logger


async def main():
    agent = FixedToolCallAgent()
    try:
        prompt = '''
1. Lecture slide:
I am a lecturer. I am teaching the machine learning coure for research students. Please generate latex code for lecture slide for different reinforcement learning algorithms.
Note that:
1). Note that the lecture duration is 2 hour, so we need to generate 30 pages.
2). for each reinforcement learning algorithms, the slide should include motivation, problem and intuitive solution and detailed math equations.
3). Please make sure the the lecture have a good self-contain.
        '''
        if not prompt.strip():
            logger.warning("Empty prompt provided.")
            return

        logger.warning("Processing your request...")
        await agent.run(prompt)
        logger.info("Request processing completed.")
    except KeyboardInterrupt:
        logger.warning("Operation interrupted.")



if __name__ == "__main__":
    asyncio.run(main())
