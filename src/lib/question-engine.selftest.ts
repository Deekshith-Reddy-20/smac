import {
  assessUtterance,
  mergeUtterance,
  normalizeQuestion,
} from "./question-engine";

const cases: Array<[string, boolean, boolean]> = [
  ["What is Python?", true, true],
  ["Can you explain", true, false],
  ["Can you explain your", true, false],
  ["Can you explain your project", true, true],
  ["Tell me about your project", true, true],
  ["Why did you use FastAPI", true, true],
  ["Okay", false, true],
  ["Let's move on", false, true],
  ["Yes that's good", false, true],
  ["Can you explain the project you worked on during your internship, what problem it solved, what technologies you used, and what your contribution was?", true, true],
  ["Why did you use it?", true, true],
  ["What dataset did you use?", true, true],
];

const failures: string[] = [];
for (const [text, isQuestion, complete] of cases) {
  const result = assessUtterance(text);
  if (result.isQuestion !== isQuestion || result.complete !== complete) {
    failures.push(`${JSON.stringify(text)} => ${JSON.stringify(result)} expected isQuestion=${isQuestion} complete=${complete}`);
  }
}

const merged = mergeUtterance("Can you explain", "the project that you mentioned in your resume?");
if (!/can you explain the project that you mentioned in your resume/i.test(merged)) {
  failures.push(`merge failed: ${merged}`);
}

if (normalizeQuestion("What is Python?") !== normalizeQuestion("what is python")) {
  failures.push("normalize failed");
}

if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}
console.log("question-engine selftest PASS", cases.length, "cases");
