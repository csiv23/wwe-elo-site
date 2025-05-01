# storage.py
import csv
from typing import Dict
import pandas as pd


def save_elos_to_csv(elos: Dict[str, float], path: str) -> None:
    """
    Save the ELO dict to a CSV file with columns ['wrestler', 'elo'].
    """
    df = pd.DataFrame(list(elos.items()), columns=['wrestler', 'elo'])
    df.to_csv(path, index=False)


def load_elos_from_csv(path: str) -> Dict[str, float]:
    """
    Load a CSV of ['wrestler','elo'] back into a dict.
    """
    df = pd.read_csv(path)
    return dict(zip(df['wrestler'], df['elo']))

# (Optional) add S3 helpers using boto3

try:
    import boto3
    def upload_to_s3(local_path: str, bucket: str, key: str):
        s3 = boto3.client('s3')
        s3.upload_file(local_path, bucket, key)

    def download_from_s3(bucket: str, key: str, local_path: str):
        s3 = boto3.client('s3')
        s3.download_file(bucket, key, local_path)

except ImportError:
    pass  # boto3 not installed; skip S3 helpers for now