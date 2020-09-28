from threading import current_thread


def set_thread_name_with_prefix(suffix):
    name = current_thread().name
    current_thread().name = f"{name.rsplit('_', 1)[0]}-{suffix}"
