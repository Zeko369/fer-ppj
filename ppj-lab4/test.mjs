#!/usr/bin/env zx
//@ts-check

import "zx/globals";
$.verbose = false;

import { readdir } from "node:fs/promises";
import { join } from "node:path";

let passed = 0;
const failed = [];
const errored = [];

const files = await readdir(join(__dirname, "./tests"));
for (const file of files) {
  console.log(`----- Testing ${file} -----`);

  try {
    await $`python3 ./FRISCGenerator.py ./tests/${file}/a.frisc < ./tests/${file}/test.in`;
  } catch (err) {
    console.log(`Failed to generate frisc code`);
    errored.push(file);
    continue;
  }

  await $`node vm/main.js < ./tests/${file}/a.frisc > ./tests/${file}/my.out 2> ./tests/${file}/my.err`;

  try {
    await $`diff ./tests/${file}/my.out ./tests/${file}/test.out`;
    console.log("Passed");
    passed++;
  } catch (error) {
    console.log(`Test ${file} failed`);
    failed.push(file);
  }
}

console.log("");
console.log(`Passed ${passed} / ${files.length} tests`);

errored.forEach((file) => {
  console.log(`Compiler errored [${file}] -> \nnr compiler:watch ./tests/${file}/test.in`);
});

failed.forEach((file) => {
  console.log(`Runtime wrong [${file}] -> \nnr compiler:watch ./tests/${file}/test.in`);
});
