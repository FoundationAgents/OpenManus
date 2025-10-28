import { defineConfig } from 'tsup'
import { readFileSync, writeFileSync } from 'fs'

export default defineConfig({
  entry: ['src/**/*.ts'],
  format: ['esm','cjs' ],
  shims: true,
  esbuildOptions(options, context) {
    if (context.format === 'esm') {
      options.banner = {
        js: `
        import { createRequire } from 'module';
        const require = createRequire(import.meta.url);
          (function() {
            if (typeof OpenApi !== 'undefined' && !OpenApi.default) {
              OpenApi.default = OpenApi;
            }
          })();
        `
      }
    }
  },
  target: 'es2020',
  outDir: 'dist',
  dts: true,
  clean: true,
  splitting: true,
  keepNames: true,
  treeshake: false,
  minify: false,
  sourcemap: true,
  outExtension({ format }) {
    return { js: format === 'esm' ? '.mjs' : '.cjs' }
  },
  async onSuccess() {
    try {
      const esmFile = './dist/index.mjs';
      let content = readFileSync(esmFile, 'utf8');
      content = content.replace(
        /class (\w+) extends (\w+)/g,
        'class $1 extends ($2.default || $2)'
      );
      content = `
        if (typeof OpenApi !== 'undefined' && !OpenApi.default) {
          OpenApi.default = OpenApi;
        }
        ${content}
      `;

      writeFileSync(esmFile, content);
      console.log('ESM file updated successfully.');
    }catch (error) {
      console.error('onSuccess error:', error);
    }

  }
})
