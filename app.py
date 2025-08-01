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
<html>
<head><title>Link Shortener</title></head>
<body>
    <h2>Shorten a URL</h2>
    <form method="post" action="/">
        <input type="text" name="url" placeholder="Enter long URL" required size="50">
        <input type="submit" value="Shorten">
    </form>
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        <ul>
        {% for message in messages %}
          <li>{{ message }}</li>
        {% endfor %}
        </ul>
      {% endif %}
    {% endwith %}
    {% if short_url %}
        <h3>Your Short URL: <a href="{{ short_url }}">{{ short_url }}</a></h3>
    {% endif %}
    <hr>
    <h4>Previously Shortened Links:</h4>
    <ul>
    {% for row in rows %}
        <li><a href="{{ request.url_root }}{{ row.short }}">
              {{ request.url_root }}{{ row.short }}</a> &rarr; {{ row.original_url }}</li>
    {% endfor %}
    </ul>
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
