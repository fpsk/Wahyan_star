#!/usr/bin/env python3
"""
Robust Multi-Threaded HTTP Server for Wah Yan Star Web Application
Prevents socket pipe drops, connection resets, and page jumps.
Includes transparent fallback between .png and .webp image requests.
"""
import os
import json
import urllib.request
import mimetypes
import http.server
import socketserver

PORT = int(os.environ.get('PORT', 8085))

# Ensure webp is registered in mimetypes
mimetypes.add_type('image/webp', '.webp')

def get_gemini_api_key():
    """Safely retrieves GEMINI_API_KEY from environment or .env without logging."""
    for var in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        val = os.environ.get(var)
        if val and val.strip():
            return val.strip()

    local_env = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(local_env):
        try:
            with open(local_env, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GEMINI_API_KEY=") or line.startswith("GOOGLE_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            return val
        except Exception:
            pass

    fallback_env = "/Users/fskpoon/Documents/antigravity_workspace/NHI_Drug_Regulations/.env"
    if os.path.exists(fallback_env):
        try:
            with open(fallback_env, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GEMINI_API_KEY=") or line.startswith("GOOGLE_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            return val
        except Exception:
            pass
    return None

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def copyfile(self, source, outputfile):
        """High-performance streaming buffer (512 KB chunks) for fast image delivery."""
        import shutil
        try:
            shutil.copyfileobj(source, outputfile, length=512 * 1024)
        except (ConnectionResetError, BrokenPipeError):
            pass

    def translate_path(self, path):
        translated = super().translate_path(path)
        # Transparent fallback: if browser requests .png but only .webp exists
        if translated.endswith('.png') and not os.path.exists(translated):
            webp_path = translated[:-4] + '.webp'
            if os.path.exists(webp_path):
                return webp_path
        # Conversely: if browser requests .webp but only .png exists
        elif translated.endswith('.webp') and not os.path.exists(translated):
            png_path = translated[:-5] + '.png'
            if os.path.exists(png_path):
                return png_path
        return translated

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')

        # Aggressive CDN (Cloudflare on Render) & Browser Caching for Images
        clean_path = self.path.split('?')[0].lower()
        if clean_path.startswith('/okf_output/photos/') or any(clean_path.endswith(ext) for ext in ('.webp', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.woff2', '.ico')):
            # 1 Year Cache: triggers Render Cloudflare CDN edge caching across Asia & Hong Kong
            self.send_header('Cache-Control', 'public, max-age=31536000, immutable')
        elif clean_path.endswith('.js') or clean_path.endswith('.css'):
            self.send_header('Cache-Control', 'public, max-age=86400')
        elif clean_path.endswith('.json'):
            self.send_header('Cache-Control', 'public, max-age=3600, must-revalidate')
        else:
            self.send_header('Cache-Control', 'no-cache, must-revalidate')

        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()


    def do_POST(self):
        if self.path == '/api/chat':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                payload = json.loads(post_data.decode('utf-8'))
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Invalid JSON payload: {e}"}).encode('utf-8'))
                return

            api_key = get_gemini_api_key()
            if not api_key:
                self.send_response(503)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "GEMINI_API_KEY not configured"}).encode('utf-8'))
                return

            messages = payload.get('messages', [])
            system_instruction = ""
            user_content = ""

            for msg in messages:
                role = msg.get('role')
                content = msg.get('content', '')
                if role == 'system':
                    system_instruction += content + "\n"
                elif role == 'user':
                    user_content = content

            if not user_content:
                user_content = payload.get('question', '')

            gemini_models = [
                ("gemini-2.5-flash", True),
                ("gemini-flash-latest", False)
            ]
            answer_text = None
            last_err = None

            for model_name, use_thinking_config in gemini_models:
                gen_config = {
                    "temperature": float(payload.get('temperature', 0.0)),
                    "maxOutputTokens": int(payload.get('max_tokens', 1500))
                }
                if use_thinking_config:
                    gen_config["thinkingConfig"] = {"thinkingBudget": 0}

                # Construct Gemini Payload
                gemini_payload = {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [{"text": user_content}]
                        }
                    ],
                    "generationConfig": gen_config
                }
                if system_instruction.strip():
                    gemini_payload["system_instruction"] = {
                        "parts": [{"text": system_instruction.strip()}]
                    }

                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
                req = urllib.request.Request(
                    url,
                    data=json.dumps(gemini_payload).encode('utf-8'),
                    headers={"Content-Type": "application/json"}
                )
                try:
                    with urllib.request.urlopen(req, timeout=18) as resp:
                        res_data = json.loads(resp.read().decode('utf-8'))
                        candidates = res_data.get('candidates', [])
                        if candidates and len(candidates) > 0:
                            parts = candidates[0].get('content', {}).get('parts', [])
                            if parts and len(parts) > 0:
                                answer_text = parts[0].get('text', '').strip()
                                if answer_text:
                                    break
                except Exception as ex:
                    last_err = ex
                    continue
                except Exception as ex:
                    last_err = ex
                    continue

            if answer_text:
                resp_payload = {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": answer_text
                            }
                        }
                    ],
                    "model": "gemini-2.5-flash"
                }
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(resp_payload).encode('utf-8'))
            else:
                self.send_response(502)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Gemini API error: {last_err}"}).encode('utf-8'))
            return

        self.send_error(404, "Endpoint not found")

    def log_message(self, format, *args):
        sys_msg = format % args
        if ' 404 ' in sys_msg:
            print(f"[404 Notice] {sys_msg}", flush=True)

if __name__ == '__main__':
    with ThreadedHTTPServer(('0.0.0.0', PORT), CustomHandler) as httpd:
        has_key = bool(get_gemini_api_key())
        print(f"Server running on http://localhost:{PORT} (Gemini AI Key: {'ENABLED' if has_key else 'DISABLED'})")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
