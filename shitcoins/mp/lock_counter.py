import multiprocessing


class LockCounter():

    def __init__(
            self,
            counter: multiprocessing.Value,
            lock: multiprocessing.Lock,
            condition: multiprocessing.Condition,
    ):
        self._counter = counter
        self._lock = lock
        self._condition = condition

    def wait(self):
        with self._condition:
            self._condition.wait()

        with self._lock:
            self._counter.value += 1