# Glossary

The shared language of Sketch. Use these terms in code, tests, issues and comments.

- **system failure**: a failure the test runner reports that is not a test: the runner could not launch, install or start (Xcode writes it as a Test Case under a "System Failures" suite). It is never counted as passed or failed, and alone it means CANNOT RUN.
- **story issue**: the tracker issue for one story, titled "Story <n>: <title>".
- **task issue**: the tracker issue for one task of a story, titled "t-<n>: <title>", a sub-issue of its story issue. Task ids restart at t-1 in every story, so a task issue belongs to a story only when it was created after that story's issue and its title matches the tasks file.
