// Type declarations for Jest
declare function describe(name: string, fn: () => void): void;
declare function beforeEach(fn: () => void | Promise<void>): void;
declare function afterEach(fn: () => void | Promise<void>): void;
declare function it(name: string, fn: () => void | Promise<void>): void;
declare namespace it {
  function only(name: string, fn: () => void | Promise<void>): void;
}
declare function expect(actual: any): any;
