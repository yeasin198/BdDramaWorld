import os
from flask import Flask, render_template_string, request, redirect, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)

# --- ডাটাবেস কানেকশন ---
# Render/Koyeb-এর Environment Variable থেকে MONGO_URI নেবে
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://admin:admin123@cluster0.mongodb.net/myDatabase?retryWrites=true&w=majority")
client = MongoClient(MONGO_URI)
db = client['webseries_db']
series_collection = db['series']

# --- স্টাইল এবং ডিজাইন (CSS) ---
COMMON_STYLE = """
<style>
    :root { --primary: #E50914; --bg: #141414; --card-bg: #2F2F2F; --text: #FFFFFF; }
    body { background-color: var(--bg); color: var(--text); font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; }
    header { background: linear-gradient(to bottom, rgba(0,0,0,0.7) 10%, transparent); padding: 20px 5%; display: flex; justify-content: space-between; align-items: center; }
    .logo { color: var(--primary); font-size: 30px; font-weight: bold; text-decoration: none; }
    .container { padding: 20px 5%; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 20px; }
    .card { background: var(--card-bg); border-radius: 8px; overflow: hidden; transition: transform 0.3s; cursor: pointer; text-decoration: none; color: white; }
    .card:hover { transform: scale(1.05); }
    .card img { width: 100%; height: 260px; object-fit: cover; }
    .card-info { padding: 10px; font-size: 14px; text-align: center; }
    .player-container { max-width: 900px; margin: auto; }
    iframe { width: 100%; aspect-ratio: 16/9; border: none; border-radius: 8px; background: #000; }
    .ep-list { margin-top: 20px; display: flex; flex-wrap: wrap; gap: 10px; }
    .ep-btn { background: var(--card-bg); color: white; border: 1px solid #444; padding: 10px 20px; cursor: pointer; border-radius: 5px; }
    .ep-btn:hover { background: var(--primary); }
    .admin-form { max-width: 600px; margin: auto; background: #222; padding: 30px; border-radius: 10px; }
    input, textarea { width: 100%; padding: 12px; margin: 10px 0; background: #333; color: white; border: 1px solid #444; border-radius: 5px; box-sizing: border-box; }
    .submit-btn { background: var(--primary); color: white; border: none; padding: 15px; width: 100%; cursor: pointer; font-weight: bold; border-radius: 5px; }
</style>
"""

# --- ফ্রন্টএন্ড লেআউট (HTML) ---

# ১. হোম পেজ
HOME_HTML = """
<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WebSeries BD - Home</title>
    """ + COMMON_STYLE + """
</head>
<body>
    <header>
        <a href="/" class="logo">WebSeries BD</a>
        <a href="/admin" style="color: #aaa; text-decoration: none;">Admin</a>
    </header>
    <div class="container">
        <h2>সব সিরিজ এবং মুভি</h2>
        <div class="grid">
            {% for s in series %}
            <a href="/series/{{ s._id }}" class="card">
                <img src="{{ s.poster }}" alt="Poster">
                <div class="card-info">{{ s.title }}</div>
            </a>
            {% endfor %}
        </div>
    </div>
</body>
</html>
"""

# ২. ভিডিও প্লেয়ার পেজ
DETAIL_HTML = """
<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <title>{{ series.title }} - WebSeries BD</title>
    """ + COMMON_STYLE + """
</head>
<body>
    <header>
        <a href="/" class="logo">WebSeries BD</a>
    </header>
    <div class="container player-container">
        <h1>{{ series.title }}</h1>
        <div id="video-player">
            <iframe id="main-frame" src="{{ series.episodes[0].url if series.episodes else '' }}" allowfullscreen></iframe>
        </div>
        <h3>এপিসোড লিস্ট:</h3>
        <div class="ep-list">
            {% for ep in series.episodes %}
            <button class="ep-btn" onclick="changeVideo('{{ ep.url }}')">{{ ep.name }}</button>
            {% endfor %}
        </div>
        <div style="margin-top: 20px; color: #ccc;">
            <h3>সিরিজ ডিটেইলস:</h3>
            <p>{{ series.description }}</p>
        </div>
    </div>
    <script>
        function changeVideo(url) {
            document.getElementById('main-frame').src = url;
            window.scrollTo({top: 0, behavior: 'smooth'});
        }
    </script>
</body>
</html>
"""

# ৩. অ্যাডমিন প্যানেল
ADMIN_HTML = """
<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <title>Admin Panel</title>
    """ + COMMON_STYLE + """
</head>
<body>
    <div class="container">
        <div class="admin-form">
            <h2 style="color: var(--primary);">নতুন সিরিজ যোগ করুন</h2>
            <form method="POST">
                <input name="title" placeholder="সিরিজের নাম" required>
                <input name="poster" placeholder="পোস্টার ইমেজের লিঙ্ক (URL)" required>
                <textarea name="desc" placeholder="সিরিজের বর্ণনা" rows="4"></textarea>
                <p style="font-size: 12px; color: #888;">এপিসোড ফরম্যাট: Episode Name | Video Link (প্রতি লাইনে একটি)</p>
                <textarea name="episodes" placeholder="Episode 1 | https://link.com" rows="6" required></textarea>
                <button type="submit" class="submit-btn">সেভ করুন</button>
            </form>
            <br>
            <a href="/" style="color: white; text-decoration: none;">← হোমে ফিরে যান</a>
        </div>
    </div>
</body>
</html>
"""

# --- রাউটিং এবং লজিক ---

@app.route('/')
def home():
    all_series = list(series_collection.find())
    return render_template_string(HOME_HTML, series=all_series)

@app.route('/series/<id>')
def detail(id):
    series = series_collection.find_one({"_id": ObjectId(id)})
    if not series:
        return "সিরিজ পাওয়া যায়নি!", 404
    return render_template_string(DETAIL_HTML, series=series)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        title = request.form.get('title')
        poster = request.form.get('poster')
        desc = request.form.get('desc')
        raw_episodes = request.form.get('episodes').strip().split('\n')
        
        episodes_list = []
        for line in raw_episodes:
            if '|' in line:
                name, url = line.split('|')
                episodes_list.append({"name": name.strip(), "url": url.strip()})

        series_collection.insert_one({
            "title": title,
            "poster": poster,
            "description": desc,
            "episodes": episodes_list
        })
        return redirect(url_for('home'))
    
    return render_template_string(ADMIN_HTML)

if __name__ == '__main__':
    # Render বা Koyeb-এর জন্য পোর্ট সেটআপ
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
