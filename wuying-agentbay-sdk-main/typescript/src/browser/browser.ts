import { Session } from '../session';
import { BrowserAgent } from './browser_agent';
import { BrowserError } from '../exceptions';
import { BROWSER_DATA_PATH } from '../config';
import { InitBrowserRequest } from '../api/models/InitBrowserRequest';
import { log } from '../utils/logger';

export interface BrowserViewport {
  width: number;
  height: number;
}

export interface BrowserScreen {
  width: number;
  height: number;
}

export interface BrowserFingerprint {
  devices?: Array<'desktop' | 'mobile'>;
  operatingSystems?: Array<'windows' | 'macos' | 'linux' | 'android' | 'ios'>;
  locales?: string[];
}

export interface BrowserProxy {
  type: 'custom' | 'wuying';
  server?: string;
  username?: string;
  password?: string;
  strategy?: 'restricted' | 'polling';
  pollsize?: number;
  toMap(): Record<string, any>;
}

export class BrowserProxyClass implements BrowserProxy {
  type: 'custom' | 'wuying';
  server?: string;
  username?: string;
  password?: string;
  strategy?: 'restricted' | 'polling';
  pollsize?: number;

  constructor(
    proxyType: 'custom' | 'wuying',
    server?: string,
    username?: string,
    password?: string,
    strategy?: 'restricted' | 'polling',
    pollsize?: number
  ) {
    this.type = proxyType;
    this.server = server;
    this.username = username;
    this.password = password;
    this.strategy = strategy;
    this.pollsize = pollsize;

    // Validation
    if (proxyType !== 'custom' && proxyType !== 'wuying') {
      throw new Error('proxy_type must be custom or wuying');
    }

    if (proxyType === 'custom' && !server) {
      throw new Error('server is required for custom proxy type');
    }

    if (proxyType === 'wuying' && !strategy) {
      throw new Error('strategy is required for wuying proxy type');
    }

    if (proxyType === 'wuying' && strategy !== 'restricted' && strategy !== 'polling') {
      throw new Error('strategy must be restricted or polling for wuying proxy type');
    }

    if (proxyType === 'wuying' && strategy === 'polling' && pollsize !== undefined && pollsize <= 0) {
      throw new Error('pollsize must be greater than 0 for polling strategy');
    }
  }

  toMap(): Record<string, any> {
    const proxyMap: Record<string, any> = {
      type: this.type
    };

    if (this.type === 'custom') {
      proxyMap.server = this.server;
      if (this.username) {
        proxyMap.username = this.username;
      }
      if (this.password) {
        proxyMap.password = this.password;
      }
    } else if (this.type === 'wuying') {
      proxyMap.strategy = this.strategy;
      if (this.strategy === 'polling') {
        proxyMap.pollsize = this.pollsize;
      }
    }

    return proxyMap;
  }

  static fromMap(m: Record<string, any> | null | undefined): BrowserProxyClass | null {
    if (!m || typeof m !== 'object') {
      return null;
    }

    const proxyType = m.type;
    if (!proxyType) {
      return null;
    }

    if (proxyType === 'custom') {
      return new BrowserProxyClass(
        proxyType,
        m.server,
        m.username,
        m.password
      );
    } else if (proxyType === 'wuying') {
      return new BrowserProxyClass(
        proxyType,
        undefined,
        undefined,
        undefined,
        m.strategy,
        m.pollsize || 10
      );
    } else {
      throw new Error(`Unsupported proxy type: ${proxyType}`);
    }
  }
}

export interface BrowserOption {
  persistentPath?: string;
  useStealth?: boolean;
  userAgent?: string;
  viewport?: BrowserViewport;
  screen?: BrowserScreen;
  fingerprint?: BrowserFingerprint;
  solveCaptchas?: boolean;
  proxies?: BrowserProxy[];
  /** Path to the extensions directory. Defaults to "/tmp/extensions/" */
  extensionPath?: string;
}

export class BrowserOptionClass implements BrowserOption {
  persistentPath?: string;
  useStealth?: boolean;
  userAgent?: string;
  viewport?: BrowserViewport;
  screen?: BrowserScreen;
  fingerprint?: BrowserFingerprint;
  solveCaptchas?: boolean;
  proxies?: BrowserProxy[];
  extensionPath?: string;

  constructor(
    useStealth = false,
    userAgent?: string,
    viewport?: BrowserViewport,
    screen?: BrowserScreen,
    fingerprint?: BrowserFingerprint,
    solveCaptchas = false,
    proxies?: BrowserProxy[],
  ) {
    this.useStealth = useStealth;
    this.userAgent = userAgent;
    this.viewport = viewport;
    this.screen = screen;
    this.fingerprint = fingerprint;
    this.solveCaptchas = solveCaptchas;
    this.extensionPath = "/tmp/extensions/";

    // Validate proxies list items
    if (proxies !== undefined) {
      if (!Array.isArray(proxies)) {
        throw new Error('proxies must be a list');
      }
      if (proxies.length > 1) {
        throw new Error('proxies list length must be limited to 1');
      }
    }

    // Set proxies after validation
    this.proxies = proxies;
  }

  toMap(): Record<string, any> {
    const optionMap: Record<string, any> = {};
    if (process.env.AGENTBAY_BROWSER_BEHAVIOR_SIMULATE) {
      optionMap['behaviorSimulate'] = (process.env.AGENTBAY_BROWSER_BEHAVIOR_SIMULATE !== "0") as boolean;
    }
    if (this.useStealth !== undefined) {
      optionMap['useStealth'] = this.useStealth;
    }
    if (this.userAgent !== undefined) {
      optionMap['userAgent'] = this.userAgent;
    }
    if (this.viewport !== undefined) {
      optionMap['viewport'] = { width: this.viewport.width, height: this.viewport.height };
    }
    if (this.screen !== undefined) {
      optionMap['screen'] = { width: this.screen.width, height: this.screen.height };
    }
    if (this.fingerprint !== undefined) {
      const fp: Record<string, any> = {};
      if (this.fingerprint.devices) fp['devices'] = this.fingerprint.devices;
      if (this.fingerprint.operatingSystems) fp['operatingSystems'] = this.fingerprint.operatingSystems;
      if (this.fingerprint.locales) fp['locales'] = this.fingerprint.locales;
      optionMap['fingerprint'] = fp;
    }
    if (this.solveCaptchas !== undefined) {
      optionMap['solveCaptchas'] = this.solveCaptchas;
    }
    if (this.proxies !== undefined) {
      optionMap['proxies'] = this.proxies.map(proxy => proxy.toMap());
    }
    if (this.extensionPath !== undefined) {
      optionMap['extensionPath'] = this.extensionPath;
    }
    return optionMap;
  }

  fromMap(m: Record<string, any> | null | undefined): BrowserOptionClass {
    const map = m || {};
    if (map.useStealth !== undefined) {
      this.useStealth = map.useStealth;
    } else {
      this.useStealth = false;
    }
    if (map.userAgent !== undefined) {
      this.userAgent = map.userAgent;
    }
    if (map.viewport !== undefined) {
      this.viewport = { width: map.viewport.width, height: map.viewport.height };
    }
    if (map.screen !== undefined) {
      this.screen = { width: map.screen.width, height: map.screen.height };
    }
    if (map.fingerprint !== undefined) {
      const fp: BrowserFingerprint = {};
      if (map.fingerprint.devices) fp.devices = map.fingerprint.devices;
      if (map.fingerprint.operatingSystems) fp.operatingSystems = map.fingerprint.operatingSystems;
      if (map.fingerprint.locales) fp.locales = map.fingerprint.locales;
      this.fingerprint = fp;
    }
    if (map.solveCaptchas !== undefined) {
      this.solveCaptchas = map.solveCaptchas;
    }
    if (map.proxies !== undefined) {
      const proxyList = map.proxies;
      if (proxyList.length > 1) {
        throw new Error('proxies list length must be limited to 1');
      }
      this.proxies = proxyList.map((proxyData: any) => {
        // If it's already a BrowserProxyClass instance, return it
        if (proxyData instanceof BrowserProxyClass) {
          return proxyData;
        }
        // Otherwise, convert from map
        return BrowserProxyClass.fromMap(proxyData);
      }).filter(Boolean) as BrowserProxy[];
    }
    if (map.extensionPath !== undefined) {
      this.extensionPath = map.extensionPath;
    }
    return this;
  }
}

export class Browser {
  private session: Session;
  private _endpointUrl: string | null = null;
  private _initialized = false;
  private _option: BrowserOptionClass | null = null;
  public agent: BrowserAgent;

  constructor(session: Session) {
    this.session = session;
    this.agent = new BrowserAgent(this.session, this);
  }

  /**
   * Initialize the browser instance with the given options.
   * Returns true if successful, false otherwise.
   */
  initialize(option: BrowserOptionClass | BrowserOption): boolean {
    if (this.isInitialized()) {
      return true;
    }

    try {
      // Use direct API call to initialize browser
      const request = new InitBrowserRequest();
      request.authorization = `Bearer ${this.session.getAPIKey()}`;
      request.persistentPath = BROWSER_DATA_PATH;
      request.sessionId = this.session.getSessionId();

      // Ensure option is a BrowserOptionClass instance
      let browserOption: BrowserOptionClass;
      if (option instanceof BrowserOptionClass) {
        browserOption = option;
      } else {
        // Convert plain object to BrowserOptionClass instance
        browserOption = new BrowserOptionClass();
        browserOption.fromMap(option as Record<string, any>);
      }

      // Map BrowserOption to API BrowserOption payload
      const browserOptionMap = browserOption.toMap();

      // Enable record if session.enableBrowserReplay is true
      if (this.session.enableBrowserReplay) {
        browserOptionMap['enableRecord'] = true;
      }

      if (Object.keys(browserOptionMap).length > 0) {
        request.browserOption = browserOptionMap;
      }

      const response = this.session.getClient().initBrowserSync(request);
      log(`Response from init_browser data:`, response.body?.data);

      const success = response.body?.data?.port !== null && response.body?.data?.port !== undefined;
      if (success) {
        this._initialized = true;
        this._option = browserOption;
        log("Browser instance was successfully initialized.");
      }

      return success;
    } catch (error) {
      console.error("Failed to initialize browser instance:", error);
      this._initialized = false;
      this._endpointUrl = null;
      this._option = null;
      return false;
    }
  }

  /**
   * Initialize the browser instance with the given options asynchronously.
   * Returns true if successful, false otherwise.
   */
  async initializeAsync(option: BrowserOptionClass | BrowserOption): Promise<boolean> {
    if (this.isInitialized()) {
      return true;
    }

    try {
      // Use direct API call to initialize browser
      const request = new InitBrowserRequest();
      request.authorization = `Bearer ${this.session.getAPIKey()}`;
      request.persistentPath = BROWSER_DATA_PATH;
      request.sessionId = this.session.getSessionId();

      // Ensure option is a BrowserOptionClass instance
      let browserOption: BrowserOptionClass;
      if (option instanceof BrowserOptionClass) {
        browserOption = option;
      } else {
        // Convert plain object to BrowserOptionClass instance
        browserOption = new BrowserOptionClass();
        browserOption.fromMap(option as Record<string, any>);
      }

      // Map BrowserOption to API BrowserOption payload
      const browserOptionMap = browserOption.toMap();

      // Enable record if session.enableBrowserReplay is true
      if (this.session.enableBrowserReplay) {
        browserOptionMap['enableRecord'] = true;
      }

      if (Object.keys(browserOptionMap).length > 0) {
        request.browserOption = browserOptionMap;
      }

      const response = await this.session.getClient().initBrowser(request);
      log(`Response from init_browser data:`, response.body?.data);

      const success = response.body?.data?.port !== null && response.body?.data?.port !== undefined;
      if (success) {
        this._initialized = true;
        this._option = browserOption;
        log("Browser instance successfully initialized");
      }

      return success;
    } catch (error) {
      console.error("Failed to initialize browser instance:", error);
      this._initialized = false;
      this._endpointUrl = null;
      this._option = null;
      return false;
    }
  }

  /**
   * Returns the endpoint URL if the browser is initialized, otherwise throws an exception.
   * When initialized, always fetches the latest CDP url from session.getLink().
   */
  async getEndpointUrl(): Promise<string> {
    if (!this.isInitialized()) {
      throw new BrowserError("Browser is not initialized. Cannot access endpoint URL.");
    }

    try {
      const linkResult = await this.session.getLink();
      this._endpointUrl = linkResult.data;
      return this._endpointUrl!;
    } catch (error) {
      throw new BrowserError(`Failed to get endpoint URL from session: ${error}`);
    }
  }

  /**
   * Returns the current BrowserOption used to initialize the browser, or null if not set.
   */
  getOption(): BrowserOptionClass | null {
    return this._option;
  }

  /**
   * Returns true if the browser was initialized, false otherwise.
   */
  isInitialized(): boolean {
    return this._initialized;
  }

  /**
   * Stop the browser instance, internal use only.
   */
  private _stopBrowser(): void {
    if (this.isInitialized()) {
      this.session.callMcpTool("stopChrome", {});
    } else {
      throw new BrowserError("Browser is not initialized. Cannot stop browser.");
    }
  }
}
