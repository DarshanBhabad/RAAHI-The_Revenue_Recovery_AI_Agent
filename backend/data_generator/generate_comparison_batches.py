"""
Generates two IDENTICAL synthetic batches — one for RAAHI's intelligent
pipeline, one for the naive baseline — so recovery outcomes can be fairly
compared under identical starting conditions.
"""
import random
from data_generator.generate_synthetic_data import generate

def generate_comparison_datasets():
    random.seed(42)  # same seed = identical batch composition for fair comparison
    print("Generating RAAHI batch (merchant_id suffix: _raahi)...")
    # You'll tag merchant_ids differently to keep them queryable/separable
    # (implementation: wrap generate() to accept a merchant_id_suffix param)