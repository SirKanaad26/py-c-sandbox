from logger import logger
import numpy as np
from hello_wrapper_test import CopyArray

class CopyArrayTest:
    def __init__(self):
        self.impl = CopyArray()

    def run_all(self):
        src = np.array([1, 2, 3, 4, 5], dtype=np.int32)

        logger.info("Running overflow variant:")
        res1 = self.impl.call_overflow(src)
        logger.info(f"Result: {res1}")

        logger.info("Running UAF variant:")
        res2 = self.impl.call_uaf(src)
        logger.info(f"Result: {res2}")
