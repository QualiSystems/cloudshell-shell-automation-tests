import time
from threading import Thread
from typing import List


def wait_for_end_threads(threads: List[Thread]):
    """Endless loop that wait for ending the threads."""
    while any(map(Thread.is_alive, threads)):
        time.sleep(1)
