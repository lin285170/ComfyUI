LOGIN_PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ComfyUI - Login</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e; color: #e0e0e0;
            display: flex; justify-content: center; align-items: center;
            min-height: 100vh;
        }
        .login-container {
            background: #16213e; padding: 2.5rem; border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.4); width: 100%; max-width: 400px;
        }
        h1 { text-align: center; margin-bottom: 0.25rem; color: #00d4ff; font-size: 1.5rem; }
        .subtitle { text-align: center; margin-bottom: 1.5rem; color: #6c6c8a; font-size: 0.85rem; }
        .form-group { margin-bottom: 1.25rem; }
        label { display: block; margin-bottom: 0.5rem; font-size: 0.875rem; color: #a0a0b0; }
        input[type="text"], input[type="password"] {
            width: 100%; padding: 0.75rem; border: 1px solid #2a2a4a;
            border-radius: 6px; background: #0f0f23; color: #e0e0e0; font-size: 1rem;
            transition: border-color 0.2s;
        }
        input:focus { outline: none; border-color: #00d4ff; }
        .captcha-group { display: flex; gap: 0.75rem; align-items: center; }
        .captcha-group input { flex: 1; }
        .captcha-img { border-radius: 6px; cursor: pointer; height: 42px; border: 1px solid #2a2a4a; }
        button {
            width: 100%; padding: 0.75rem; background: #00d4ff; color: #1a1a2e;
            border: none; border-radius: 6px; font-size: 1rem; font-weight: 600;
            cursor: pointer; transition: background 0.2s;
        }
        button:hover { background: #00b8e6; }
        button:disabled { opacity: 0.6; cursor: not-allowed; }
        .error { color: #ff6b6b; font-size: 0.875rem; margin-top: 0.75rem; display: none; text-align: center; }
        .error.visible { display: block; }
    </style>
</head>
<body>
    <div class="login-container">
        <h1>ComfyUI</h1>
        <p class="subtitle">Authentication Required</p>
        <form id="login-form" autocomplete="off">
            <input type="hidden" id="csrf-token" value="{{CSRF_TOKEN}}">
            <div class="form-group">
                <label for="username">Username</label>
                <input type="text" id="username" name="username" required autofocus autocomplete="off">
            </div>
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required autocomplete="off">
            </div>
            <div class="form-group">
                <label for="captcha">CAPTCHA</label>
                <div class="captcha-group">
                    <input type="text" id="captcha" name="captcha" maxlength="6" required
                           placeholder="Enter characters shown" autocomplete="off">
                    <img id="captcha-img" class="captcha-img" src="/auth/captcha"
                         alt="CAPTCHA" title="Click to refresh">
                </div>
            </div>
            <div id="error-msg" class="error"></div>
            <button type="submit" id="submit-btn">Sign In</button>
        </form>
    </div>
    <script>
        var captchaId = '';
        var csrfToken = document.getElementById('csrf-token').value;

        function loadCaptcha() {
            fetch('/auth/captcha', {credentials: 'same-origin'})
                .then(function(r) {
                    captchaId = r.headers.get('X-Captcha-Id') || '';
                    return r.blob();
                })
                .then(function(blob) {
                    document.getElementById('captcha-img').src = URL.createObjectURL(blob);
                });
        }

        document.getElementById('captcha-img').addEventListener('click', loadCaptcha);

        function showError(msg) {
            var el = document.getElementById('error-msg');
            el.textContent = msg;
            el.classList.add('visible');
        }

        function hideError() {
            var el = document.getElementById('error-msg');
            el.classList.remove('visible');
        }

        document.getElementById('login-form').addEventListener('submit', function(e) {
            e.preventDefault();
            hideError();
            var btn = document.getElementById('submit-btn');
            btn.disabled = true;
            btn.textContent = 'Signing in...';

            var payload = {
                username: document.getElementById('username').value.trim(),
                password: document.getElementById('password').value,
                captcha_id: captchaId,
                captcha_answer: document.getElementById('captcha').value.trim(),
                csrf_token: csrfToken
            };

            fetch('/auth/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
                credentials: 'same-origin',
                body: JSON.stringify(payload)
            })
            .then(function(r) { return r.json().then(function(data) { return {status: r.status, data: data}; }); })
            .then(function(result) {
                if (result.status === 200 && result.data.success) {
                    window.location.href = result.data.redirect || '/';
                } else {
                    showError(result.data.error || 'Login failed');
                    loadCaptcha();
                    document.getElementById('captcha').value = '';
                }
            })
            .catch(function() {
                showError('Network error. Please try again.');
                loadCaptcha();
                document.getElementById('captcha').value = '';
            })
            .finally(function() {
                btn.disabled = false;
                btn.textContent = 'Sign In';
            });
        });

        loadCaptcha();
    </script>
</body>
</html>"""