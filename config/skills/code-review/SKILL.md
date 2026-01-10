---
name: code-review
description: Reviews code for quality, security, and best practices. Use when user asks to review code, check for bugs, or evaluate code quality.
keywords:
  - review
  - code review
  - quality
  - security
  - best practices
  - bugs
  - evaluate
allowed-tools:
  - Read
  - Grep
  - Glob
---

# Code Review

## Instructions

When reviewing code, follow these steps:

1. **Analyze the Code**
   - Read the file(s) specified
   - Understand the code's purpose and functionality
   - Identify the programming language and patterns used

2. **Check for Issues**
   - **Security**: Look for common vulnerabilities (SQL injection, XSS, hardcoded secrets)
   - **Performance**: Identify potential performance bottlenecks
   - **Code Quality**: Check for code smells, naming conventions, and readability
   - **Best Practices**: Verify adherence to language/framework best practices
   - **Error Handling**: Ensure proper error handling exists

3. **Provide Feedback**
   - List issues found with severity (Critical, High, Medium, Low)
   - For each issue, explain:
     - What the problem is
     - Why it's a problem
     - How to fix it
   - Suggest code improvements and refactoring opportunities
   - Highlight what's done well

4. **Prioritize Findings**
   - Start with critical security issues
   - Follow by high-priority bugs
   - Include performance concerns
   - End with style and minor improvements

Keep reviews constructive and educational. Explain the reasoning behind each suggestion.
