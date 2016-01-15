# pyforth
A minimal implementation of the FORTH language, written in Python.

This is nothing more than a language implementation experiment.

The aim is to see what the minimum subset of the Forth VM and language needs to be implemented, 
in order to boot a credible language, such that the booted language could then be used
to boot the rest of the language. i.e, how much of Forth do you need to implement
natively, to be able to write the rest of Forth in Forth itself?

The language is not designed to be efficient, standards compliant or complete.
It is merely an experiment in language implementation, to inform other projects

## Current Status

All core data structures implemented (dictionary, stacks, variables)

Minimal I/O working, complete with mocked versions for auto test.

Minimal unit test suite in place for smoke-testing and regression testing.

Core mathematical and logical operations (16 bit) implemented and working.

A very basic REPL shell (Read, Execute, Print, Loop) implemented and working.

Not much else is implemented.

## Running the tests

    python tests.py

## Running the REPL

    python forth.py
    STAR EMIT
    * Ok




