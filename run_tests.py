#!/usr/bin/env python

# The purpose of this script is to run all doctests in a single way that loads
# everything as modules to support relative imports.
# To be used with tox or virtualenv.

import doctest
import importlib

modules = [
    "pyghost.api_client",
    "pyghost.app_schema",
    "pyghost.utils",
]

runner = doctest.DocTestRunner(verbose=True)
finder = doctest.DocTestFinder(verbose=True, exclude_empty=False)

for module in modules:
    for test in finder.find(importlib.import_module(module)):
        runner.run(test)

# return a tuple (f, t), where f is the total number of failed examples, and t is the total number of tried examples.
test_result = runner.summarize()
exit(test_result[0])
