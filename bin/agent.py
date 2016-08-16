#! /usr/bin/env python

import sys
import runpy

sys.path.insert(0, "/Users/jblackford/Development/agent")

if __name__ == '__main__':
    runpy.run_module("agent.main", run_name="__main__")
