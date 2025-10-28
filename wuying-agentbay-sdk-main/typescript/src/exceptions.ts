/**
 * Base exception for all AgentBay SDK errors.
 */
export class AgentBayError extends Error {
  extra: Record<string, any>;

  constructor(message?: string, extra: Record<string, any> = {}) {
    const errorMessage = message || "AgentBayError";
    super(errorMessage);
    this.name = "AgentBayError";
    this.extra = extra;
    Object.setPrototypeOf(this, AgentBayError.prototype);
  }
}

/**
 * Raised when there is an authentication error.
 */
export class AuthenticationError extends AgentBayError {
  constructor(
    message = "Authentication failed",
    extra: Record<string, any> = {}
  ) {
    super(message, extra);
    this.name = "AuthenticationError";
    Object.setPrototypeOf(this, AuthenticationError.prototype);
  }
}

/**
 * Raised when there is an error with the API.
 */
export class APIError extends AgentBayError {
  statusCode?: number;

  constructor(
    message = "API error",
    statusCode?: number,
    extra: Record<string, any> = {}
  ) {
    super(message, extra);
    this.name = "APIError";
    this.statusCode = statusCode;
    Object.setPrototypeOf(this, APIError.prototype);
  }
}

/**
 * Raised for errors related to file operations.
 */
export class FileError extends AgentBayError {
  constructor(
    message = "File operation error",
    extra: Record<string, any> = {}
  ) {
    super(message, extra);
    this.name = "FileError";
    Object.setPrototypeOf(this, FileError.prototype);
  }
}

/**
 * Raised for errors related to command execution.
 */
export class CommandError extends AgentBayError {
  constructor(
    message = "Command execution error",
    extra: Record<string, any> = {}
  ) {
    super(message, extra);
    this.name = "CommandError";
    Object.setPrototypeOf(this, CommandError.prototype);
  }
}

/**
 * Raised for errors related to session operations.
 */
export class SessionError extends AgentBayError {
  constructor(message = "Session error", extra: Record<string, any> = {}) {
    super(message, extra);
    this.name = "SessionError";
    Object.setPrototypeOf(this, SessionError.prototype);
  }
}

/**
 * Raised for errors related to OSS operations.
 */
export class OssError extends AgentBayError {
  constructor(
    message = "OSS operation error",
    extra: Record<string, any> = {}
  ) {
    super(message, extra);
    this.name = "OssError";
    Object.setPrototypeOf(this, OssError.prototype);
  }
}

/**
 * Raised for errors related to application operations.
 */
export class ApplicationError extends AgentBayError {
  constructor(
    message = "Application operation error",
    extra: Record<string, any> = {}
  ) {
    super(message, extra);
    this.name = "ApplicationError";
    Object.setPrototypeOf(this, ApplicationError.prototype);
  }
}

/**
 * Raised for errors related to UI operations.
 */
export class UIError extends AgentBayError {
  constructor(message = "UI operation error", extra: Record<string, any> = {}) {
    super(message, extra);
    this.name = "UIError";
    Object.setPrototypeOf(this, UIError.prototype);
  }
}

/**
 * Raised for errors related to browser operations.
 */
export class BrowserError extends AgentBayError {
  constructor(
    message = "Browser operation error",
    extra: Record<string, any> = {}
  ) {
    super(message, extra);
    this.name = "BrowserError";
    Object.setPrototypeOf(this, BrowserError.prototype);
  }
}
