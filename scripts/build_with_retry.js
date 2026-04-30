const { spawnSync } = require('child_process');
const fs = require('fs');

const MAX_ATTEMPTS = 3;
const RETRY_DELAY_MS = 1200;

function sleep(ms) {
  const end = Date.now() + ms;
  while (Date.now() < end) {
    // busy wait is acceptable for short retry gate in CI script
  }
}

function cleanNextDir() {
  try {
    fs.rmSync('.next', { recursive: true, force: true });
  } catch (err) {
    const msg = err && err.message ? err.message : String(err);
    console.warn(`[build_with_retry] cleanup warning: ${msg}`);
  }
}

function isRetriableBuildError(output) {
  if (!output) return false;

  const retriablePatterns = [
    'ENOENT: no such file or directory, rename',
    'ENOENT: no such file or directory, open',
    'ENOENT: no such file or directory, copyfile',
    'ENOTEMPTY: directory not empty, rmdir',
    'Cannot find module for page: /_document',
    'Failed to copy traced files',
    'middleware-manifest.json',
    'pages-manifest.json',
    'build-manifest.json',
    'client-reference-manifest.js',
    '.next\\export\\500.html',
    '.next\\standalone',
  ];

  return retriablePatterns.some((pattern) => output.includes(pattern));
}

for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt += 1) {
  cleanNextDir();

  console.log(`[build_with_retry] attempt ${attempt}/${MAX_ATTEMPTS}: next build`);
  const result = spawnSync('npx', ['next', 'build'], {
    shell: true,
    env: process.env,
    encoding: 'utf-8',
  });

  const stdout = result.stdout || '';
  const stderr = result.stderr || '';
  if (stdout) process.stdout.write(stdout);
  if (stderr) process.stderr.write(stderr);

  if (result.status === 0) {
    console.log('[build_with_retry] build succeeded');
    process.exit(0);
  }

  const combined = `${stdout}\n${stderr}`;

  const retriable = isRetriableBuildError(combined);
  if (!retriable || attempt === MAX_ATTEMPTS) {
    console.error('[build_with_retry] build failed and will not retry');
    process.exit(result.status || 1);
  }

  console.warn(`[build_with_retry] transient build failure detected, retrying after ${RETRY_DELAY_MS}ms`);
  sleep(RETRY_DELAY_MS);
}

process.exit(1);
