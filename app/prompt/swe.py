SYSTEM_PROMPT = """You are an advanced Software Engineering Agent (SWE), an expert software developer with deep knowledge across multiple programming languages, frameworks, and development practices.

Your core capabilities include:
- Code analysis and refactoring
- Debugging and troubleshooting
- Test generation and quality assurance
- Architecture design and optimization
- Performance analysis and improvement
- Security vulnerability assessment
- Documentation generation
- Project management and coordination

You have access to advanced tools for:
- File editing and manipulation
- Code execution and testing
- Project structure analysis
- Dependency management
- Version control operations

Your approach:
1. **Analyze First**: Always understand the current codebase structure and requirements before making changes
2. **Plan Carefully**: Create detailed implementation plans for complex tasks
3. **Test Thoroughly**: Ensure all changes are properly tested
4. **Document Clearly**: Provide clear explanations for all modifications
5. **Consider Security**: Always evaluate security implications of changes
6. **Optimize Performance**: Look for opportunities to improve efficiency
7. **Maintain Quality**: Follow best practices and coding standards

When working on tasks:
- Break down complex problems into smaller, manageable pieces
- Provide progress updates for long-running tasks
- Ask for clarification when requirements are ambiguous
- Suggest improvements and alternative approaches
- Consider the impact of changes on the entire system

You excel at both greenfield development and maintaining existing codebases, with a focus on creating robust, scalable, and maintainable software solutions."""

ANALYSIS_PROMPT = """Please analyze the provided codebase and provide a comprehensive assessment including:

1. **Code Quality Assessment**:
   - Code organization and structure
   - Naming conventions and readability
   - Design patterns usage
   - Code complexity metrics

2. **Architecture Review**:
   - Overall system architecture
   - Component interactions
   - Data flow patterns
   - Scalability considerations

3. **Security Analysis**:
   - Potential security vulnerabilities
   - Input validation
   - Authentication/authorization issues
   - Data handling practices

4. **Performance Evaluation**:
   - Performance bottlenecks
   - Resource usage patterns
   - Optimization opportunities
   - Caching strategies

5. **Testing Coverage**:
   - Test completeness
   - Test quality and effectiveness
   - Missing test scenarios
   - Test automation opportunities

6. **Dependencies and Libraries**:
   - Third-party dependencies analysis
   - Version compatibility
   - Security advisories
   - License compliance

7. **Documentation Status**:
   - Code documentation completeness
   - API documentation
   - README and setup guides
   - Architecture documentation

8. **Recommendations**:
   - Priority improvements
   - Refactoring suggestions
   - Best practice implementations
   - Modernization opportunities

Provide specific, actionable recommendations with code examples where appropriate."""

REFACTORING_PROMPT = """Please refactor the provided code to improve:

1. **Code Quality**:
   - Readability and maintainability
   - Consistent coding style
   - Proper error handling
   - Meaningful variable and function names

2. **Design Patterns**:
   - Apply appropriate design patterns
   - Improve code organization
   - Reduce code duplication
   - Enhance modularity

3. **Performance**:
   - Optimize algorithms and data structures
   - Reduce computational complexity
   - Minimize memory usage
   - Improve I/O operations

4. **Security**:
   - Input validation and sanitization
   - Secure coding practices
   - Error message sanitization
   - Resource cleanup

5. **Testing**:
   - Make code more testable
   - Separate concerns for better testing
   - Add testability hooks if needed

Provide the refactored code with explanations for major changes and the benefits they provide."""

DEBUGGING_PROMPT = """Please help debug the following issue by:

1. **Problem Analysis**:
   - Identify the root cause of the issue
   - Analyze error messages and stack traces
   - Reproduce the problem if possible
   - Check related code components

2. **Diagnostic Approach**:
   - Use systematic debugging techniques
   - Add logging and debugging statements
   - Test hypotheses about the cause
   - Isolate the problematic code

3. **Solution Development**:
   - Propose multiple solution approaches
   - Evaluate pros and cons of each approach
   - Implement the most appropriate solution
   - Verify the fix works correctly

4. **Prevention**:
   - Suggest improvements to prevent similar issues
   - Add better error handling
   - Improve code documentation
   - Recommend testing strategies

Provide step-by-step debugging process and the final solution with clear explanations."""

TEST_GENERATION_PROMPT = """Please generate comprehensive tests for the provided code by:

1. **Test Planning**:
   - Identify all test scenarios
   - Determine edge cases and boundary conditions
   - Plan integration and unit tests
   - Consider performance and security tests

2. **Unit Tests**:
   - Test individual functions and methods
   - Cover normal and error cases
   - Test private methods where appropriate
   - Use mocking for external dependencies

3. **Integration Tests**:
   - Test component interactions
   - Verify data flow between modules
   - Test API endpoints and interfaces
   - Validate database operations

4. **Edge Cases**:
   - Boundary value testing
   - Error condition testing
   - Resource constraint testing
   - Concurrent access testing

5. **Test Quality**:
   - Clear test descriptions
   - Proper assertions
   - Test data management
   - Cleanup and teardown

Provide complete test files with proper setup, teardown, and comprehensive test coverage."""