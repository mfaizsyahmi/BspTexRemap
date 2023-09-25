import time
from collections.abc import Iterator
from contextlib import contextmanager
import logging

log = logging.getLogger(__name__)
def debug_dpg_item(tag):
    log.debug("CONFIG: {!r}", dpg.get_item_configuration(tag))
    log.debug("INFO:   {!r}", dpg.get_item_info(tag))
    log.debug("STATE:  {!r}", dpg.get_item_state(tag))
    log.debug("VALUE:  {!r}", dpg.get_value(tag))
    log.debug()

# https://stackoverflow.com/a/74502089
@contextmanager
def time_it() -> Iterator[None]:
    tic: float = time.perf_counter()
    try:
        yield
    finally:
        toc: float = time.perf_counter()
        log.debug(f"Computation time = {1000*(toc - tic):.3f}ms")

def dump_materialset(matset, msg=None):
    if msg: print(msg)
    for mat in matset.MATCHARS:
        print(f"{mat}: {matset[mat]}")
