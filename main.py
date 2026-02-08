import os
from flask import Flask, render_template_string, request, redirect, url_for, flash
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = "secret_key_123"

# --- ডাটাবেস কানেকশন ---
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
client = MongoClient(MONGO_URI)
db = client['webseries_db']
series_collection = db['series']

# --- আধুনিক এবং রেসপন্সিভ ডিজাইন (CSS) ---
COMMON_STYLE = """
<style>
    :root { --primary: #E50914; --bg: #0b0b0b; --card-bg: #1a1a1a; --text: #ffffff; }
    body { background-color: var(--bg); color: var(--text); font-family: 'Segoe UI', sans-serif; margin: 0; padding: 0; }
    
    /* Header & Search */
    header { background: #000; padding: 10px 5%; display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; border-bottom: 2px solid var(--primary); sticky: top; position: sticky; top: 0; z-index: 1000; }
    .logo { color: var(--primary); font-size: 22px; font-weight: bold; text-decoration: none; text-transform: uppercase; }
    .search-box { display: flex; background: #222; border-radius: 5px; overflow: hidden; margin: 10px 0; width: 100%; max-width: 400px; }
    .search-box input { border: none; background: transparent; color: white; padding: 8px 15px; width: 100%; outline: none; }
    .search-box button { background: var(--primary); border: none; color: white; padding: 0 15px; cursor: pointer; }

    /* Layout Containers */
    .container { padding: 20px 5%; }
    
    /* Responsive Grid */
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 15px; }
    @media (min-width: 768px) { .grid { grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 20px; } }

    /* Card Styling */
    .card { background: var(--card-bg); border-radius: 8px; overflow: hidden; position: relative; text-decoration: none; color: white; transition: 0.3s; border: 1px solid #333; }
    .card:hover { transform: translateY(-5px); border-color: var(--primary); }
    .card img { width: 100%; aspect-ratio: 2/3; object-fit: cover; }
    .poster-badge { position: absolute; top: 8px; left: 8px; background: var(--primary); color: white; padding: 2px 8px; font-size: 10px; border-radius: 3px; font-weight: bold; }
    .card-info { padding: 8px; font-size: 13px; text-align: center; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

    /* Admin Table/List */
    .admin-list { width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 14px; }
    .admin-list th, .admin-list td { padding: 12px; border-bottom: 1px solid #333; text-align: left; }
    .admin-list th { background: #222; }
    .btn-edit { color: #3498db; text-decoration: none; margin-right: 10px; }
    .btn-delete { color: #e74c3c; text-decoration: none; cursor: pointer; border:none; background:none; padding:0; font-size:14px; }

    /* Forms */
    .form-group { background: #1a1a1a; padding: 20px; border-radius: 8px; max-width: 700px; margin: auto; }
    input, textarea { width: 100%; padding: 12px; margin: 8px 0; background: #262626; color: white; border: 1px solid #333; border-radius: 5px; box-sizing: border-box; }
    .submit-btn { background: var(--primary); color: white; border: none; padding: 12px; width: 100%; cursor: pointer; font-weight: bold; border-radius: 5px; margin-top: 10px; }
    .ep-input-group { border: 1px dashed #444; padding: 10px; margin-bottom: 10px; border-radius: 5px; }

    /* Detail Page */
    .detail-flex { display: flex; flex-direction: column; gap: 20px; }
    @media (min-width: 768px) { .detail-flex { flex-direction: row; } }
    .ep-box { background: #1a1a1a; padding: 12px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid var(--primary); display: flex; flex-direction: column; gap: 10px; }
    .btn-links { display: flex; flex-wrap: wrap; gap: 8px; }
    .link-btn { padding: 8px 12px; border-radius: 4px; text-decoration: none; color: white; font-size: 12px; font-weight: bold; }
    .bg-dl { background: #27ae60; } .bg-st { background: #2980b9; } .bg-tg { background: #0088cc; }
</style>
"""

# --- HTML টেমপ্লেট ফাংশন সমূহ ---

def header_html(admin=False):
    search_url = "/admin" if admin else "/"
    return f"""
    <header>
        <a href="/" class="logo">WebSeries BD</a>
        <form action="{search_url}" method="GET" class="search-box">
            <input type="text" name="q" placeholder="মুভি বা সিরিজ খুঁজুন..." value="{request.args.get('q', '')}">
            <button type="submit">Search</button>
        </form>
        <div>
            { '<a href="/admin/add" style="color:white; margin-right:15px; text-decoration:none;">+ Add New</a><a href="/" style="color:var(--primary); text-decoration:none;">User View</a>' if admin else '<a href="/admin" style="color:#aaa; text-decoration:none;">Admin</a>' }
        </div>
    </header>
    """

@app.route('/')
def home():
    query = request.args.get('q', '')
    filter_data = {"title": {"$regex": query, "$options": "i"}} if query else {}
    movies = list(series_collection.find(filter_data).sort("_id", -1))
    
    html = f"<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'><title>Home</title>{COMMON_STYLE}</head><body>"
    html += header_html()
    html += '<div class="container">'
    html += f'<h3>{"অনুসন্ধানের ফলাফল: " + query if query else "সব মুভি এবং সিরিজ"}</h3>'
    html += '<div class="grid">'
    for s in movies:
        html += f'''
        <a href="/series/{s['_id']}" class="card">
            {f'<div class="poster-badge">{s.get("poster_text", "")}</div>' if s.get("poster_text") else ''}
            <img src="{s['poster']}">
            <div class="card-info">{s['title']} ({s['year']})</div>
        </a>
        '''
    html += '</div></div></body></html>'
    return render_template_string(html)

@app.route('/series/<id>')
def detail(id):
    s = series_collection.find_one({"_id": ObjectId(id)})
    html = f"<!DOCTYPE html><html><head><title>{s['title']}</title>{COMMON_STYLE}</head><body>"
    html += header_html()
    html += f'''
    <div class="container">
        <div class="detail-flex">
            <img src="{s['poster']}" style="width:250px; border-radius:10px;">
            <div>
                <h1>{s['title']} ({s['year']})</h1>
                <p style="color:#aaa;">ভাষা: {s['language']}</p>
                <p>{s['description']}</p>
            </div>
        </div>
        <hr style="border:0.1px solid #333; margin:30px 0;">
        <h3>এপিসোড ও ডাউনলোড লিঙ্ক:</h3>
        {''.join([f'''
        <div class="ep-box">
            <strong>Episode: {ep['ep_no']}</strong>
            <div class="btn-links">
                {f'<a href="{ep["dl_link"]}" class="link-btn bg-dl" target="_blank">Download</a>' if ep["dl_link"] else ''}
                {f'<a href="{ep["st_link"]}" class="link-btn bg-st" target="_blank">Stream</a>' if ep["st_link"] else ''}
                {f'<a href="{ep["tg_link"]}" class="link-btn bg-tg" target="_blank">Telegram</a>' if ep["tg_link"] else ''}
            </div>
        </div>
        ''' for ep in s['episodes']])}
    </div></body></html>
    '''
    return render_template_string(html)

# --- এডমিন সেকশন (Search, Add, Edit, Delete) ---

@app.route('/admin')
def admin_dashboard():
    query = request.args.get('q', '')
    filter_data = {"title": {"$regex": query, "$options": "i"}} if query else {}
    movies = list(series_collection.find(filter_data).sort("_id", -1))
    
    html = f"<!DOCTYPE html><html><head><title>Admin Panel</title>{COMMON_STYLE}</head><body>"
    html += header_html(admin=True)
    html += '<div class="container"><h2>মুভি ম্যানেজমেন্ট</h2>'
    html += '<table class="admin-list"><tr><th>Poster</th><th>Title</th><th>Year</th><th>Action</th></tr>'
    for s in movies:
        html += f'''
        <tr>
            <td><img src="{s['poster']}" style="width:40px; height:50px; object-fit:cover;"></td>
            <td>{s['title']}</td>
            <td>{s['year']}</td>
            <td>
                <a href="/admin/edit/{s['_id']}" class="btn-edit">Edit</a>
                <form action="/admin/delete/{s['_id']}" method="POST" style="display:inline;">
                    <button type="submit" class="btn-delete" onclick="return confirm('ডিলেট করতে চান?')">Delete</button>
                </form>
            </td>
        </tr>
        '''
    html += '</table></div></body></html>'
    return render_template_string(html)

@app.route('/admin/add', methods=['GET', 'POST'])
@app.route('/admin/edit/<id>', methods=['GET', 'POST'])
def edit_movie(id=None):
    movie = series_collection.find_one({"_id": ObjectId(id)}) if id else None
    
    if request.method == 'POST':
        shortener = request.form.get('shortener', "")
        ep_nos = request.form.getlist('ep_no[]')
        dl_links = request.form.getlist('dl_link[]')
        st_links = request.form.getlist('st_link[]')
        tg_links = request.form.getlist('tg_link[]')
        
        ep_list = []
        for i in range(len(ep_nos)):
            def lnk(l): return shortener + l.strip() if shortener and l.strip() else l.strip()
            ep_list.append({"ep_no": ep_nos[i], "dl_link": lnk(dl_links[i]), "st_link": lnk(st_links[i]), "tg_link": lnk(tg_links[i])})

        data = {
            "title": request.form.get('title'), "year": request.form.get('year'),
            "language": request.form.get('lang'), "poster": request.form.get('poster'),
            "poster_text": request.form.get('poster_text'), "description": request.form.get('desc'),
            "episodes": ep_list
        }
        
        if id: series_collection.update_one({"_id": ObjectId(id)}, {"$set": data})
        else: series_collection.insert_one(data)
        return redirect(url_for('admin_dashboard'))

    # Form HTML
    html = f"<!DOCTYPE html><html><head><title>Form</title>{COMMON_STYLE}</head><body>"
    html += header_html(admin=True)
    html += f'''
    <div class="container"><div class="form-group">
        <h2>{"মুভি আপডেট করুন" if id else "নতুন মুভি যোগ করুন"}</h2>
        <form method="POST">
            <input name="title" placeholder="মুভির নাম" value="{movie['title'] if movie else ''}" required>
            <input name="year" placeholder="সাল" value="{movie['year'] if movie else ''}" required>
            <input name="lang" placeholder="ভাষা" value="{movie['language'] if movie else ''}" required>
            <input name="poster" placeholder="পোস্টার ইউআরএল" value="{movie['poster'] if movie else ''}" required>
            <input name="poster_text" placeholder="পোস্টার টেক্স (যেমন: HD)" value="{movie['poster_text'] if movie else ''}">
            <textarea name="desc" placeholder="গল্প...">{movie['description'] if movie else ''}</textarea>
            <input name="shortener" placeholder="লিঙ্ক শর্টনার (ঐচ্ছিক)">
            
            <h3>এপিসোড সমূহ:</h3>
            <div id="ep-area">
                {"".join([f'''
                <div class="ep-input-group">
                    <input name="ep_no[]" placeholder="EP No" value="{e['ep_no']}" required>
                    <input name="dl_link[]" placeholder="Download Link" value="{e['dl_link']}">
                    <input name="st_link[]" placeholder="Stream Link" value="{e['st_link']}">
                    <input name="tg_link[]" placeholder="Telegram Link" value="{e['tg_link']}">
                </div>
                ''' for e in movie['episodes']]) if movie else '<div class="ep-input-group"><input name="ep_no[]" placeholder="EP No" required><input name="dl_link[]" placeholder="DL"><input name="st_link[]" placeholder="ST"><input name="tg_link[]" placeholder="TG"></div>'}
            </div>
            <button type="button" class="submit-btn" style="background:#444;" onclick="addEp()">+ Add Episode Box</button>
            <button type="submit" class="submit-btn">পাবলিশ করুন</button>
        </form>
    </div></div>
    <script>
        function addEp() {{
            const div = document.createElement('div');
            div.className = 'ep-input-group';
            div.innerHTML = '<input name="ep_no[]" placeholder="EP No" required><input name="dl_link[]" placeholder="DL"><input name="st_link[]" placeholder="ST"><input name="tg_link[]" placeholder="TG">';
            document.getElementById('ep-area').appendChild(div);
        }}
    </script></body></html>
    '''
    return render_template_string(html)

@app.route('/admin/delete/<id>', methods=['POST'])
def delete_movie(id):
    series_collection.delete_one({"_id": ObjectId(id)})
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
