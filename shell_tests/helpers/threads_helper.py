import time
from threading import Thread, current_thread
from typing import List


def wait_for_end_threads(threads: List[Thread]):
    """Endless loop that wait for ending the threads."""
    while any(map(Thread.is_alive, threads)):
        time.sleep(1)


def set_thread_name_with_prefix(suffix):
    name = current_thread().name
    current_thread().name = f"{name.rsplit('_', 1)[0]}-{suffix}"
