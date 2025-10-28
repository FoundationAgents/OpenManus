import { WhiteList, WhiteListValidator, newContextSync, ContextSync } from '../../src/context-sync';

describe('WhiteListValidator', () => {
  describe('valid paths', () => {
    it('should accept path without wildcards', () => {
      const whitelist: WhiteList = { path: '/src' };
      expect(() => WhiteListValidator.validate(whitelist)).not.toThrow();
    });

    it('should accept path with exclude_paths without wildcards', () => {
      const whitelist: WhiteList = {
        path: '/src',
        excludePaths: ['/node_modules', '/temp']
      };
      expect(() => WhiteListValidator.validate(whitelist)).not.toThrow();
    });

    it('should accept empty path', () => {
      const whitelist: WhiteList = { path: '' };
      expect(() => WhiteListValidator.validate(whitelist)).not.toThrow();
    });

    it('should accept empty exclude_paths', () => {
      const whitelist: WhiteList = { path: '/src', excludePaths: [] };
      expect(() => WhiteListValidator.validate(whitelist)).not.toThrow();
    });
  });

  describe('invalid paths with wildcards', () => {
    it('should reject path with asterisk wildcard', () => {
      const whitelist: WhiteList = { path: '/data/*' };
      expect(() => WhiteListValidator.validate(whitelist)).toThrow(
        'Wildcard patterns are not supported in path. Got: /data/*'
      );
    });

    it('should reject path with double asterisk', () => {
      const whitelist: WhiteList = { path: '/logs/**/*.txt' };
      expect(() => WhiteListValidator.validate(whitelist)).toThrow(
        'Wildcard patterns are not supported in path'
      );
    });

    it('should reject path with question mark', () => {
      const whitelist: WhiteList = { path: '/file?.txt' };
      expect(() => WhiteListValidator.validate(whitelist)).toThrow(
        'Wildcard patterns are not supported in path'
      );
    });

    it('should reject path with brackets', () => {
      const whitelist: WhiteList = { path: '/file[0-9].txt' };
      expect(() => WhiteListValidator.validate(whitelist)).toThrow(
        'Wildcard patterns are not supported in path'
      );
    });

    it('should reject glob pattern', () => {
      const whitelist: WhiteList = { path: '*.json' };
      expect(() => WhiteListValidator.validate(whitelist)).toThrow(
        'Wildcard patterns are not supported in path'
      );
    });
  });

  describe('invalid exclude_paths with wildcards', () => {
    it('should reject exclude_paths with asterisk', () => {
      const whitelist: WhiteList = {
        path: '/src',
        excludePaths: ['*.log']
      };
      expect(() => WhiteListValidator.validate(whitelist)).toThrow(
        'Wildcard patterns are not supported in exclude_paths. Got: *.log'
      );
    });

    it('should reject exclude_paths with pattern', () => {
      const whitelist: WhiteList = {
        path: '/src',
        excludePaths: ['/node_modules', '**/*.tmp']
      };
      expect(() => WhiteListValidator.validate(whitelist)).toThrow(
        'Wildcard patterns are not supported in exclude_paths'
      );
    });
  });
});

describe('ContextSync validation', () => {
  it('should validate policy when creating ContextSync via constructor', () => {
    expect(() => {
      new ContextSync('ctx-123', '/tmp/data', {
        bwList: {
          whiteLists: [{ path: '*.json' }]
        }
      });
    }).toThrow('Wildcard patterns are not supported in path');
  });

  it('should validate policy when creating ContextSync via newContextSync', () => {
    expect(() => {
      newContextSync('ctx-123', '/tmp/data', {
        bwList: {
          whiteLists: [{ path: '/data/*' }]
        }
      });
    }).toThrow('Wildcard patterns are not supported in path');
  });

  it('should validate policy when using withPolicy', () => {
    const contextSync = new ContextSync('ctx-123', '/tmp/data');
    expect(() => {
      contextSync.withPolicy({
        bwList: {
          whiteLists: [{ path: '/src', excludePaths: ['*.log'] }]
        }
      });
    }).toThrow('Wildcard patterns are not supported in exclude_paths');
  });

  it('should allow valid policy', () => {
    expect(() => {
      new ContextSync('ctx-123', '/tmp/data', {
        bwList: {
          whiteLists: [
            { path: '/src', excludePaths: ['/node_modules'] }
          ]
        }
      });
    }).not.toThrow();
  });
});
