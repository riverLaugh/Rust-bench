import argparse
from datasets import load_dataset, DatasetDict, Dataset
import os
from huggingface_hub import login
import sys

def parse_args():
    parser = argparse.ArgumentParser(
        description="Pull a dataset from Hugging Face, delete entries based on instance_id, and upload the cleaned dataset back to Hugging Face."
    )
    parser.add_argument(
        "--dataset_name",
        type=str,
        required=True,
        help="Name of the dataset on Hugging Face (e.g., username/dataset_name)."
    )
    parser.add_argument(
        "--split",
        type=str,
        default="train",
        help="Dataset split to process (e.g., train, test, validation). Default is 'train'."
    )
    parser.add_argument(
        "--instance_ids",
        type=str,
        nargs='+',
        required=True,
        help="List of instance_ids to delete. Provide as space-separated values."
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="cleaned_dataset",
        help="Directory where the cleaned dataset will be saved locally before uploading."
    )
    parser.add_argument(
        "--repo_id",
        type=str,
        default=None,
        help="Repository ID on Hugging Face to push the cleaned dataset to. If not specified, defaults to the original dataset name."
    )
    parser.add_argument(
        "--token",
        type=str,
        default=None,
        help="Hugging Face access token. If not provided, the script will attempt to read from the HUGGINGFACE_TOKEN environment variable."
    )
    return parser.parse_args()

def filter_dataset(dataset: Dataset, instance_ids_to_delete: set) -> Dataset:
    """
    Filters out instances from the dataset where 'instance_id' is in the instance_ids_to_delete set.
    """
    def is_not_in_delete_list(example):
        return example['instance_id'] not in instance_ids_to_delete

    cleaned_dataset = dataset.filter(is_not_in_delete_list)
    return cleaned_dataset

def main():
    args = parse_args()

    # Handle Hugging Face authentication
    token = args.token or os.getenv("HUGGING_FACE_HUB_TOKEN")
    if not token:
        print("Error: Hugging Face access token not provided. Use --token or set the HUGGINGFACE_TOKEN environment variable.")
        sys.exit(1)
    
    login(token=token)

    # Load the dataset
    print(f"Loading dataset '{args.dataset_name}' split '{args.split}' from Hugging Face...")
    try:
        dataset = load_dataset(args.dataset_name, split=args.split)
    except Exception as e:
        print(f"Error loading dataset: {e}")
        sys.exit(1)
    
    # Load instance_ids to delete
    instance_ids_to_delete = set(args.instance_ids)
    print(f"Total instance_ids to delete: {len(instance_ids_to_delete)}")

    # Filter the dataset
    print("Filtering the dataset...")
    cleaned_dataset = filter_dataset(dataset, instance_ids_to_delete)
    print(f"Original dataset size: {len(dataset)}")
    print(f"Cleaned dataset size: {len(cleaned_dataset)}")
    print(f"Number of entries removed: {len(dataset) - len(cleaned_dataset)}")

    # Prepare output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Save the cleaned dataset locally
    output_path = os.path.join(args.output_dir, f"{args.split}-cleaned.arrow")
    print(f"Saving the cleaned dataset locally to '{output_path}'...")
    cleaned_dataset.save_to_disk(output_path)
    print("Cleaned dataset saved successfully.")

    # Determine the repository ID for uploading
    repo_id = args.repo_id if args.repo_id else args.dataset_name
    print(f"Uploading the cleaned dataset to Hugging Face repository '{repo_id}'...")

    try:
        # Load the cleaned dataset as a DatasetDict if multiple splits are involved
        # For simplicity, we'll assume a single split is being handled
        # Initialize a DatasetDict for uploading
        cleaned_dataset_dict = DatasetDict({args.split: cleaned_dataset})

        # Push to Hugging Face Hub
        cleaned_dataset_dict.push_to_hub(repo_id, token=token)
        print("Cleaned dataset uploaded successfully to Hugging Face.")
    except Exception as e:
        print(f"Error uploading dataset: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
