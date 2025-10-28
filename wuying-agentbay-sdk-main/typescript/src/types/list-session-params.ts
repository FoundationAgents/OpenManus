import { Session } from "../session";
import { ApiResponse } from "./api-response";

/**
 * Parameters for listing sessions with pagination support
 */
export interface ListSessionParams {
  /** Number of results per page (default: 10) */
  maxResults?: number;

  /** Token for the next page */
  nextToken?: string;

  /** Labels to filter by */
  labels: Record<string, string>;
}

/**
 * Result type for session listing with pagination information
 */
export interface SessionListResult extends ApiResponse {
  /** Array of session IDs */
  sessionIds: string[];

  /** Token for the next page (if available) */
  nextToken?: string;

  /** Number of results per page */
  maxResults?: number;

  /** Total number of results */
  totalCount?: number;
}

/**
 * Helper function to create ListSessionParams with default values
 */
export function createListSessionParams(
  labels: Record<string, string> = {}
): ListSessionParams {
  return {
    maxResults: 10,
    labels,
  };
}
