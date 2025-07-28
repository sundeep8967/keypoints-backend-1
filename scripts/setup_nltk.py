#!/usr/bin/env python3
"""
Script to download NLTK data if not already cached.
Used by GitHub Actions workflow.
"""

import nltk
import os

nltk_data_dir = os.path.expanduser('~/nltk_data')
if not os.path.exists(os.path.join(nltk_data_dir, 'tokenizers', 'punkt')):
    print('Downloading NLTK punkt data...')
    nltk.download('punkt', download_dir=nltk_data_dir)
else:
    print('NLTK punkt data already cached')