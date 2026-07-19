import sys
import tempfile
from pathlib import Path

import polars as pl

from polars_baseball._cache import configure_cache, global_cache

if __name__ == "__main__":
    cache_dir = Path(tempfile.mkdtemp(prefix="cache_validate_"))
    configure_cache(cache_dir)

    test_df = pl.DataFrame({"a": [1, 2, 3]})
    key = "ci_validation_test_key"

    # Verify set
    try:
        global_cache.set(key, test_df)
    except Exception as e:
        print(f"Cache set failed: {e}")
        sys.exit(1)

    # Verify get
    cached_df = global_cache.get(key)
    if cached_df is None:
        print("Cache get returned None (cache miss when hit expected)")
        sys.exit(1)

    if not cached_df.equals(test_df):
        print("Cached DataFrame does not match original DataFrame")
        sys.exit(1)

    # Verify clear
    global_cache.clear()
    cleared_df = global_cache.get(key)
    if cleared_df is not None:
        print("Cache clear failed to remove entry")
        sys.exit(1)

    # Cleanup temp dir
    if cache_dir.exists():
        cache_dir.rmdir()

    print("Cache validation passed successfully!")
    sys.exit(0)
