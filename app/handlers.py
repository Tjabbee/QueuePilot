"""Centralized handler registry for site type dispatching."""

from sites import momentum, kjellberg

HANDLERS = {
    "momentum": momentum.run,
    "vitec": kjellberg.run,
    "kjellberg": kjellberg.run,  # legacy alias
}
