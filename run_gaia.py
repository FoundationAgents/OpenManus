from dotenv import load_dotenv
load_dotenv()

import os
from loguru import logger


from utils import GAIABenchmark


# Configuration
LEVEL = 1
SAVE_RESULT = True
test_idx = [0,1]


def main():
    """Main function to run the GAIA benchmark."""
    # Create cache directory
    cache_dir = "tmp/"
    os.makedirs(cache_dir, exist_ok=True)
    

    # Initialize benchmark
    benchmark = GAIABenchmark(
        data_dir="/Users/yigeng/projects/owl/owl/data/gaia",
        save_to=f"results/result.json"
    )

    # Print benchmark information
    print(f"Number of validation examples: {len(benchmark.valid)}")
    print(f"Number of test examples: {len(benchmark.test)}")

    # Run benchmark
    result = benchmark.run(
        on="valid", 
        level=LEVEL, 
        idx=test_idx,
        save_result=SAVE_RESULT,
    )

    # Output results
    logger.success(f"Correct: {result['correct']}, Total: {result['total']}")
    logger.success(f"Accuracy: {result['accuracy']}")


if __name__ == "__main__":
    main()
