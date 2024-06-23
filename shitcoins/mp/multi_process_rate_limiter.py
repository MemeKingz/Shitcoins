import multiprocessing
import time
from collections import deque

from shitcoins.mp.lock_counter import LockCounter


class MultiProcessRateLimiter:

    def __init__(
            self,
            max_requests: int = 100,
            per_seconds: int = 60,
            *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self._max_requests = max_requests
        self._per_seconds = per_seconds
        self._manager = multiprocessing.Manager()
        self._counter = self._manager.Value('b', 0)
        self._lock = self._manager.Lock()
        self._condition = self._manager.Condition()

        self._call_counts: [] = deque(maxlen=per_seconds)
        self._last_counter = 0
        self._last_cycle = 0

    def cycle(self):
        with self._lock:
            counter_value = self._counter.value

        current_time_sec: float = time.time()
        time_diff = current_time_sec - self._last_cycle
        # we use the counter.value to find out how many calls we have made since the last time we checked
        diff = self._counter.value - self._last_counter
        if diff > 0:
            self._last_counter = counter_value
            for i in range(diff):
                self.call(current_time_sec)

        current_calls = self.calculate_current_calls(current_time_sec)

        # remaining calls is the amount of calls still permitted, hence release many multiprocessors using condition
        remaining_calls = self._max_requests - current_calls
        with self._condition:
            self._condition.notify(remaining_calls)

        next_slot = self._per_seconds - (current_time_sec - self._call_counts[0][0]) if len(self._call_counts) else 0

        if time_diff > 10:
            self._last_cycle = current_time_sec
            print(f"Calls in the last {self._per_seconds} seconds: "
                  f"current={current_calls} :: available={remaining_calls} "
                  f":: total={counter_value} :: next slot in={next_slot:.0f}s")

        time.sleep(0.5)

    def call(self, current_time_sec: float):
        if len(self._call_counts) == 0 or current_time_sec - self._call_counts[-1][0] >= 1:
            # create a new entry if none exists this second
            self._call_counts.append((current_time_sec, 1))
        else:
            # if there is an entry in the current second, add to the counter of the existing entry
            self._call_counts[-1] = (self._call_counts[-1][0], self._call_counts[-1][1] + 1)

    def calculate_current_calls(self, current_time_sec):
        # clean up calls that are older than the time limit
        while self._call_counts and current_time_sec - self._call_counts[0][0] > self._per_seconds:
            self._call_counts.popleft()

        # sum up the calls in the current time window
        current_calls = sum(count for _, count in self._call_counts)
        return current_calls

    def get_lock_counter(self):
        return LockCounter(
            counter=self._counter,
            lock=self._lock,
            condition=self._condition,
        )
