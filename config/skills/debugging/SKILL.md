---
name: debugging
description: Debugs and fixes code issues. Use when user reports errors, bugs, or unexpected behavior in code.
keywords:
  - debug
  - fix
  - error
  - bug
  - unexpected behavior
allowed-tools:
  - PythonExecute
  - Bash
  - Read
  - StrReplaceEditor
---

# Debugging

## Instructions

When debugging, follow this systematic approach:

1. **Understand the Problem**
   - Read error messages and stack traces carefully
   - Identify the exact error type and location
   - Understand what the user expected vs. what happened
   - Gather context about when the issue occurs

2. **Investigate the Code**
   - Read relevant source files
   - Trace the execution path leading to the error
   - Check for common issues:
     - Typo or syntax error
     - Missing imports or dependencies
     - Incorrect variable scope or naming
     - Type mismatch or None/undefined values
     - Logic errors in conditionals or loops

3. **Reproduce and Isolate**
   - If possible, create a minimal reproduction case
   - Add print statements or logging to trace execution
   - Use PythonExecute to test suspected problematic code
   - Isolate the specific line or function causing the issue

4. **Fix the Issue**
   - Implement the smallest fix that resolves the problem
   - Test the fix to verify it works
   - Ensure the fix doesn't break other functionality
   - Add comments explaining the fix if not obvious

5. **Provide Explanation**
   - Explain what the root cause was
   - Describe how the fix addresses it
   - Suggest how to prevent similar issues
   - Include code example of the fix if applicable

Always handle errors gracefully. When you encounter an error during debugging:
1. Log the full error message and traceback
2. Analyze the error before proceeding
3. Try alternative approaches if one fails
4. If stuck, explain the current state and what you've tried
