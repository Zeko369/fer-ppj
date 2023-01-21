#!/usr/bin/env zx
//@ts-check

import "zx/globals";
$.verbose = false;

import { readdir } from "node:fs/promises";
import { join } from "node:path";
import c from "chalk";

let passed = 0;
const failed = [];
const errored = [];

const files = await readdir(join(__dirname, "./tests"));
for (const file of files) {
  console.log(`----- Testing ${file} -----`);

  try {
    await $`python3 ./FRISCGenerator.py ./tests/${file}/a.frisc < ./tests/${file}/test.in`;
  } catch (err) {
    console.log(c.red(`Failed to generate frisc code`));
    errored.push(file);
    continue;
  }

  await $`node vm/main.js < ./tests/${file}/a.frisc > ./tests/${file}/my.out 2> ./tests/${file}/my.err`;

  try {
    await $`diff ./tests/${file}/my.out ./tests/${file}/test.out`;
    console.log(c.green("Passed"));
    passed++;
  } catch (error) {
    console.log(c.red(`Test ${file} failed`));
    failed.push(file);
  }
}

console.log("");
console.log(c.bold(`Passed ${passed} / ${files.length} tests`));
console.log("");

errored.forEach((file) => {
  console.log(`${c.bold("Compiler errored")} [${file}]:`);
  console.log(`nr compiler:watch ./tests/${file}/test.in`);
});

failed.forEach((file) => {
  console.log(`${c.bold("Runtime wrong")} [${file}]:`);
  console.log(`nr compiler:watch ./tests/${file}/test.in`);
});
