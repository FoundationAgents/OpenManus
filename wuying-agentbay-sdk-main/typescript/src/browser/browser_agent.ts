import { Session } from '../session';
import { Browser } from './browser';
import { BrowserError } from '../exceptions';
import { log } from '../utils/logger';

// Options interfaces
export interface ActOptions {
  action: string;
  timeoutMS?: number;
  iframes?: boolean;
  domSettleTimeoutMS?: number;
  variables?: Record<string, string>;
  use_vision?: boolean;
}

export interface ObserveOptions {
  instruction: string;
  iframes?: boolean;
  domSettleTimeoutMS?: number;
  use_vision?: boolean;
}

export interface ExtractOptions<T = any> {
  instruction: string;
  schema: new (...args: any[]) => T;
  use_text_extract?: boolean;
  selector?: string;
  iframe?: boolean;
  domSettleTimeoutMS?: number;
  use_vision?: boolean;
}

export class ActResult {
  success: boolean;
  message: string;
  action?: string;
  constructor(success: boolean, message: string, action?: string) {
    this.success = success;
    this.message = message;
    this.action = action;
  }
}

export class ObserveResult {
  selector: string;
  description: string;
  method: string;
  args: Record<string, any>;
  constructor(selector: string, description: string, method: string, args: Record<string, any>) {
    this.selector = selector;
    this.description = description;
    this.method = method;
    this.args = args;
  }
}

export class BrowserAgent {
  private session: Session;
  private browser: Browser;

  constructor(session: Session, browser: Browser) {
    this.session = session;
    this.browser = browser;
  }

  /** ------------------ ACT ------------------ **/
  async act(options: ActOptions, page: any): Promise<ActResult> {
    if (!this.browser.isInitialized()) throw new BrowserError("Browser must be initialized before calling act.");
    const [pageId, contextId] = await this._getPageAndContextIndexAsync(page);

    const args: Record<string, any> = {
      context_id: contextId,
      page_id: pageId,
      action: options.action,
      variables: options.variables,
      timeout_ms: options.timeoutMS,
      iframes: options.iframes,
      dom_settle_timeout_ms: options.domSettleTimeoutMS,
      use_vision: options.use_vision
    };
    const task_name = options.action;
    log(`${task_name}`);
  
    const response = await this._callMcpTool("page_use_act", args);

    if (response.success && response.data) {
      const data = typeof response.data === 'string' ? JSON.parse(response.data) : response.data;
      return new ActResult(true, JSON.stringify(data), options.action);
    }
    return new ActResult(false, response.errorMessage || "");
  }

  async actAsync(options: ActOptions, page: any): Promise<ActResult> {
    if (!this.browser.isInitialized()) throw new BrowserError("Browser must be initialized before calling actAsync.");

    const [pageId, contextId] = await this._getPageAndContextIndexAsync(page);
    const args: Record<string, any> = {
      context_id: contextId,
      page_id: pageId,
      action: options.action,
      variables: options.variables,
      timeout_ms: options.timeoutMS,
      iframes: options.iframes,
      dom_settle_timeout_ms: options.domSettleTimeoutMS,
      use_vision: options.use_vision
    };
    const task_name = options.action;
    log(`${task_name}`);

    const startResp = await this._callMcpTool("page_use_act_async", args);
    if (!startResp.success) throw new BrowserError("Failed to start act task");

    const { task_id } = JSON.parse(startResp.data);
    let retries = 30;

    while (retries-- > 0) {
      await this._delay(5000);
      const pollResp = await this._callMcpTool("page_use_get_act_result", { task_id });

      if (pollResp.success && pollResp.data) {
        const data = typeof pollResp.data === 'string' ? JSON.parse(pollResp.data) : pollResp.data;
        const steps = data.steps || [];
        const is_done = data.is_done || false;
        const success = !!data.success;
        if (is_done) {
          const msg = steps.length ? JSON.stringify(steps) : "No actions have been executed.";
          log(`Task ${task_id}:${task_name} is done. Success=${success}. ${msg}`);
          return new ActResult(success, msg, options.action);
        } else {
          if (steps.length) {
            log(`Task ${task_id}:${task_name} progress: ${steps.length} steps done. Details: ${JSON.stringify(steps)}`);
          } else {
            log(`Task ${task_id}:${task_name} No actions have been executed yet.`);
          }
        }
      }
    }
    throw new BrowserError(`Task ${task_id}: Act timed out`);
  }

  /** ------------------ OBSERVE ------------------ **/
  async observe(options: ObserveOptions, page: any): Promise<[boolean, ObserveResult[]]> {
    if (!this.browser.isInitialized()) throw new BrowserError("Browser must be initialized before calling observe.");
    const [pageId, contextId] = await this._getPageAndContextIndexAsync(page);

    const args: Record<string, any> = {
      context_id: contextId,
      page_id: pageId,
      instruction: options.instruction,
      iframes: options.iframes,
      dom_settle_timeout_ms: options.domSettleTimeoutMS,
      use_vision: options.use_vision
    };

    const response = await this._callMcpTool("page_use_observe", args);
    if (response.success && response.data) {
      const data = typeof response.data === 'string' ? JSON.parse(response.data) : response.data;
      const results: ObserveResult[] = [];

      for (const item of data) {
        let argsParsed: any;
        try {
          argsParsed = typeof item.arguments === 'string' ? JSON.parse(item.arguments) : item.arguments;
        } catch {
          log(`Warning: Could not parse arguments JSON: ${item.arguments}`);
          argsParsed = item.arguments;
        }
        results.push(new ObserveResult(item.selector || "", item.description || "", item.method || "", argsParsed));
      }
      return [true, results];
    }
    return [false, []];
  }

  async observeAsync(options: ObserveOptions, page: any): Promise<[boolean, ObserveResult[]]> {
    return this.observe(options, page);
  }

  /** ------------------ EXTRACT ------------------ **/
  async extract<T>(options: ExtractOptions<T>, page: any): Promise<[boolean, T | null]> {
    if (!this.browser.isInitialized()) throw new BrowserError("Browser must be initialized before calling extract.");
    const [pageId, contextId] = await this._getPageAndContextIndexAsync(page);

    const args: Record<string, any> = {
      context_id: contextId,
      page_id: pageId,
      instruction: options.instruction,
      field_schema: `schema: ${JSON.stringify({ name: options.schema.name })}`,
      use_text_extract: options.use_text_extract,
      use_vision: options.use_vision,
      selector: options.selector,
      iframe: options.iframe,
      dom_settle_timeout_ms: options.domSettleTimeoutMS
    };

    const response = await this._callMcpTool("page_use_extract", args);
    if (response.success && response.data) {
      const data = typeof response.data === 'string' ? JSON.parse(response.data) : response.data;
      return [true, data as T];
    }
    return [false, null];
  }

  async extractAsync<T>(options: ExtractOptions<T>, page: any): Promise<[boolean, T | null]> {
    if (!this.browser.isInitialized()) throw new BrowserError("Browser must be initialized before calling extractAsync.");
    const [pageId, contextId] = await this._getPageAndContextIndexAsync(page);

    const args: Record<string, any> = {
      context_id: contextId,
      page_id: pageId,
      instruction: options.instruction,
      field_schema: `schema: ${JSON.stringify({ name: options.schema.name })}`,
      use_text_extract: options.use_text_extract,
      use_vision: options.use_vision,
      selector: options.selector,
      iframe: options.iframe,
      dom_settle_timeout_ms: options.domSettleTimeoutMS
    };

    const startResp = await this._callMcpTool("page_use_extract_async", args);
    if (!startResp.success) throw new BrowserError("Failed to start extract task");

    const { task_id } = JSON.parse(startResp.data);
    let retries = 20;

    while (retries-- > 0) {
      await this._delay(8000);
      const pollResp = await this._callMcpTool("page_use_get_extract_result", { task_id });

      if (pollResp.success && pollResp.data) {
        const data = typeof pollResp.data === 'string' ? JSON.parse(pollResp.data) : pollResp.data;
        return [true, data as T];
      }
      log(`Task ${task_id}: No extract result yet (attempt ${20 - retries}/20)`);
    }
    throw new BrowserError(`Task ${task_id}: Extract timed out`);
  }

  private async _getPageAndContextIndexAsync(page: any): Promise<[string, number]> {
    if (!page) {
      throw new BrowserError("Page is null");
    }

    // Try to use Playwright CDP if available
    try {
      if (page.context && typeof page.context === 'function') {
        const context = page.context();
        if (context && typeof context.newCDPSession === 'function') {
          const cdpSession = await context.newCDPSession(page);
          const targetInfo = await cdpSession.send('Target.getTargetInfo');
          const pageIndex = (targetInfo && targetInfo.targetInfo && targetInfo.targetInfo.targetId) ? targetInfo.targetInfo.targetId : 'default-page-id';
          if (typeof cdpSession.detach === 'function') {
            await cdpSession.detach();
          }

          let contextIndex = 0;
          if (typeof context.browser === 'function') {
            const browserObj = context.browser();
            if (browserObj && typeof browserObj.contexts === 'function') {
              const contexts = browserObj.contexts();
              const idx = contexts.indexOf(context);
              if (idx >= 0) {
                contextIndex = idx;
              }
            }
          }
          return [pageIndex, contextIndex];
        }
      }
    } catch (error) {
      log(`CDP targetId retrieval failed, fallback to defaults: ${error}`);
    }

    // Fallback to defaults if CDP is not available
    const pageIndex = "default-page-id";
    const contextIndex = 0;
    return [pageIndex, contextIndex];
  }

  private async _callMcpTool(toolName: string, args: Record<string, any>) {
    return this.session.callMcpTool(toolName, args);
  }

  private _delay(ms: number) {
    return new Promise(res => setTimeout(res, ms));
  }
}
