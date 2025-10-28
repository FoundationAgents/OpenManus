module.exports = {
    preset: 'ts-jest',
    testEnvironment: 'node',
    testTimeout: 60000, // Set global timeout to 60 seconds for all tests
    moduleFileExtensions: ['ts', 'js', 'json'],
    transform: {
        '^.+\\.ts$': ['ts-jest', {
            tsconfig: 'tsconfig.json',
            diagnostics: {
                ignoreCodes: [151001]
            }
        }]
    },
    transformIgnorePatterns: [
        'node_modules/(?!(chai|playwright)/)' // Exclude chai and playwright from transform ignore
    ],
    testMatch: ['**/tests/**/*.test.ts', '**/tests/**/*.test.js'],
    collectCoverageFrom: [
        'src/**/*.ts',
        '!src/**/*.d.ts',
        '!src/**/index.ts'
    ],
    coverageDirectory: 'coverage',
    coverageReporters: ['text', 'lcov', 'html'],
    testPathIgnorePatterns: [
        '/node_modules/',
        '/dist/'
    ],
    // globals configuration moved to transform options above
};
