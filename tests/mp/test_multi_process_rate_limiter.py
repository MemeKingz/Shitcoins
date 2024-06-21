import multiprocessing
import time
import unittest
from concurrent.futures import ProcessPoolExecutor

from shitcoins.mp.lock_counter import LockCounter
from shitcoins.mp.multi_process_rate_limiter import MultiProcessRateLimiter



def _wait_for(num: int, lock_counter: LockCounter):
    lock_counter.wait()
    time.sleep(2)


class TestMultiProcessRateLimiter(unittest.TestCase):

    def test_lock_counter_rate_limits_1_req_every_2_secs(self):
        mp_rate_limiter = MultiProcessRateLimiter(max_requests=1, per_seconds=2)
        lock_counter = mp_rate_limiter.get_lock_counter()

        start_time_sec = time.time()
        futures = []
        with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
            for i in range(3):
                futures.append(executor.submit(_wait_for, i, lock_counter))

            while len(futures):
                mp_rate_limiter.cycle()

                for future in futures:
                    if future.done():
                        futures.remove(future)

        finish_time_sec = time.time() - start_time_sec
        self.assertTrue(finish_time_sec > 6)
        self.assertEqual(1, 1)
