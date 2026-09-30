import { useState } from "react";

function add(a, b) {
  return helper(a) + b;
}

function helper(n) {
  return n + 1;
}

const multiply = (a, b) => {
  return a * b;
};

class Animal {
  constructor(name) {
    this.name = name;
  }

  speak() {
    return `${this.name} makes a sound`;
  }
}

class Dog extends Animal {
  speak() {
    return this.bark() + super.speak();
  }

  bark() {
    return "Woof! ";
  }
}
