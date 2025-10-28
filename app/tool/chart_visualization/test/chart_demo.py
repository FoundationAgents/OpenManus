import asyncio

from app.agent.data_analysis import DataAnalysis
from app.logger import logger


prefix = "Help me generate charts and save them locally, specifically:"
tasks = [
    {
        "prompt": "Help me show the sales of different products in different regions",
        "data": """Product Name,Region,Sales
Coke,South,2350
Coke,East,1027
Coke,West,1027
Coke,North,1027
Sprite,South,215
Sprite,East,654
Sprite,West,159
Sprite,North,28
Fanta,South,345
Fanta,East,654
Fanta,West,2100
Fanta,North,1679
Xingmu,South,1476
Xingmu,East,830
Xingmu,West,532
Xingmu,North,498
""",
    },
    {
        "prompt": "Show market share of each brand",
        "data": """Brand Name,Market Share,Average Price,Net Profit
Apple,0.5,7068,314531
Samsung,0.2,6059,362345
Vivo,0.05,3406,234512
Nokia,0.01,1064,-1345
Xiaomi,0.1,4087,131345""",
    },
    {
        "prompt": "Please help me show the sales trend of each product",
        "data": """Date,Type,Value
2023-01-01,Product A,52.9
2023-01-01,Product B,63.6
2023-01-01,Product C,11.2
2023-01-02,Product A,45.7
2023-01-02,Product B,89.1
2023-01-02,Product C,21.4
2023-01-03,Product A,67.2
2023-01-03,Product B,82.4
2023-01-03,Product C,31.7
2023-01-04,Product A,80.7
2023-01-04,Product B,55.1
2023-01-04,Product C,21.1
2023-01-05,Product A,65.6
2023-01-05,Product B,78
2023-01-05,Product C,31.3
2023-01-06,Product A,75.6
2023-01-06,Product B,89.1
2023-01-06,Product C,63.5
2023-01-07,Product A,67.3
2023-01-07,Product B,77.2
2023-01-07,Product C,43.7
2023-01-08,Product A,96.1
2023-01-08,Product B,97.6
2023-01-08,Product C,59.9
2023-01-09,Product A,96.1
2023-01-09,Product B,100.6
2023-01-09,Product C,66.8
2023-01-10,Product A,101.6
2023-01-10,Product B,108.3
2023-01-10,Product C,56.9""",
    },
    {
        "prompt": "Show the popularity of search keywords",
        "data": """Keyword,Popularity
Hot Word,1000
Zao Le Wo Men,800
Rao Jian Huo,400
My Wish is World Peace,400
Xiu Xiu Xiu,400
Shenzhou 11,400
Hundred Birds Facing the Wind,400
China Women's Volleyball Team,400
My Guan Na,400
Leg Dong,400
Hot Pot Hero,400
Baby's Heart is Bitter,400
Olympics,400
Awesome My Brother,400
Poetry and Distance,400
Song Joong-ki,400
PPAP,400
Blue Thin Mushroom,400
Rain Dew Evenly,400
Friendship's Little Boat Says It Flips,400
Beijing Slump,400
Dedication,200
Apple,200
Dog Belt,200
Old Driver,200
Melon-Eating Crowd,200
Zootopia,200
City Will Play,200
Routine,200
Water Reverse,200
Why Don't You Go to Heaven,200
Snake Spirit Man,200
Why Don't You Go to Heaven,200
Samsung Explosion Gate,200
Little Li Oscar,200
Ugly People Need to Read More,200
Boyfriend Power,200
A Face of Confusion,200
Descendants of the Sun,200""",
    },
    {
        "prompt": "Help me compare the performance of different electric vehicle brands using a scatter plot",
        "data": """Range,Charging Time,Brand Name,Average Price
2904,46,Brand1,2350
1231,146,Brand2,1027
5675,324,Brand3,1242
543,57,Brand4,6754
326,234,Brand5,215
1124,67,Brand6,654
3426,81,Brand7,159
2134,24,Brand8,28
1234,52,Brand9,345
2345,27,Brand10,654
526,145,Brand11,2100
234,93,Brand12,1679
567,94,Brand13,1476
789,45,Brand14,830
469,75,Brand15,532
5689,54,Brand16,498
""",
    },
    {
        "prompt": "Show conversion rates for each process",
        "data": """Process,Conversion Rate,Month
Step1,100,1
Step2,80,1
Step3,60,1
Step4,40,1""",
    },
    {
        "prompt": "Show the difference in breakfast consumption between men and women",
        "data": """Day,Men-Breakfast,Women-Breakfast
Monday,15,22
Tuesday,12,10
Wednesday,15,20
Thursday,10,12
Friday,13,15
Saturday,10,15
Sunday,12,14""",
    },
    {
        "prompt": "Help me show this person's performance in different aspects, is he a hexagonal warrior",
        "data": """dimension,performance
Strength,5
Speed,5
Shooting,3
Endurance,5
Precision,5
Growth,5""",
    },
    {
        "prompt": "Show data flow",
        "data": """Origin,Destination,value
Node A,Node 1,10
Node A,Node 2,5
Node B,Node 2,8
Node B,Node 3,2
Node C,Node 2,4
Node A,Node C,2
Node C,Node 1,2""",
    },
]


async def main():
    for index, item in enumerate(tasks):
        logger.info(f"Begin task {index} / {len(tasks)}!")
        agent = DataAnalysis()
        await agent.run(
            f"{prefix},chart_description:{item['prompt']},Data:{item['data']}"
        )
        logger.info(f"Finish with {item['prompt']}")


if __name__ == "__main__":
    asyncio.run(main())
