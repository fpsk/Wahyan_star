const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 8080;
const HOST = '127.0.0.1';
const PUBLIC_DIR = __dirname;
const LM_STUDIO_HOST = '127.0.0.1';
const LM_STUDIO_PORT = 1234;

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon'
};

const server = http.createServer((req, res) => {
  // Add CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  // Strip query string (e.g. ?v=123) to fix file path resolution for CSS/JS assets!
  const cleanUrl = req.url.split('?')[0];

  // Proxy endpoint for LM Studio (/api/chat) to bypass browser CORS / PNA restrictions
  if (cleanUrl === '/api/chat' && req.method === 'POST') {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => {
      const lmReq = http.request({
        hostname: LM_STUDIO_HOST,
        port: LM_STUDIO_PORT,
        path: '/v1/chat/completions',
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(body)
        },
        timeout: 60000
      }, (lmRes) => {
        let lmBody = '';
        lmRes.on('data', chunk => { lmBody += chunk; });
        lmRes.on('end', () => {
          res.writeHead(lmRes.statusCode, { 'Content-Type': 'application/json' });
          res.end(lmBody);
        });
      });

      lmReq.on('error', (err) => {
        console.error('LM Studio Proxy Error:', err.message);
        res.writeHead(502, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'LM Studio Port 1234 Unreachable', message: err.message }));
      });

      lmReq.on('timeout', () => {
        lmReq.destroy();
        res.writeHead(540, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'LM Studio Timeout (60s)' }));
      });

      lmReq.write(body);
      lmReq.end();
    });
    return;
  }

  let safePath = path.normalize(decodeURIComponent(cleanUrl)).replace(/^(\.\.[\/\\])+/, '');
  if (safePath === '/' || safePath === '\\') {
    safePath = '/index.html';
  }

  const filePath = path.join(PUBLIC_DIR, safePath);
  const ext = path.extname(filePath).toLowerCase();
  const contentType = MIME_TYPES[ext] || 'application/octet-stream';

  fs.stat(filePath, (err, stats) => {
    if (err || !stats.isFile()) {
      res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
      res.end('404 Not Found: ' + safePath);
      return;
    }

    res.writeHead(200, {
      'Content-Type': contentType,
      'Content-Length': stats.size,
      'Cache-Control': 'public, max-age=3600'
    });

    const stream = fs.createReadStream(filePath);
    stream.on('error', () => {
      if (!res.headersSent) {
        res.writeHead(500, { 'Content-Type': 'text/plain' });
      }
      res.end();
    });

    stream.pipe(res);
  });
});

server.on('clientError', (err, socket) => {
  socket.destroy();
});

server.listen(PORT, HOST, () => {
  console.log(`🚀 Node.js Server & LM Studio Proxy running on http://localhost:${PORT}`);
});
