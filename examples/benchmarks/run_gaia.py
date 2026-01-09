import sys


sys.path.append("/Users/yigeng/projects/agent-research/OpenManus/")
import argparse
import asyncio
import json
import os
import threading
from datetime import datetime
from pathlib import Path

import datasets
import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm

# Import OpenManus classes.
from app.agent.manus import Manus
from app.llm import LLM
from app.logger import logger


append_answer_lock = threading.Lock()


def preprocess_file_paths(row):
    if len(row["file_name"]) > 0:
        row["file_name"] = os.path.join("data", "gaia", SET, row["file_name"])
    return row


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run-name",
        type=str,
        default="default_run",
        help="Name for the evaluation run (used for output file naming)",
    )
    parser.add_argument(
        "--num-questions",
        type=str,
        default="1",
        help="Number of GAIA questions to be tested. Use an integer (default: 1) or 'all' to run all questions.",
    )
    return parser.parse_args()


print("Make sure you deactivated Tailscale VPN, else some URLs will be blocked!")

# Evaluation settings
SET = "validation"

# Load environment variables and log in
load_dotenv(override=True)
# login(os.getenv("HF_TOKEN"))
os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "60"

# Load the GAIA evaluation dataset (with trust_remote_code)
eval_ds = datasets.load_dataset(
    "gaia-benchmark/GAIA", "2023_all", trust_remote_code=True
)[SET]
eval_ds = eval_ds.rename_columns(
    {"Question": "question", "Final answer": "true_answer", "Level": "task"}
)


eval_ds = eval_ds.map(preprocess_file_paths)
eval_df = pd.DataFrame(eval_ds)
print("Loaded evaluation dataset:")
print(eval_df["task"].value_counts())


async def prepare_response(
    original_task: str, intermediate_steps: str, model: LLM
) -> str:
    # Format the intermediate steps into a readable format
    """
    Prepare the input for the LLM by formatting the intermediate steps and creating a prompt with the original question and execution steps.

    Args:
        original_task (str): The original question text.
        intermediate_steps (str or list[str]): The intermediate execution steps as a single string or a list of strings.
        model (LLM): The LLM agent instance.

    Returns:
        str: The final answer following the requirements specified in the prompt.
    """
    steps_text = ""
    if isinstance(intermediate_steps, list):
        for i, step in enumerate(intermediate_steps, 1):
            steps_text += f"Step {i}: {step}\n"
    else:
        steps_text = str(intermediate_steps)

    # Create the prompt for the LLM
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"""Based on the following execution steps, provide a final answer to the original question.

ORIGINAL QUESTION:
{original_task}

EXECUTION STEPS:
{steps_text}

To output the final answer, use the following template: FINAL ANSWER: [YOUR FINAL ANSWER]

Requirements for the final answer:
1. Your answer should be a number OR as few words as possible OR a comma separated list of numbers and/or strings
2. For numbers:
   - Express them numerically (use digits, not words)
   - Don't use commas in numbers
   - Don't include units (like $, USD, %) unless specifically requested
3. For strings:
   - Don't use articles or abbreviations unless specified
   - Don't include final punctuation (., !, ?)
4. For lists:
   - Use comma separation
   - Apply the number/string rules above to each element
5. If no answer can be determined, write: FINAL ANSWER: Unable to determine
6. Follow any specific formatting instructions in the original question (e.g., alphabetization, sequencing, units, rounding, decimal places)

Please analyze the execution steps and provide the final answer following these requirements.""",
                }
            ],
        }
    ]

    # Get response from LLM using the agent's LLM instance
    response = await model.ask(messages=messages)

    # Extract the final answer
    if "FINAL ANSWER:" in response:
        final_answer = response.split("FINAL ANSWER:")[-1].strip()
    else:
        final_answer = "Unable to determine"

    logger.info(f"> Reformulated answer: {final_answer}")

    return final_answer


def append_answer(entry: dict, jsonl_file: str) -> None:
    """
    Append an answer to a file.

    Args:
        entry: The answer data to write as a JSON object
        jsonl_file: The path to the file to write to

    Returns:
        None
    """
    jsonl_file = Path(jsonl_file)
    jsonl_file.parent.mkdir(parents=True, exist_ok=True)
    with append_answer_lock, open(jsonl_file, "a", encoding="utf-8") as fp:
        fp.write(json.dumps(entry) + "\n")
    print("Answer exported to file:", jsonl_file.resolve())


async def answer_single_question(example, answers_file: str):
    """
    Run a single question with the Manus agent and save the result to a file.

    Args:
        example (dict): A dictionary containing the question and its metadata.
        answers_file (str): The path to the file where the answer should be saved in JSON Lines format.

    Returns:
        None
    """
    agent = Manus()  # Instantiate the Manus (OpenManus) agent.

    augmented_question = (
        "You have one question to answer. It is paramount that you provide a correct answer. "
        "Run verification steps if needed. Here is the task:\n" + example["question"]
    )
    if example.get("file_name"):
        file_path = example["file_name"]
        if not os.path.exists(file_path):
            logger.warning(
                f"Attached file {file_path} not found. Skipping file conversion."
            )
            prompt_files = "\n\n[Warning: Attached file not found; proceeding without its content.]"
        else:
            prompt_files = f"\n\n[Attached file: {file_path} found and processed.]"
        augmented_question += prompt_files

    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        logger.info("Running agent for the given prompt...")
        result = await agent.run(augmented_question)
        final_answer = await prepare_response(augmented_question, result, agent.llm)
        raised_exception = False
        error_message = None
    except Exception as e:
        logger.error("Error processing prompt: " + str(e))
        final_answer = None
        raised_exception = True
        error_message = str(e)
    end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    annotated_example = {
        "agent_name": "OpenManus",
        "question": example["question"],
        "augmented_question": augmented_question,
        "prediction": final_answer,
        "intermediate_steps": result,
        "agent_error": error_message if raised_exception else None,
        "start_time": start_time,
        "end_time": end_time,
        "task": example["task"],
        "task_id": example["task_id"],
        "true_answer": example["true_answer"],
    }
    append_answer(annotated_example, answers_file)


def get_examples_to_answer(answers_file: str, dataset) -> list:
    """
    Get examples from a dataset that have not been answered yet.

    Args:
    answers_file (str): path to a JSON lines file containing previous answers.
    dataset (Dataset): a dataset object containing examples to process.

    Returns:
    list: a list of examples from the dataset that have not been answered yet.
    """
    print(f"Loading previous answers from {answers_file}...")
    try:
        done_questions = pd.read_json(answers_file, lines=True)["question"].tolist()
        print(f"Found {len(done_questions)} answered questions.")
    except Exception as e:
        print("No previous answers found or error reading file:", e)
        done_questions = []
    return [ex for ex in dataset.to_list() if ex["question"] not in done_questions]


async def main():
    args = parse_args()
    print(f"Starting run with arguments: {args}")
    answers_file = os.path.join("output", SET, f"{args.run_name}.jsonl")

    # Get only unanswered questions from the dataset
    all_examples = get_examples_to_answer(answers_file, eval_ds)
    # Apply num_questions limit if not set to "all"
    if args.num_questions.lower() != "all":
        n = int(args.num_questions)
        all_examples = all_examples[:n]

    print(
        f"Processing {len(all_examples)} examples out of remaining unanswered questions."
    )

    for example in tqdm(all_examples, desc="Processing tasks"):
        await answer_single_question(example, answers_file)

    print("All tasks processed.")


if __name__ == "__main__":
    asyncio.run(main())
