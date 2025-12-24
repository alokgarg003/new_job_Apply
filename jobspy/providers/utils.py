import time
import random
import logging
from typing import Callable, Any

logger = logging.getLogger("jobspy.providers.utils")


def retry_with_backoff(fn: Callable, attempts: int = 3, base_delay: float = 0.5, max_delay: float = 10.0, jitter: float = 0.2):
    """Simple retry wrapper with exponential backoff and jitter.

    Usage:
        result = retry_with_backoff(lambda: provider.fetch_contacts(...), attempts=5)
    """
    exc = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as e:
            exc = e
            sleep_time = min(max_delay, base_delay * (2 ** (attempt - 1)))
            sleep_time = sleep_time + random.random() * jitter
            logger.warning("Attempt %d failed: %s. Sleeping %.2fs before retry", attempt, str(e), sleep_time)
            time.sleep(sleep_time)
    # if we reach here, raise last exception
    raise exc
