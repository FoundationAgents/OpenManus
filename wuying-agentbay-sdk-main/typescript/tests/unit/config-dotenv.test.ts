/**
 * Test cases for enhanced .env file loading functionality.
 */

import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import { 
  findDotEnvFile, 
  loadDotEnvWithFallback, 
  loadConfig, 
  defaultConfig 
} from '../../src/config';

// Mock process.cwd() for testing
const originalCwd = process.cwd;
const originalEnv = process.env;

describe('Enhanced .env file loading', () => {
  let tempDir: string;
  
  beforeEach(() => {
    // Create temporary directory for testing
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'agentbay-test-'));
    
    // Clean up environment variables
    const envVars = ['AGENTBAY_ENDPOINT', 'AGENTBAY_TIMEOUT_MS'];
    envVars.forEach(key => {
      delete process.env[key];
    });
  });

  afterEach(() => {
    // Restore original cwd and environment
    process.cwd = originalCwd;
    process.env = { ...originalEnv };
    
    // Clean up temporary directory
    if (fs.existsSync(tempDir)) {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });

  describe('findDotEnvFile', () => {
    test('should find .env file in current directory', () => {
      // Create .env file in temp directory
      const envFile = path.join(tempDir, '.env');
      fs.writeFileSync(envFile, 'TEST_VAR=current_dir');
      
      // Find .env file
      const foundFile = findDotEnvFile(tempDir);
      expect(foundFile).toBe(envFile);
      expect(fs.existsSync(foundFile!)).toBe(true);
    });

    test('should find .env file in parent directory', () => {
      // Create .env in parent directory
      const parentEnv = path.join(tempDir, '.env');
      fs.writeFileSync(parentEnv, 'TEST_VAR=parent_dir');
      
      // Create subdirectory
      const subDir = path.join(tempDir, 'subdir');
      fs.mkdirSync(subDir);
      
      // Find .env file from subdirectory
      const foundFile = findDotEnvFile(subDir);
      expect(foundFile).toBe(parentEnv);
    });

    test('should find .env file in git repository root', () => {
      // Create .git directory (simulate git repo)
      const gitDir = path.join(tempDir, '.git');
      fs.mkdirSync(gitDir);
      
      // Create .env in git root
      const gitEnv = path.join(tempDir, '.env');
      fs.writeFileSync(gitEnv, 'TEST_VAR=git_root');
      
      // Create nested subdirectory
      const deepDir = path.join(tempDir, 'src', 'deep');
      fs.mkdirSync(deepDir, { recursive: true });
      
      // Find .env file from deep subdirectory
      const foundFile = findDotEnvFile(deepDir);
      expect(foundFile).toBe(gitEnv);
    });

    test('should return null when .env file is not found', () => {
      // Create subdirectory without .env
      const subDir = path.join(tempDir, 'subdir');
      fs.mkdirSync(subDir);
      
      // No .env file anywhere
      const foundFile = findDotEnvFile(subDir);
      expect(foundFile).toBeNull();
    });
  });

  describe('loadDotEnvWithFallback', () => {
    test('should load .env file from custom path', () => {
      // Create custom .env file
      const customEnv = path.join(tempDir, 'custom.env');
      fs.writeFileSync(customEnv, 'CUSTOM_VAR=custom_value');
      
      // Load custom .env file
      loadDotEnvWithFallback(customEnv);
      
      // Check if variable was loaded
      expect(process.env.CUSTOM_VAR).toBe('custom_value');
    });

    test('should load .env file using fallback search', () => {
      // Create .env in parent
      const parentEnv = path.join(tempDir, '.env');
      fs.writeFileSync(parentEnv, 'FALLBACK_VAR=fallback_value');
      
      // Create subdirectory
      const subDir = path.join(tempDir, 'subdir');
      fs.mkdirSync(subDir);
      
      // Mock process.cwd to return subdirectory
      process.cwd = jest.fn().mockReturnValue(subDir);
      
      // Load .env using fallback
      loadDotEnvWithFallback();
      
      // Check if variable was loaded from parent
      expect(process.env.FALLBACK_VAR).toBe('fallback_value');
    });

    test('should handle missing custom .env file gracefully', () => {
      const nonExistentFile = path.join(tempDir, 'nonexistent.env');
      
      // Should not throw error
      expect(() => loadDotEnvWithFallback(nonExistentFile)).not.toThrow();
    });

    test('should not override existing environment variables', () => {
      // Set environment variable
      process.env.EXISTING_VAR = 'from_environment';
      
      // Create .env file with same variable
      const envFile = path.join(tempDir, '.env');
      fs.writeFileSync(envFile, 'EXISTING_VAR=from_env_file');
      
      // Load .env file
      loadDotEnvWithFallback(envFile);
      
      // Environment variable should not be overridden
      expect(process.env.EXISTING_VAR).toBe('from_environment');
    });
  });

  describe('loadConfig', () => {
    test('should use custom config when provided', () => {
      const customConfig = {
        endpoint: 'custom.endpoint.com',
        timeout_ms: 12345
      };
      
      const result = loadConfig(customConfig);
      expect(result).toEqual(customConfig);
    });

    test('should load config from custom .env file', () => {
      // Create custom .env file
      const customEnv = path.join(tempDir, 'test.env');
      fs.writeFileSync(customEnv, [
        'AGENTBAY_ENDPOINT=wuyingai.ap-southeast-1.aliyuncs.com',
        'AGENTBAY_TIMEOUT_MS=30000'
      ].join('\n'));
      
      // Load config with custom .env file
      const config = loadConfig(undefined, customEnv);
      
      // Check if config was loaded from custom .env file
      expect(config.endpoint).toBe('wuyingai.ap-southeast-1.aliyuncs.com');
      expect(config.timeout_ms).toBe(30000);
    });

    test('should load config with upward .env file search', () => {
      // Create .env in parent
      const parentEnv = path.join(tempDir, '.env');
      fs.writeFileSync(parentEnv, 'AGENTBAY_ENDPOINT=wuyingai.cn-shanghai.aliyuncs.com');
      
      // Create subdirectory
      const subDir = path.join(tempDir, 'project', 'src');
      fs.mkdirSync(subDir, { recursive: true });
      
      // Mock process.cwd to return subdirectory
      process.cwd = jest.fn().mockReturnValue(subDir);
      
      // Load config (should find .env from parent)
      const config = loadConfig();
      
      // Should find .env from parent directory
      expect(config.endpoint).toBe('wuyingai.cn-shanghai.aliyuncs.com');
    });

    test('should handle invalid timeout values gracefully', () => {
      // Create .env with invalid timeout
      const envFile = path.join(tempDir, '.env');
      fs.writeFileSync(envFile, 'AGENTBAY_TIMEOUT_MS=invalid_number');
      
      // Load config
      const config = loadConfig(undefined, envFile);
      
      // Should use default timeout value
      expect(config.timeout_ms).toBe(defaultConfig().timeout_ms);
    });

    test('should prioritize environment variables over .env file', () => {
      // Set environment variable
      process.env.AGENTBAY_ENDPOINT = 'wuyingai.from-environment.aliyuncs.com';
      
      // Create .env file with different value
      const envFile = path.join(tempDir, '.env');
      fs.writeFileSync(envFile, 'AGENTBAY_ENDPOINT=wuyingai.from-env-file.aliyuncs.com');
      
      // Load config
      const config = loadConfig(undefined, envFile);
      
      // Environment variable should take precedence
      expect(config.endpoint).toBe('wuyingai.from-environment.aliyuncs.com');
    });

    test('should use default values when no config is provided', () => {
      // No .env file, no environment variables
      const config = loadConfig();
      const defaults = defaultConfig();

      expect(config.endpoint).toBe(defaults.endpoint);
      expect(config.timeout_ms).toBe(defaults.timeout_ms);
    });
  });

  describe('environment variable precedence', () => {
    test('should follow correct precedence order', () => {
      // 1. Custom config (highest priority)
      const customConfig = { endpoint: 'custom.com', timeout_ms: 1000 };
      
      // 2. Environment variable
      process.env.AGENTBAY_ENDPOINT = 'wuyingai.from-env.aliyuncs.com';
      
      // 3. .env file (lowest priority)
      const envFile = path.join(tempDir, '.env');
      fs.writeFileSync(envFile, 'AGENTBAY_ENDPOINT=wuyingai.from-file.aliyuncs.com');
      
      // Test custom config precedence
      const configWithCustom = loadConfig(customConfig, envFile);
      expect(configWithCustom.endpoint).toBe('custom.com');

      // Test environment variable precedence over .env file
      const configWithEnv = loadConfig(undefined, envFile);
      expect(configWithEnv.endpoint).toBe('wuyingai.from-env.aliyuncs.com');
    });
  });
});