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
from huggingface_hub import login
from tqdm import tqdm

# Import OpenManus classes.
from app.agent.manus import Manus
from app.logger import logger

append_answer_lock = threading.Lock()

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--concurrency", type=int, default=8,
                        help="Number of concurrent evaluation tasks (default: 8)")
    parser.add_argument("--model-id", type=str, default="o3-mini",
                        help="The model identifier to use (default: 'o3-mini')")
    parser.add_argument("--run-name", type=str, default="default_run",
                        help="Name for the evaluation run (used for output file naming)")
    parser.add_argument("--num-questions", type=str, default="1",
                        help="Number of GAIA questions to be tested. Use an integer (default: 1) or 'all' to run all questions.")
    return parser.parse_args()

print("Make sure you deactivated Tailscale VPN, else some URLs will be blocked!")

# Evaluation settings
SET = "validation"
custom_role_conversions = {"tool-call": "assistant", "tool-response": "user"}

# Load environment variables and log in
load_dotenv(override=True)
login(os.getenv("HF_TOKEN"))
os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "60"

# Load the GAIA evaluation dataset (with trust_remote_code)
eval_ds = datasets.load_dataset("gaia-benchmark/GAIA", "2023_all", trust_remote_code=True)[SET]
eval_ds = eval_ds.rename_columns({"Question": "question", "Final answer": "model_answer", "Level": "task"})

def preprocess_file_paths(row):
    if len(row["file_name"]) > 0:
        row["file_name"] = os.path.join("data", "gaia", SET, row["file_name"])
    return row

eval_ds = eval_ds.map(preprocess_file_paths)
eval_df = pd.DataFrame(eval_ds)
print("Loaded evaluation dataset:")
print(eval_df["task"].value_counts())

def append_answer(entry: dict, jsonl_file: str) -> None:
    jsonl_file = Path(jsonl_file)
    jsonl_file.parent.mkdir(parents=True, exist_ok=True)
    with append_answer_lock, open(jsonl_file, "a", encoding="utf-8") as fp:
        fp.write(json.dumps(entry) + "\n")
    print("Answer exported to file:", jsonl_file.resolve())

async def answer_single_question(example, answers_file: str):
    agent = Manus()  # Instantiate the Manus (OpenManus) agent.
    
    augmented_question = (
        "You have one question to answer. It is paramount that you provide a correct answer. "
        "Run verification steps if needed. Here is the task:\n" + example["question"]
    )
    if example.get("file_name"):
        file_path = example["file_name"]
        if not os.path.exists(file_path):
            logger.warning(f"Attached file {file_path} not found. Skipping file conversion.")
            prompt_files = "\n\n[Warning: Attached file not found; proceeding without its content.]"
        else:
            prompt_files = f"\n\n[Attached file: {file_path} found and processed.]"
        augmented_question += prompt_files

    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        logger.info("Running agent for the given prompt...")
        result = await agent.run(augmented_question)
        final_answer = str(result)
        intermediate_steps = []  # Placeholder for intermediate steps.
        parsing_error = False
        iteration_limit_exceeded = False
        raised_exception = False
        error_message = None
    except Exception as e:
        logger.error("Error processing prompt: " + str(e))
        final_answer = None
        intermediate_steps = []
        parsing_error = False
        iteration_limit_exceeded = False
        raised_exception = True
        error_message = str(e)
    end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    annotated_example = {
        "agent_name": "OpenManus",
        "question": example["question"],
        "augmented_question": augmented_question,
        "prediction": final_answer,
        "intermediate_steps": intermediate_steps,
        "parsing_error": parsing_error,
        "iteration_limit_exceeded": iteration_limit_exceeded,
        "agent_error": error_message if raised_exception else None,
        "start_time": start_time,
        "end_time": end_time,
        "task": example["task"],
        "task_id": example["task_id"],
        "model_answer": example["model_answer"],
    }
    append_answer(annotated_example, answers_file)

def get_examples_to_answer(answers_file: str, dataset) -> list:
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
    
    print(f"Processing {len(all_examples)} examples out of remaining unanswered questions.")
    
    for example in tqdm(all_examples, desc="Processing tasks"):
        await answer_single_question(example, answers_file)
    
    print("All tasks processed.")

if __name__ == "__main__":
    asyncio.run(main())
(OpenManus) williamsun@Williams-MacBook-Pro OpenManus % cat run_gaia_model_answer.py
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
from huggingface_hub import login
from tqdm import tqdm

# Import OpenManus classes.
from app.agent.manus import Manus
from app.logger import logger

append_answer_lock = threading.Lock()

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--concurrency", type=int, default=8,
                        help="Number of concurrent evaluation tasks (default: 8)")
    parser.add_argument("--model-id", type=str, default="o3-mini",
                        help="The model identifier to use (default: 'o3-mini')")
    parser.add_argument("--run-name", type=str, default="default_run",
                        help="Name for the evaluation run (used for output file naming)")
    parser.add_argument("--num-questions", type=str, default="1",
                        help="Number of GAIA questions to be tested. Use an integer (default: 1) or 'all' to run all questions.")
    return parser.parse_args()

print("Make sure you deactivated Tailscale VPN, else some URLs will be blocked!")

# Evaluation settings
SET = "validation"
custom_role_conversions = {"tool-call": "assistant", "tool-response": "user"}

# Load environment variables and log in
load_dotenv(override=True)
login(os.getenv("HF_TOKEN"))
os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "60"

# Load the GAIA evaluation dataset (with trust_remote_code)
eval_ds = datasets.load_dataset("gaia-benchmark/GAIA", "2023_all", trust_remote_code=True)[SET]
eval_ds = eval_ds.rename_columns({"Question": "question", "Final answer": "model_answer", "Level": "task"})

def preprocess_file_paths(row):
    if len(row["file_name"]) > 0:
        row["file_name"] = os.path.join("data", "gaia", SET, row["file_name"])
    return row

eval_ds = eval_ds.map(preprocess_file_paths)
eval_df = pd.DataFrame(eval_ds)
print("Loaded evaluation dataset:")
print(eval_df["task"].value_counts())

def append_answer(entry: dict, jsonl_file: str) -> None:
    jsonl_file = Path(jsonl_file)
    jsonl_file.parent.mkdir(parents=True, exist_ok=True)
    with append_answer_lock, open(jsonl_file, "a", encoding="utf-8") as fp:
        fp.write(json.dumps(entry) + "\n")
    print("Answer exported to file:", jsonl_file.resolve())

async def answer_single_question(example, answers_file: str):
    agent = Manus()  # Instantiate the Manus (OpenManus) agent.
    
    augmented_question = (
        "You have one question to answer. It is paramount that you provide a correct answer. "
        "Run verification steps if needed. Here is the task:\n" + example["question"]
    )
    if example.get("file_name"):
        file_path = example["file_name"]
        if not os.path.exists(file_path):
            logger.warning(f"Attached file {file_path} not found. Skipping file conversion.")
            prompt_files = "\n\n[Warning: Attached file not found; proceeding without its content.]"
        else:
            prompt_files = f"\n\n[Attached file: {file_path} found and processed.]"
        augmented_question += prompt_files

    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        logger.info("Running agent for the given prompt...")
        result = await agent.run(augmented_question)
        final_answer = str(result)
        intermediate_steps = []  # Placeholder for intermediate steps.
        parsing_error = False
        iteration_limit_exceeded = False
        raised_exception = False
        error_message = None
    except Exception as e:
        logger.error("Error processing prompt: " + str(e))
        final_answer = None
        intermediate_steps = []
        parsing_error = False
        iteration_limit_exceeded = False
        raised_exception = True
        error_message = str(e)
    end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    annotated_example = {
        "agent_name": "OpenManus",
        "question": example["question"],
        "augmented_question": augmented_question,
        "prediction": final_answer,
        "intermediate_steps": intermediate_steps,
        "parsing_error": parsing_error,
        "iteration_limit_exceeded": iteration_limit_exceeded,
        "agent_error": error_message if raised_exception else None,
        "start_time": start_time,
        "end_time": end_time,
        "task": example["task"],
        "task_id": example["task_id"],
        "model_answer": example["model_answer"],
    }
    append_answer(annotated_example, answers_file)

def get_examples_to_answer(answers_file: str, dataset) -> list:
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
    
    print(f"Processing {len(all_examples)} examples out of remaining unanswered questions.")
    
    for example in tqdm(all_examples, desc="Processing tasks"):
        await answer_single_question(example, answers_file)
    
    print("All tasks processed.")

if __name__ == "__main__":
    asyncio.run(main())
(OpenManus) williamsun@Williams-MacBook-Pro OpenManus % vi run_gaia_model_answer.py           
(OpenManus) williamsun@Williams-MacBook-Pro OpenManus % cat run_gaia_model_answer.py 
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
from huggingface_hub import login
from tqdm import tqdm

# Import OpenManus classes.
from app.agent.manus import Manus
from app.logger import logger

append_answer_lock = threading.Lock()

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--concurrency", type=int, default=8,
                        help="Number of concurrent evaluation tasks (default: 8)")
    parser.add_argument("--model-id", type=str, default="o3-mini",
                        help="The model identifier to use (default: 'o3-mini')")
    parser.add_argument("--run-name", type=str, default="default_run",
                        help="Name for the evaluation run (used for output file naming)")
    parser.add_argument("--num-questions", type=str, default="1",
                        help="Number of GAIA questions to be tested. Use an integer (default: 1) or 'all' to run all questions.")
    return parser.parse_args()

print("Make sure you deactivated Tailscale VPN, else some URLs will be blocked!")

# Evaluation settings
SET = "validation"
custom_role_conversions = {"tool-call": "assistant", "tool-response": "user"}

# Load environment variables and log in
load_dotenv(override=True)
login(os.getenv("HF_TOKEN"))
os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "60"

# Load the GAIA evaluation dataset (with trust_remote_code)
eval_ds = datasets.load_dataset("gaia-benchmark/GAIA", "2023_all", trust_remote_code=True)[SET]
eval_ds = eval_ds.rename_columns({"Question": "question", "Final answer": "model_answer", "Level": "task"})

def preprocess_file_paths(row):
    if len(row["file_name"]) > 0:
        row["file_name"] = os.path.join("data", "gaia", SET, row["file_name"])
    return row

eval_ds = eval_ds.map(preprocess_file_paths)
eval_df = pd.DataFrame(eval_ds)
print("Loaded evaluation dataset:")
print(eval_df["task"].value_counts())

def append_answer(entry: dict, jsonl_file: str) -> None:
    jsonl_file = Path(jsonl_file)
    jsonl_file.parent.mkdir(parents=True, exist_ok=True)
    with append_answer_lock, open(jsonl_file, "a", encoding="utf-8") as fp:
        fp.write(json.dumps(entry) + "\n")
    print("Answer exported to file:", jsonl_file.resolve())

async def answer_single_question(example, answers_file: str):
    agent = Manus()  # Instantiate the Manus (OpenManus) agent.
    
    augmented_question = (
        "You have one question to answer. It is paramount that you provide a correct answer. "
        "Run verification steps if needed. Here is the task:\n" + example["question"]
    )
    if example.get("file_name"):
        file_path = example["file_name"]
        if not os.path.exists(file_path):
            logger.warning(f"Attached file {file_path} not found. Skipping file conversion.")
            prompt_files = "\n\n[Warning: Attached file not found; proceeding without its content.]"
        else:
            prompt_files = f"\n\n[Attached file: {file_path} found and processed.]"
        augmented_question += prompt_files

    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        logger.info("Running agent for the given prompt...")
        result = await agent.run(augmented_question)
        final_answer = str(result)
        intermediate_steps = []  # Placeholder for intermediate steps.
        parsing_error = False
        iteration_limit_exceeded = False
        raised_exception = False
        error_message = None
    except Exception as e:
        logger.error("Error processing prompt: " + str(e))
        final_answer = None
        intermediate_steps = []
        parsing_error = False
        iteration_limit_exceeded = False
        raised_exception = True
        error_message = str(e)
    end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    annotated_example = {
        "agent_name": "OpenManus",
        "question": example["question"],
        "augmented_question": augmented_question,
        "prediction": final_answer,
        "intermediate_steps": intermediate_steps,
        "parsing_error": parsing_error,
        "iteration_limit_exceeded": iteration_limit_exceeded,
        "agent_error": error_message if raised_exception else None,
        "start_time": start_time,
        "end_time": end_time,
        "task": example["task"],
        "task_id": example["task_id"],
        "model_answer": example["model_answer"],
    }
    append_answer(annotated_example, answers_file)

def get_examples_to_answer(answers_file: str, dataset) -> list:
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
    
    print(f"Processing {len(all_examples)} examples out of remaining unanswered questions.")
    
    for example in tqdm(all_examples, desc="Processing tasks"):
        await answer_single_question(example, answers_file)
    
    print("All tasks processed.")

if __name__ == "__main__":
    asyncio.run(main())
