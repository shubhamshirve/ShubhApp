const express = require('express');
const cors = require('cors');
const { Client, LocalAuth } = require('whatsapp-web.js');
const QRCode = require('qrcode');
const path = require('path');
const fs = require('fs');
const { execSync } = require('child_process');

const app = express();
app.use(cors());
app.use(express.json());

const PORT = process.env.WHATSAPP_PORT || 8002;
const AUTH_DIR = path.join(__dirname, '.wwebjs_auth');

// Ensure auth directory exists
if (!fs.existsSync(AUTH_DIR)) {
  fs.mkdirSync(AUTH_DIR, { recursive: true });
}

// ── Startup: purge ALL stale Chromium lock files across all sessions ──────
// SingletonLock is a Linux SYMLINK. fs.existsSync() follows symlinks and returns
// false for dangling ones — so we CANNOT use existsSync to detect them.
// Solution: use shell 'find -delete' which handles dangling symlinks correctly.
(function purgeAllStaleLocks() {
  try {
    // find handles dangling symlinks, any nesting depth, and all lock types
    execSync(
      `find "${AUTH_DIR}" -maxdepth 3 \( -name "SingletonLock" -o -name "SingletonSocket" -o -name "SingletonCookie" \) -delete 2>/dev/null || true`,
      { stdio: 'pipe' }
    );
    console.log('[startup] Chromium lock purge complete');
  } catch (e) {
    console.warn(`[startup] Lock cleanup warning: ${e.message}`);
  }
})();


// Auto-detect Chromium executable path (handles different Linux distros)
function getChromiumPath() {
  const candidates = [
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
    '/usr/bin/google-chrome',
    '/usr/bin/google-chrome-stable',
    process.env.PUPPETEER_EXECUTABLE_PATH,
  ].filter(Boolean);

  for (const p of candidates) {
    if (fs.existsSync(p)) {
      console.log(`[chromium] Found at: ${p}`);
      return p;
    }
  }

  console.warn('[chromium] No executable found in standard paths, Puppeteer will use default.');
  return undefined;
}

const CHROMIUM_PATH = getChromiumPath();

// ── Per-operator client management ────────────────────────────────────────
const clients = {};      // operatorId -> Client instance
const qrCodes = {};      // operatorId -> latest QR string
const statuses = {};     // operatorId -> 'disconnected' | 'qr_pending' | 'ready' | 'initializing' | 'error'
const errors = {};       // operatorId -> last error message

function getClientState(operatorId) {
  return {
    status: statuses[operatorId] || 'disconnected',
    hasQR: !!qrCodes[operatorId],
    error: errors[operatorId] || null,
  };
}

// Clean up stale Chromium lock files before launching a new browser instance.
// IMPORTANT: SingletonLock is a Linux SYMLINK. We must use lstatSync() (not
// existsSync/statSync) because those follow symlinks and return false for
// dangling symlinks — which is exactly what a stale lock becomes after
// the previous container is killed (the symlink target no longer exists).
function cleanChromiumLocks(operatorId) {
  const sessionDir = path.join(AUTH_DIR, `session-${operatorId}`);
  const lockFiles = ['SingletonLock', 'SingletonSocket', 'SingletonCookie'];

  // Also use find for belt-and-suspenders coverage of dangling symlinks
  try {
    execSync(
      `find "${sessionDir}" -maxdepth 1 \( -name "SingletonLock" -o -name "SingletonSocket" -o -name "SingletonCookie" \) -delete 2>/dev/null || true`,
      { stdio: 'pipe' }
    );
  } catch (e) { /* session dir may not exist yet */ }

  // Also try via Node.js (handles regular files that find might miss)
  for (const lockFile of lockFiles) {
    const lockPath = path.join(sessionDir, lockFile);
    try {
      fs.lstatSync(lockPath);  // lstatSync does NOT follow symlinks — detects dangling symlinks
      fs.rmSync(lockPath, { force: true });
      console.log(`[${operatorId}] Removed stale lock: ${lockFile}`);
    } catch (e) {
      // lstatSync throws if file doesn't exist at all — that's fine
    }
  }
}


// Starts the client initialization in the background (non-blocking).
// The caller gets an immediate response; status/QR is polled separately.
function initClientBackground(operatorId) {
  // If already initialized and ready, skip
  if (clients[operatorId] && statuses[operatorId] === 'ready') {
    return 'already_ready';
  }

  // If already in-progress, skip
  if (statuses[operatorId] === 'initializing' || statuses[operatorId] === 'qr_pending') {
    return statuses[operatorId];
  }

  // Destroy old client if exists
  if (clients[operatorId]) {
    try { clients[operatorId].destroy(); } catch (e) { /* ignore */ }
    delete clients[operatorId];
  }

  statuses[operatorId] = 'initializing';
  qrCodes[operatorId] = null;
  errors[operatorId] = null;

  // Clean up any stale Chromium lock files from previous container runs
  cleanChromiumLocks(operatorId);

  const puppeteerArgs = {
    headless: true,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
      '--no-first-run',
      '--disable-extensions',
      '--disable-default-apps',
      '--remote-debugging-port=0',
      // Network fixes for Docker bridge networks:
      '--disable-ipv6',             // Docker bridge often has broken IPv6; force IPv4
      '--no-proxy-server',          // Ensure no proxy intercepts connections
      '--ignore-certificate-errors',// Prevent TLS issues in restricted environments
      '--disable-background-timer-throttling',
      '--disable-renderer-backgrounding',
      '--disable-backgrounding-occluded-windows',
    ],
  };

  if (CHROMIUM_PATH) {
    puppeteerArgs.executablePath = CHROMIUM_PATH;
  }

  const client = new Client({
    authStrategy: new LocalAuth({
      clientId: operatorId,
      dataPath: AUTH_DIR,
    }),
    puppeteer: puppeteerArgs,
  });

  client.on('qr', (qr) => {
    console.log(`[${operatorId}] QR code received`);
    qrCodes[operatorId] = qr;
    statuses[operatorId] = 'qr_pending';
  });

  client.on('ready', () => {
    console.log(`[${operatorId}] Client is ready`);
    statuses[operatorId] = 'ready';
    qrCodes[operatorId] = null;
    errors[operatorId] = null;
  });

  client.on('authenticated', () => {
    console.log(`[${operatorId}] Authenticated`);
    qrCodes[operatorId] = null;
    errors[operatorId] = null;
  });

  client.on('auth_failure', (msg) => {
    console.error(`[${operatorId}] Auth failure:`, msg);
    statuses[operatorId] = 'auth_failed';
    errors[operatorId] = `Auth failure: ${msg}`;
    qrCodes[operatorId] = null;
    delete clients[operatorId];
  });

  client.on('disconnected', (reason) => {
    console.log(`[${operatorId}] Disconnected:`, reason);
    statuses[operatorId] = 'disconnected';
    qrCodes[operatorId] = null;
    delete clients[operatorId];
  });

  clients[operatorId] = client;

  // Run initialize in background — do NOT await here
  client.initialize().catch(async (err) => {
    console.error(`[${operatorId}] Init error:`, err.message);
    statuses[operatorId] = 'error';
    errors[operatorId] = err.message;
    // Destroy the client to kill Chromium so next retry doesn't
    // fail with 'browser is already running for this userDataDir'
    try {
      await client.destroy();
    } catch (destroyErr) {
      console.warn(`[${operatorId}] Destroy on error:`, destroyErr.message);
    }
    delete clients[operatorId];
    // Also clean up any new lock files the failed session may have left
    cleanChromiumLocks(operatorId);
  });

  return 'initializing';
}

// ── API Endpoints ─────────────────────────────────────────────────────────

// Health check
app.get('/health', (req, res) => {
  const mem = process.memoryUsage();
  res.json({
    status: 'ok',
    service: 'whatsapp-webjs',
    uptime: Math.floor(process.uptime()),
    chromium: CHROMIUM_PATH || 'default',
    activeClients: Object.keys(clients).length,
    memoryMB: Math.round(mem.rss / 1024 / 1024),
  });
});

// Initialize client for an operator (non-blocking)
app.post('/init/:operatorId', (req, res) => {
  const { operatorId } = req.params;
  try {
    const status = initClientBackground(operatorId);
    res.json({ status });
  } catch (err) {
    console.error(`[${operatorId}] Init error:`, err.message);
    res.status(500).json({ error: err.message });
  }
});

// Get status for an operator
app.get('/status/:operatorId', (req, res) => {
  const { operatorId } = req.params;
  res.json(getClientState(operatorId));
});

// Get QR code as base64 image
app.get('/qr/:operatorId', async (req, res) => {
  const { operatorId } = req.params;
  const qrString = qrCodes[operatorId];

  if (!qrString) {
    return res.json({ qr: null, status: statuses[operatorId] || 'disconnected' });
  }

  try {
    const qrDataUrl = await QRCode.toDataURL(qrString, { width: 300, margin: 2 });
    res.json({ qr: qrDataUrl, status: statuses[operatorId] });
  } catch (err) {
    res.status(500).json({ error: 'Failed to generate QR image' });
  }
});

// Send message
app.post('/send/:operatorId', async (req, res) => {
  const { operatorId } = req.params;
  const { phone, message } = req.body;

  if (!phone || !message) {
    return res.status(400).json({ error: 'phone and message are required' });
  }

  const client = clients[operatorId];
  if (!client || statuses[operatorId] !== 'ready') {
    return res.status(400).json({ error: 'WhatsApp client not connected', status: statuses[operatorId] || 'disconnected' });
  }

  try {
    // Format phone number: remove leading + and non-digits, append @c.us
    const cleanPhone = phone.replace(/[^\d]/g, '');
    const chatId = cleanPhone.includes('@c.us') ? cleanPhone : `${cleanPhone}@c.us`;

    // Check if the number is registered on WhatsApp
    const isRegistered = await client.isRegisteredUser(chatId);
    if (!isRegistered) {
      return res.status(400).json({ error: `Number ${phone} is not registered on WhatsApp` });
    }

    const sentMsg = await client.sendMessage(chatId, message);
    console.log(`[${operatorId}] Message sent to ${chatId}`);
    res.json({ success: true, messageId: sentMsg.id?.id || null });
  } catch (err) {
    console.error(`[${operatorId}] Send error:`, err.message);
    res.status(500).json({ error: err.message });
  }
});

// Disconnect client
app.post('/disconnect/:operatorId', async (req, res) => {
  const { operatorId } = req.params;
  const client = clients[operatorId];

  if (!client) {
    statuses[operatorId] = 'disconnected';
    return res.json({ status: 'disconnected' });
  }

  try {
    await client.logout();
    await client.destroy();
  } catch (e) {
    console.log(`[${operatorId}] Disconnect cleanup:`, e.message);
  }

  delete clients[operatorId];
  delete qrCodes[operatorId];
  delete errors[operatorId];
  statuses[operatorId] = 'disconnected';

  // Clean up session files
  const sessionDir = path.join(AUTH_DIR, `session-${operatorId}`);
  if (fs.existsSync(sessionDir)) {
    fs.rmSync(sessionDir, { recursive: true, force: true });
  }

  res.json({ status: 'disconnected' });
});

// ── Start server ──────────────────────────────────────────────────────────
app.listen(PORT, '0.0.0.0', () => {
  console.log(`WhatsApp Web.js service running on port ${PORT}`);
  console.log(`Chromium: ${CHROMIUM_PATH || 'default (puppeteer bundled)'}`);
});
