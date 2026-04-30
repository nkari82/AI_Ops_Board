declare module "vitest" {
  export type ExpectChain = {
    toThrow: (expected?: unknown) => void | Promise<void>;
    toContain: (expected: unknown) => void;
    toBeDefined: () => void;
    toBe: (expected: unknown) => void;
    toBeInstanceOf: (ctor: abstract new (...args: never[]) => object) => void;
    rejects: {
      toThrow: (expected?: unknown) => Promise<void>;
    };
    not: {
      toContain: (expected: unknown) => void;
    };
  };

  export type ExpectFn = {
    (actual: unknown): ExpectChain;
    fail: (message?: string) => never;
  };

  export const describe: (name: string, fn: () => void) => void;
  export const it: (name: string, fn: () => void | Promise<void>) => void;
  export const beforeEach: (fn: () => void | Promise<void>) => void;
  export const expect: ExpectFn;

  export type MockFn<TArgs extends unknown[] = unknown[], TReturn = unknown> = {
    (...args: TArgs): TReturn;
    mockResolvedValueOnce: (value: unknown) => void;
    mockRejectedValueOnce: (value: unknown) => void;
    mockImplementationOnce: (impl: (...args: TArgs) => TReturn) => void;
  };

  export const vi: {
    fn: <TArgs extends unknown[] = unknown[], TReturn = unknown>() => MockFn<TArgs, TReturn>;
    clearAllMocks: () => void;
  };
}
