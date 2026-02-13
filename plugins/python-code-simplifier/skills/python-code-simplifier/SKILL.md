---
name: python-code-simplifier
description:
  "Simplifies and refines Python code for clarity, consistency, and maintainability while preserving
  all functionality. Focuses on recently modified code unless instructed otherwise. Use after
  implementing features, fixing bugs, or modifying Python code to ensure it meets quality standards."
allowed-tools:
  - Read
  - Edit
  - Grep
  - Glob
  - Bash
---

# Python Code Simplifier

Analyze recently modified Python code and apply refinements that improve clarity, consistency, and maintainability while preserving exact functionality.

## When to Use

- After implementing a feature or fixing a bug in Python code
- When Python code feels overly complex or hard to follow
- To clean up code before committing or creating a pull request
- When refactoring Python modules for readability and maintainability

## When NOT to Use

- For non-Python code (TypeScript, Rust, Go, etc.)
- When the task is to add new functionality, not simplify existing code
- For performance optimization — this focuses on clarity, not speed
- When code is already clean and well-structured

## Refinement Principles

### 1. Preserve Functionality

Never change what the code does — only how it does it. All original features, outputs, and behaviors must remain intact.

### 2. Apply Python Standards

Follow established Python coding standards including:

- Use absolute imports with proper sorting (`import` stdlib first, then third-party, then local)
- Prefer explicit function definitions over lambdas for non-trivial logic
- Use type annotations on public function signatures and return types
- Follow proper class patterns with clear `__init__`, explicit attributes, and dataclasses where appropriate
- Use structured error handling — prefer early returns and guard clauses over deeply nested try/except
- Maintain consistent naming: `snake_case` for functions and variables, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants

### 3. Enhance Clarity

Simplify code structure by:

- Reducing unnecessary complexity and nesting
- Eliminating redundant code and abstractions
- Improving readability through clear variable and function names
- Consolidating related logic
- Removing unnecessary comments that describe obvious code
- Preferring early returns over deep nesting — flatten conditional chains with guard clauses
- Choosing clarity over brevity — explicit code is often better than overly compact comprehensions or chained expressions

### 4. Maintain Balance

Avoid over-simplification that could:

- Reduce code clarity or maintainability
- Create overly clever solutions that are hard to understand
- Combine too many concerns into single functions or classes
- Remove helpful abstractions that improve code organization
- Prioritize "fewer lines" over readability (e.g., dense comprehensions, excessive unpacking, overloaded walrus operators)
- Make the code harder to debug or extend

### 5. Focus Scope

Only refine code that has been recently modified or touched in the current session, unless explicitly instructed to review a broader scope.

## Process

1. Identify the recently modified code sections
2. Analyze for opportunities to improve clarity and consistency
3. Apply Python best practices and coding standards
4. Ensure all functionality remains unchanged
5. Verify the refined code is simpler and more maintainable
6. Document only significant changes that affect understanding
