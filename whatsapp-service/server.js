const express = require('express');
const cors = require('cors');
const { Client, LocalAuth } = require('whatsapp-web.js');
const QRCode = require('qrcode');
const path = require('path');
const fs = require('fs');

const app = express();
app.use(cors());
app.use(express.json());

const PORT = process.env.WHATSAPP_PORT || 8002;
const AUTH_DIR = path.join(__dirname, '.wwebjs_auth');

// Ensure auth directory exists
if (!fs.existsSync(AUTH_DIR)) {
  fs.mkdirSync(AUTH_DIR, { recursive: true });
}

// ── Per-operator client management ────────────────────────────────────────
const clients = {};      // operatorId -> Client instance
const qrCodes = {};      // operatorId -> latest QR string
const statuses = {};     // operatorId -> 'disconnected' | 'qr_pending' | 'ready' | 'initializing'

function getClientState(operatorId) {
  return {
    status: statuses[operatorId] || 'disconnected',
    hasQR: !!qrCodes[operatorId],
  };
}

async function initClient(operatorId) {
  // If already initialized and ready, skip
  if (clients[operatorId] && statuses[operatorId] === 'ready') {
    return { status: 'already_ready' };
  }

  // If already initializing, skip
  if (statuses[operatorId] === 'initializing' || statuses[operatorId] === 'qr_pending') {
    return { status: statuses[operatorId] };
  }

  // Destroy old client if exists
  if (clients[operatorId]) {
    try { await clients[operatorId].destroy(); } catch (e) { /* ignore */ }
    delete clients[operatorId];
  }

  statuses[operatorId] = 'initializing';
  qrCodes[operatorId] = null;

  const client = new Client({
    authStrategy: new LocalAuth({
      clientId: operatorId,
      dataPath: AUTH_DIR,
    }),
    puppeteer: {
      headless: true,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--no-first-run',
        '--single-process',
      ],
      executablePath: '/usr/bin/chromium',
    },
  });

  client.on('qr', (qr) => {
    console.log(`[${operatorId}] QR code received`);
    qrCodes[operatorId] = qr;
    statuses[operatorId] = 'qr_pending';
  });

  client.on('ready', () => {
    console.log(`[${operatorId}] Client is ready`);
    statuses[operatorId] = 'ready';
    qrCodes[operatorId] = null; // QR no longer needed
  });

  client.on('authenticated', () => {
    console.log(`[${operatorId}] Authenticated`);
    qrCodes[operatorId] = null;
  });

  client.on('auth_failure', (msg) => {
    console.error(`[${operatorId}] Auth failure:`, msg);
    statuses[operatorId] = 'auth_failed';
    qrCodes[operatorId] = null;
  });

  client.on('disconnected', (reason) => {
    console.log(`[${operatorId}] Disconnected:`, reason);
    statuses[operatorId] = 'disconnected';
    qrCodes[operatorId] = null;
    delete clients[operatorId];
  });

  clients[operatorId] = client;

  try {
    await client.initialize();
  } catch (err) {
    console.error(`[${operatorId}] Init error:`, err.message);
    statuses[operatorId] = 'error';
    delete clients[operatorId];
    throw err;
  }

  return { status: statuses[operatorId] };
}

// ── API Endpoints ─────────────────────────────────────────────────────────

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'whatsapp-webjs' });
});

// Initialize client for an operator
app.post('/init/:operatorId', async (req, res) => {
  const { operatorId } = req.params;
  try {
    const result = await initClient(operatorId);
    res.json(result);
  } catch (err) {
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
});
