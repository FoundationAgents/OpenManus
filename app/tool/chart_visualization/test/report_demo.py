import asyncio

from app.agent.data_analysis import DataAnalysis


# from app.agent.manus import Manus


async def main():
    agent = DataAnalysis()
    # agent = Manus()
    await agent.run(
        """Requirement:
1. Analyze the following data and generate a graphical data report in HTML format. The final product should be a data report.
Data:
Month | Team A | Team B | Team C
January | 1200 hours | 1350 hours | 1100 hours
February | 1250 hours | 1400 hours | 1150 hours
March | 1180 hours | 1300 hours | 1300 hours
April | 1220 hours | 1280 hours | 1400 hours
May | 1230 hours | 1320 hours | 1450 hours
June | 1200 hours | 1250 hours | 1500 hours  """
    )


if __name__ == "__main__":
    asyncio.run(main())
