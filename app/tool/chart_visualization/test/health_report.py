import asyncio
import os
import sys
print(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
from app.agent.data_analysis import DataAnalysis
from app.agent.manus import Manus


# from app.agent.manus import Manus


async def main():
    # agent = DataAnalysis()
    agent = Manus()
    await agent.run(
"""Requirement: Analyze the following data and generate a graphical data report in HTML format. The final product should be a data report.
Table1: 用户基本信息
Name,Age,Gender,Height(cm),Weight(kg),MeasureDate
张三,45,男,170,98.6,2023-10-01

Table2: 身体成分数据
Date,BodyFat(%),MuscleMass(kg),WaterContent(%),BoneMass(kg),VisceralFat,Protein(%)
2023-10-01,35.2,42.3,43.1,2.8,18,14.2

Table3: 每日营养活动数据
Date,CaloriesIntake(kcal),CaloriesBurned(kcal),ProteinIntake(g),CarbIntake(g),FatIntake(g),Steps,ActiveMinutes,SleepHours,MorningWeight(kg)
2023-09-01,3850,1250,85,480,120,3200,12,5.2,99.2
2023-09-02,4200,1100,90,520,135,2800,8,4.8,99.5
2023-09-03,3600,950,78,450,110,2500,5,5.5,99.8
2023-09-04,3950,1050,82,490,125,2900,10,4.5,100.1
2023-09-05,4100,1150,88,510,130,3100,15,5.0,100.3
2023-09-06,3750,980,80,460,115,2600,6,4.7,100.6
2023-09-07,4300,1200,92,540,140,3300,18,4.3,100.9
2023-09-08,3450,900,75,430,105,2400,4,5.2,101.2
2023-09-09,4000,1000,84,500,122,2700,9,4.9,101.5
2023-09-10,3800,975,79,470,118,2550,7,5.1,101.8
2023-09-11,4150,1100,86,515,128,3000,14,4.6,102.0
2023-09-12,3550,925,77,440,108,2300,3,5.4,102.3
2023-09-13,4250,1180,94,530,138,3400,20,4.2,102.6
2023-09-14,3700,990,81,465,113,2650,8,5.3,102.9
2023-09-15,4050,1070,87,505,127,2950,13,4.8,103.1
2023-09-16,3500,910,76,435,104,2250,2,5.6,103.4
2023-09-17,3900,1020,83,485,120,2750,11,4.7,103.7
2023-09-18,4350,1250,96,550,145,3500,22,4.0,104.0
2023-09-19,3650,960,79,455,112,2450,5,5.2,104.3
2023-09-20,4000,1030,85,495,124,2850,12,4.9,104.5
2023-09-21,3450,890,74,425,103,2200,1,5.5,104.8
2023-09-22,3850,995,82,475,119,2700,10,4.6,105.1
2023-09-23,4100,1120,89,515,131,3050,16,4.3,105.4
2023-09-24,3550,935,77,440,107,2350,4,5.4,105.7
2023-09-25,3950,1010,84,490,123,2800,13,4.8,106.0
2023-09-26,4200,1150,91,525,136,3200,19,4.1,106.3
2023-09-27,3600,945,78,445,109,2400,6,5.3,106.6
2023-09-28,4050,1080,87,505,128,2900,15,4.7,106.9
2023-09-29,3750,970,80,460,116,2600,9,5.0,107.2
2023-09-30,4300,1220,95,540,142,3350,23,3.9,107.5

Table4: 健康指标参考范围
Category,SubCategory,Range,Unit
BMI,Underweight,<18.5,kg/m²
BMI,Normal,18.5-24.9,kg/m²
BMI,Overweight,25-29.9,kg/m²
BMI,Obese,≥30,kg/m²
BodyFat,Male(40-59),11-22,%
BodyFat,Female(40-59),23-34,%
VisceralFat,Normal,1-9,Level
VisceralFat,High,10-14,Level
VisceralFat,Very High,≥15,Level
Sleep,Recommended,7-9,hours
Steps,Active,≥10000,steps/day
"""
    )
if __name__ == "__main__":
    asyncio.run(main())
