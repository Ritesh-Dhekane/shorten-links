import sqlite3
from flask import Flask, render_template_string, request, redirect, url_for, flash
from hashids import Hashids
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

DATABASE = 'database.db'

hashids = Hashids(min_length=4, salt="this is my salt")  # Use your own salt!

# HTML templates (for simplicity, using template_string)
INDEX_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Link Shortener</title>
  <!-- Bootstrap 5 CSS CDN -->
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet" />
  <style>
    body {
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }
    main {
      flex: 1 0 auto;
    }
    footer {
      flex-shrink: 0;
      background-color: #f8f9fa;
      padding: 1rem 0;
      text-align: center;
      font-size: 0.9rem;
      color: #6c757d;
      border-top: 1px solid #dee2e6;
      margin-top: 3rem;
    }
  </style>
</head>
<body>
  <main class="container py-5">
    <div class="text-center mb-4">
      <h1 class="fw-bold">Simple Link Shortener</h1>
      <p class="text-muted">Shorten your URLs quickly and easily</p>
    </div>
    
    <!-- Flash messages -->
    {% with messages = get_flashed_messages() %}
      {% if messages %}
      <div class="alert alert-info alert-dismissible fade show" role="alert">
        {% for message in messages %}
          <div>{{ message }}</div>
        {% endfor %}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
      </div>
      {% endif %}
    {% endwith %}
    
    <!-- URL input form -->
    <form method="post" action="/" class="row g-3 justify-content-center mb-5">
      <div class="col-sm-8 col-md-6 col-lg-5">
        <input
          type="url"
          name="url"
          id="url-input"
          placeholder="Enter a long URL to shorten"
          class="form-control form-control-lg"
          required
          autofocus
        />
      </div>
      <div class="col-auto">
        <button type="submit" class="btn btn-primary btn-lg px-4">Shorten</button>
      </div>
    </form>
    
    <!-- Show short URL -->
    {% if short_url %}
    <div class="text-center mb-5">
      <h5>Your Short URL:</h5>
      <a href="{{ short_url }}" target="_blank" class="link-primary fs-5">{{ short_url }}</a>
    </div>
    {% endif %}
    
    <!-- Recently shortened URLs -->
    <section>
      <h4 class="mb-3">Recently Shortened Links</h4>
      {% if rows %}
      <ul class="list-group">
        {% for row in rows %}
        <li class="list-group-item d-flex justify-content-between align-items-center">
          <a href="{{ request.url_root }}{{ row.short }}" target="_blank" class="text-decoration-none">
            {{ request.url_root }}{{ row.short }}
          </a>
          <span class="text-truncate ms-3 text-muted" style="max-width: 70%">
            → {{ row.original_url }}
          </span>
        </li>
        {% endfor %}
      </ul>
      {% else %}
      <p class="text-muted">No links shortened yet.</p>
      {% endif %}
    </section>
  </main>
  
  <footer>
    &copy; 2025 Ritesh Dhekane
  </footer>
  
  <!-- Bootstrap 5 JS Bundle with Popper -->
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
'''


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_url TEXT NOT NULL,
                clicks INTEGER DEFAULT 0,
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')

@app.route('/', methods=['GET', 'POST'])
def index():
    conn = get_db()
    short_url = None

    if request.method == 'POST':
        url = request.form.get('url')
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url
        cursor = conn.execute('INSERT INTO urls (original_url) VALUES (?)', (url,))
        conn.commit()
        id = cursor.lastrowid
        short_code = hashids.encode(id)
        short_url = url_for('redirect_short', short=short_code, _external=True)
        flash('Short URL created!')
    else:
        short_code = None

    # Show last 10 links
    rows = []
    for row in conn.execute('SELECT id, original_url FROM urls ORDER BY id DESC LIMIT 10'):
        rid = row['id']
        rows.append({
            'short': hashids.encode(rid),
            'original_url': row['original_url']
        })

    return render_template_string(INDEX_HTML, short_url=short_url, rows=rows)

@app.route('/<short>')
def redirect_short(short):
    conn = get_db()
    try:
        ids = hashids.decode(short)
        if len(ids) == 0:
            flash('Invalid short link.')
            return redirect(url_for('index'))
        (idnum,) = ids
        row = conn.execute('SELECT original_url FROM urls WHERE id=?', (idnum,)).fetchone()
        if row:
            conn.execute('UPDATE urls SET clicks = clicks + 1 WHERE id=?', (idnum,))
            conn.commit()
            return redirect(row['original_url'])
        else:
            flash('URL not found.')
    except Exception as e:
        flash('Invalid link!')
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
