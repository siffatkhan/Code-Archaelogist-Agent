"""A small sample module used to test python_parser.py."""

import os
from typing import Optional


def add(a: int, b: int) -> int:
    return helper(a) + b


def helper(n: int) -> int:
    return n + 1


class Animal:
    def __init__(self, name: str):
        self.name = name

    def speak(self) -> str:
        return f"{self.name} makes a sound"


class Dog(Animal):
    def speak(self) -> str:
        base_sound = super().speak()
        return self.bark() + base_sound

    def bark(self) -> str:
        return "Woof! "
