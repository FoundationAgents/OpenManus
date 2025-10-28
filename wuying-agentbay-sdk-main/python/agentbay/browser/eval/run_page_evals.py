import asyncio
import json
import logging
import os
import time
import importlib
import argparse
from typing import Dict, Any
from dotenv import load_dotenv

from agentbay.browser.eval.page_agent import PageAgent


# Configure logging to output to console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("run_page_evals")


async def run_single_task(
    task_name: str, task_config: Dict[str, Any]
) -> Dict[str, Any]:
    logger.info(f"🚀 Starting task: {task_name}")
    overall_start = time.perf_counter()

    agent = PageAgent(enable_metrics=True)
    browser_setup_s = 0.0
    open_start = time.perf_counter()
    await agent.initialize()
    open_end = time.perf_counter()
    browser_setup_s += open_end - open_start

    try:
        task_module = importlib.import_module(f"page_tasks.{task_name}")

        #result = await task_module.run(agent, logger, task_config)
        result = await agent.run_task(task_module, logger, task_config)

        status = "✅ Passed" if result.get("_success") else "❌ Failed"
        logger.info(f"{status} - Task: {task_name}")
        if not result.get("_success"):
            logger.error(f"Error: {result.get('error')}")

    except Exception as e:
        logger.error(f"💥 Unhandled exception in task {task_name}: {e}", exc_info=True)
        result = {"_success": False, "error": str(e)}
    finally:
        close_start = time.perf_counter()
        await agent.close()
        close_end = time.perf_counter()
        browser_setup_s += close_end - close_start
        browser_setup_s = round(browser_setup_s, 2)

    overall_end = time.perf_counter()
    total_duration_s = round(overall_end - overall_start, 2)
    task_duration_s = round(total_duration_s - browser_setup_s, 2)

    llm_metrics = agent.get_metrics()
    llm_metrics["llm_duration_s"] = int(round(llm_metrics.get("llm_duration_s", 0.0), 2))
    if task_duration_s:
        llm_time_percentage = round(
            llm_metrics["llm_duration_s"] / task_duration_s * 100, 1
        )
    else:
        llm_time_percentage = 0.0

    performance = {
        "total_duration_s": total_duration_s,
        "browser_setup_s": browser_setup_s,
        "task_duration_s": task_duration_s,
        **llm_metrics,
        "llm_time_percentage": llm_time_percentage,
    }

    return {
        "task_name": task_name,
        "result": result,
        "performance": performance,
    }


async def main():
    parser = argparse.ArgumentParser(
        description="""
        PageAgent Evals Runner
        ----------------------
        This script is for the running of evaluation tasks for the PageAgent.
        It reads a configuration from 'page_evals.config.json' to determine which
        tasks are available and their categories.

        The results, including pass/fail status and performance metrics, are
        aggregated and saved to 'eval-summary.json'.
        """,
        epilog="""
        Usage Examples:
        -----------------
        1. Run all evaluation tasks defined in the config file:
        python run_page_evals.py

        2. Run all tasks belonging to the 'observe' category:
        python run_page_evals.py --category observe

        3. Run only the 'arxiv' evaluation task:
        python run_page_evals.py --eval_name arxiv

        4. Run a task and pass a specific configuration override from the command line
        (This requires adding functionality to parse extra args, see advanced example):
        python run_page_evals.py --eval_name allrecipes --config --config '{"extract_method": "textExtract"}'
        """,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--eval_name",
        type=str,
        help="Run a single evaluation by its exact name (e.g., 'extract_apartments').",
    )
    parser.add_argument(
        "--category",
        type=str,
        help="Run all evaluations in a specific category (e.g., 'observe').",
    )
    args = parser.parse_args()
    try:
        with open("page_evals.config.json", "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        logger.error("page_evals.config.json not found! Please create it.")
        return

    all_tasks = config["tasks"]
    tasks_to_run = []
    if args.eval_name:
        tasks_to_run = [
            task for task in all_tasks if task.get("name") == args.eval_name
        ]
        if not tasks_to_run:
            logger.error(f"Task with name '{args.eval_name}' not found in config file.")
            return
    elif args.category:
        tasks_to_run = [
            task for task in all_tasks if args.category in task.get("categories", [])
        ]
        if not tasks_to_run:
            logger.error(
                f"No tasks found for category '{args.category}' in config file."
            )
            return
    else:
        tasks_to_run = all_tasks
    all_results = []

    for task in tasks_to_run:
        task_result = await run_single_task(task["name"], task)
        all_results.append(task_result)

    passed_tasks = [r for r in all_results if r["result"]["_success"]]
    failed_tasks = [r for r in all_results if not r["result"]["_success"]]

    summary = {
        "experimentName": "page_agent_local_run",
        "passed": [{"eval": r["task_name"]} for r in passed_tasks],
        "failed": [
            {"eval": r["task_name"], "error": r["result"].get("error")}
            for r in failed_tasks
        ],
        "summary": {
            "total": len(all_results),
            "passed_count": len(passed_tasks),
            "failed_count": len(failed_tasks),
            "success_rate": (
                len(passed_tasks) / len(all_results) * 100 if all_results else 0
            ),
        },
        "results": all_results,
    }

    summary_path = os.path.join(os.path.dirname(__file__), "eval-summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    logger.info(f"📊 Evaluation summary written to {summary_path}")


if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())
