import os
import requests
from flask import Flask, render_template_string, request, redirect, url_for, flash
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = "movie_pro_ultra_unlimited_v10_fixed"

# --- MongoDB Connection ---
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client.movie_database
movies_col = db.movies
settings_col = db.settings

# --- Context Processor (সব পেজে সেটিংস অটোমেটিক পাঠানোর জন্য) ---
@app.context_processor
def inject_global_vars():
    cfg = settings_col.find_one({"type": "config"}) or {
        "limit": 15, 
        "slider_limit": 5, 
        "api": "",
        "site_name": "MoviePro"
    }
    ads = list(settings_col.find({"type": "ad_unit"}))
    return dict(cfg=cfg, ads=ads)

# --- Helper Functions ---
def shorten_link(url):
    if not url or not url.strip(): return ""
    try:
        cfg = settings_col.find_one({"type": "config"})
        if cfg and cfg.get('api') and "{url}" in cfg.get('api'):
            api_url = cfg.get('api').replace("{url}", url)
            r = requests.get(api_url, timeout=5)
            if r.status_code == 200:
                return r.text.strip()
    except Exception as e:
        print(f"Shortener Error: {e}")
    return url

# --- HTML TEMPLATES ---
COMMON_HEAD = """
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<script src="https://cdn.tailwindcss.com"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.css" />
<script src="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;700;900&display=swap" rel="stylesheet">
<style>
    body { background-color: #0b0f19; color: white; font-family: 'Inter', sans-serif; overflow-x: hidden; }
    .glass { background: rgba(255, 255, 255, 0.03); backdrop-filter: blur(15px); border: 1px solid rgba(255,255,255,0.05); }
    .corner-tag { position: absolute; padding: 2px 8px; font-size: 10px; font-weight: bold; border-radius: 4px; z-index: 10; }
    .movie-card:hover img { transform: scale(1.1); transition: 0.6s cubic-bezier(0.4, 0, 0.2, 1); }
</style>
"""

NAVBAR_HTML = """
<nav class="p-4 glass sticky top-0 z-50 border-b border-white/5">
    <div class="max-w-7xl mx-auto flex justify-between items-center px-4">
        <a href="/" class="text-3xl font-black text-blue-500 uppercase italic tracking-tighter">
            {{ cfg.site_name }}<span class="text-white">PRO</span>
        </a>
        <div class="flex items-center gap-6">
            <form action="/" class="hidden md:flex bg-gray-950/50 border border-gray-800 rounded-full px-4 py-1">
                <input name="q" placeholder="Search..." class="bg-transparent outline-none text-sm p-1 w-48 text-white">
                <button class="text-blue-500"><i class="fa fa-search"></i></button>
            </form>
            <a href="/admin" class="bg-blue-600 hover:bg-blue-700 px-6 py-2 rounded-full text-xs font-black uppercase tracking-widest transition shadow-lg shadow-blue-600/20">Admin</a>
        </div>
    </div>
</nav>
"""

# --- USER ROUTES ---
@app.route('/')
def index():
    q = request.args.get('q')
    cat = request.args.get('cat')
    filter_q = {}
    if q: filter_q["name"] = {"$regex": q, "$options": "i"}
    if cat: filter_q["category"] = cat
    
    cfg = inject_global_vars()['cfg']
    slider_movies = list(movies_col.find({"in_slider": "on"}).sort("_id", -1).limit(int(cfg.get('slider_limit', 5))))
    movies = list(movies_col.find(filter_q).sort("_id", -1).limit(int(cfg.get('limit', 15))))
    categories = movies_col.distinct("category")
    
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en"><head>""" + COMMON_HEAD + """<title>{{cfg.site_name}}</title></head>
    <body>""" + NAVBAR_HTML + """
        <div class="max-w-7xl mx-auto p-4 md:p-6">
            <div class="mb-8 text-center">{% for ad in ads %}{% if ad.position == 'top' %}{{ ad.code | safe }}{% endif %}{% endfor %}</div>
            {% if slider_movies %}
            <div class="swiper mySwiper rounded-3xl overflow-hidden mb-10 h-[400px]">
                <div class="swiper-wrapper">
                    {% for sm in slider_movies %}
                    <div class="swiper-slide relative">
                        <img src="{{ sm.poster }}" class="w-full h-full object-cover">
                        <div class="absolute inset-0 bg-gradient-to-t from-black flex flex-col justify-end p-10">
                            <h2 class="text-4xl font-black italic uppercase">{{ sm.name }}</h2>
                            <a href="/movie/{{ sm._id }}" class="bg-blue-600 w-max px-8 py-3 rounded-full mt-4 font-black">WATCH NOW</a>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
            {% endif %}
            <div class="grid grid-cols-2 md:grid-cols-5 gap-6">
                {% for m in movies %}
                <a href="/movie/{{ m._id }}" class="group relative aspect-[2/3] rounded-2xl overflow-hidden glass block movie-card">
                    <span class="corner-tag top-2 left-2 bg-blue-600">{{ m.tag1 }}</span>
                    <img src="{{ m.poster }}" class="w-full h-full object-cover">
                    <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent p-4 flex flex-col justify-end">
                        <h3 class="font-bold text-sm">{{ m.name }}</h3>
                    </div>
                </a>
                {% endfor %}
            </div>
        </div>
        <script>new Swiper(".mySwiper", { loop: true, autoplay: true });</script>
    </body></html>""")

@app.route('/movie/<id>')
def movie_details(id):
    try:
        movie = movies_col.find_one({"_id": ObjectId(id)})
        if not movie: return redirect('/')
    except: return redirect('/')
    
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en"><head>""" + COMMON_HEAD + """<title>{{ movie.name }}</title></head>
    <body>""" + NAVBAR_HTML + """
        <div class="max-w-6xl mx-auto p-6">
            <div class="md:flex gap-10 glass p-8 rounded-[2rem]">
                <img src="{{ movie.poster }}" class="w-full md:w-72 rounded-xl shadow-2xl">
                <div>
                    <h1 class="text-4xl font-black italic uppercase mb-4">{{ movie.name }}</h1>
                    <p class="text-gray-400 mb-6 italic">{{ movie.story }}</p>
                    <div class="flex gap-4"><span class="bg-blue-600 px-4 py-1 rounded-full text-xs font-bold">{{ movie.category }}</span></div>
                </div>
            </div>
            <div class="mt-10 space-y-6">
                {% for ep in movie.episodes %}
                <div class="glass p-6 rounded-3xl border-l-8 border-blue-600">
                    <h3 class="text-xl font-black mb-4 uppercase">Episode: {{ ep.ep_no }}</h3>
                    <div class="grid md:grid-cols-2 gap-4">
                        {% for link in ep.links %}
                        <div class="bg-black/40 p-4 rounded-xl">
                            <span class="text-[10px] text-gray-500 font-bold uppercase">{{ link.quality }}</span>
                            <div class="flex gap-2 mt-2">
                                <a href="{{ link.stream }}" target="_blank" class="bg-blue-600 px-4 py-2 rounded-lg text-xs font-bold">STREAM</a>
                                <a href="{{ link.download }}" target="_blank" class="bg-green-600 px-4 py-2 rounded-lg text-xs font-bold">DOWNLOAD</a>
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
    </body></html>""", movie=movie)

# --- ADMIN ROUTES ---
@app.route('/admin')
def admin_dash():
    q = request.args.get('q')
    filter_q = {"name": {"$regex": q, "$options": "i"}} if q else {}
    movies = list(movies_col.find(filter_q).sort("_id", -1))
    return render_template_string("""
    <!DOCTYPE html><html><head>""" + COMMON_HEAD + """</head>
    <body class="p-6">""" + NAVBAR_HTML + """
        <div class="max-w-6xl mx-auto mt-10">
            <div class="flex justify-between items-center mb-10">
                <h1 class="text-2xl font-black italic uppercase">Admin Dashboard</h1>
                <div class="flex gap-4">
                    <a href="/admin/settings" class="bg-gray-700 px-6 py-3 rounded-xl font-bold">SETTINGS</a>
                    <a href="/admin/add" class="bg-green-600 px-6 py-3 rounded-xl font-bold">+ ADD MOVIE</a>
                </div>
            </div>
            <div class="grid gap-4">
                {% for m in movies %}
                <div class="glass p-4 rounded-2xl flex justify-between items-center">
                    <div class="flex items-center gap-4">
                        <img src="{{ m.poster }}" class="w-10 h-14 object-cover rounded-lg">
                        <span class="font-bold">{{ m.name }}</span>
                    </div>
                    <div class="flex gap-2">
                        <a href="/admin/edit/{{ m._id }}" class="bg-yellow-500 text-black px-4 py-2 rounded-lg font-bold text-xs">EDIT</a>
                        <a href="/admin/delete/{{ m._id }}" class="bg-red-600 px-4 py-2 rounded-lg font-bold text-xs" onclick="return confirm('Delete?')">DEL</a>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
    </body></html>""", movies=movies)

@app.route('/admin/add', methods=['GET', 'POST'])
@app.route('/admin/edit/<id>', methods=['GET', 'POST'])
def manage_movie(id=None):
    movie = None
    if id:
        try: movie = movies_col.find_one({"_id": ObjectId(id)})
        except: return redirect('/admin')

    if request.method == 'POST' and 'save_movie' in request.form:
        data = {
            "name": request.form['name'], "poster": request.form['poster'],
            "year": request.form['year'], "lang": request.form['lang'],
            "category": request.form['category'].strip().upper(),
            "tag1": request.form['tag1'], "tag2": request.form['tag2'],
            "tag3": request.form['tag3'], "tag4": request.form['tag4'],
            "story": request.form['story'], "in_slider": request.form.get('in_slider', 'off')
        }
        if id:
            movies_col.update_one({"_id": ObjectId(id)}, {"$set": data})
            return redirect(url_for('manage_movie', id=id))
        else:
            data['episodes'] = []
            new_id = movies_col.insert_one(data).inserted_id
            return redirect(url_for('manage_movie', id=new_id))

    ep_idx = request.args.get('ep_idx')
    ep_to_edit = None
    if ep_idx is not None and movie and 'episodes' in movie:
        try: ep_to_edit = movie['episodes'][int(ep_idx)]
        except: pass

    return render_template_string("""
    <!DOCTYPE html><html><head>""" + COMMON_HEAD + """</head>
    <body class="p-6">""" + NAVBAR_HTML + """
        <div class="max-w-7xl mx-auto mt-10 grid md:grid-cols-2 gap-10">
            <form method="POST" class="glass p-8 rounded-3xl h-max">
                <h2 class="text-xl font-black mb-6 italic text-blue-500 uppercase">Movie Details</h2>
                <div class="space-y-4">
                    <input name="name" value="{{ movie.name if movie else '' }}" placeholder="Name" class="w-full bg-black/40 p-4 rounded-xl border border-gray-800 text-white" required>
                    <input name="poster" value="{{ movie.poster if movie else '' }}" placeholder="Poster URL" class="w-full bg-black/40 p-4 rounded-xl border border-gray-800 text-white">
                    <div class="grid grid-cols-2 gap-4">
                        <input name="category" value="{{ movie.category if movie else '' }}" placeholder="Category" class="bg-black/40 p-4 rounded-xl border border-gray-800 text-white">
                        <input name="year" value="{{ movie.year if movie else '' }}" placeholder="Year" class="bg-black/40 p-4 rounded-xl border border-gray-800 text-white">
                    </div>
                    <input name="lang" value="{{ movie.lang if movie else '' }}" placeholder="Language" class="w-full bg-black/40 p-4 rounded-xl border border-gray-800 text-white">
                    <div class="grid grid-cols-2 gap-4">
                        <input name="tag1" value="{{ movie.tag1 if movie else '' }}" placeholder="Tag 1" class="bg-black/40 p-3 rounded-lg border border-gray-800 text-white text-xs">
                        <input name="tag2" value="{{ movie.tag2 if movie else '' }}" placeholder="Tag 2" class="bg-black/40 p-3 rounded-lg border border-gray-800 text-white text-xs">
                        <input name="tag3" value="{{ movie.tag3 if movie else '' }}" placeholder="Tag 3" class="bg-black/40 p-3 rounded-lg border border-gray-800 text-white text-xs">
                        <input name="tag4" value="{{ movie.tag4 if movie else '' }}" placeholder="Tag 4" class="bg-black/40 p-3 rounded-lg border border-gray-800 text-white text-xs">
                    </div>
                    <textarea name="story" class="w-full bg-black/40 p-4 rounded-xl border border-gray-800 text-white h-32">{{ movie.story if movie else '' }}</textarea>
                    <label class="flex items-center gap-2"><input type="checkbox" name="in_slider" {{ 'checked' if movie and movie.in_slider == 'on' else '' }}> Show in Slider</label>
                    <button name="save_movie" class="w-full bg-blue-600 py-4 rounded-xl font-black">SAVE MOVIE</button>
                    <a href="/admin" class="block text-center text-xs text-gray-500 uppercase mt-4">Back to Dashboard</a>
                </div>
            </form>

            {% if movie %}
            <div class="space-y-6">
                <form action="/admin/episode/save" method="POST" class="glass p-8 rounded-3xl border border-blue-500/20">
                    <h2 class="text-xl font-black mb-6 uppercase text-green-500">{{ 'Edit' if ep_to_edit else 'Add' }} Episode</h2>
                    <input type="hidden" name="mid" value="{{ movie._id }}">
                    <input type="hidden" name="idx" value="{{ ep_idx if ep_idx is not None else '' }}">
                    <input name="ep_no" value="{{ ep_to_edit.ep_no if ep_to_edit else '' }}" placeholder="Episode No" class="w-full bg-black/40 p-4 rounded-xl border border-gray-800 mb-4 text-white" required>
                    
                    {% for i in range(1, 3) %}
                    {% set link = ep_to_edit.links[i-1] if (ep_to_edit and ep_to_edit.links and ep_to_edit.links|length >= i) else None %}
                    <div class="bg-black/20 p-4 rounded-xl mb-4 border border-white/5">
                        <p class="text-[10px] text-gray-500 uppercase font-black mb-2">Slot {{ i }}</p>
                        <input name="q{{i}}_n" value="{{ link.quality if link else '' }}" placeholder="Quality (720p)" class="w-full bg-black/40 p-2 rounded-lg border border-gray-800 mb-2 text-white text-xs">
                        <input name="q{{i}}_s" value="{{ link.stream if link else '' }}" placeholder="Stream Link" class="w-full bg-black/40 p-2 rounded-lg border border-gray-800 mb-2 text-white text-xs">
                        <input name="q{{i}}_d" value="{{ link.download if link else '' }}" placeholder="Download Link" class="w-full bg-black/40 p-2 rounded-lg border border-gray-800 mb-2 text-white text-xs">
                        <input name="q{{i}}_t" value="{{ link.telegram if link else '' }}" placeholder="Telegram Link" class="w-full bg-black/40 p-2 rounded-lg border border-gray-800 text-white text-xs">
                    </div>
                    {% endfor %}
                    <button class="w-full bg-green-600 py-4 rounded-xl font-black">SAVE EPISODE</button>
                    {% if ep_to_edit %}<a href="/admin/edit/{{ movie._id }}" class="block text-center text-xs text-gray-500 mt-2">CANCEL EDIT</a>{% endif %}
                </form>

                <div class="glass p-6 rounded-3xl">
                    <h3 class="font-bold text-sm text-gray-500 mb-4 uppercase italic">Episodes List</h3>
                    {% for ep in movie.episodes %}
                    <div class="flex justify-between items-center bg-black/40 p-4 rounded-xl mb-2">
                        <span class="font-bold uppercase">EPISODE {{ ep.ep_no }}</span>
                        <div class="flex gap-4 text-[10px] font-bold">
                            <a href="/admin/edit/{{ movie._id }}?ep_idx={{ loop.index0 }}" class="text-yellow-500">EDIT</a>
                            <a href="/admin/episode/delete/{{ movie._id }}/{{ loop.index0 }}" class="text-red-500">DEL</a>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
            {% endif %}
        </div>
    </body></html>""", movie=movie, ep_to_edit=ep_to_edit, ep_idx=ep_idx)

@app.route('/admin/episode/save', methods=['POST'])
def save_episode():
    mid = request.form['mid']
    idx_str = request.form.get('idx')
    links = []
    for i in range(1, 3):
        links.append({
            "quality": request.form.get(f'q{i}_n', 'HD'),
            "stream": shorten_link(request.form.get(f'q{i}_s', '')),
            "download": shorten_link(request.form.get(f'q{i}_d', '')),
            "telegram": shorten_link(request.form.get(f'q{i}_t', ''))
        })
    new_ep = {"ep_no": request.form['ep_no'], "links": links}
    try:
        movie = movies_col.find_one({"_id": ObjectId(mid)})
        if movie:
            episodes = movie.get('episodes', [])
            if idx_str and idx_str.strip() != "":
                idx = int(idx_str)
                if idx < len(episodes): episodes[idx] = new_ep
            else:
                episodes.append(new_ep)
            movies_col.update_one({"_id": ObjectId(mid)}, {"$set": {"episodes": episodes}})
    except Exception as e: print(e)
    return redirect(url_for('manage_movie', id=mid))

@app.route('/admin/episode/delete/<mid>/<int:idx>')
def delete_episode(mid, idx):
    try:
        movie = movies_col.find_one({"_id": ObjectId(mid)})
        if movie and 'episodes' in movie:
            eps = movie['episodes']
            if idx < len(eps):
                eps.pop(idx)
                movies_col.update_one({"_id": ObjectId(mid)}, {"$set": {"episodes": eps}})
    except: pass
    return redirect(url_for('manage_movie', id=mid))

@app.route('/admin/delete/<id>')
def delete_movie(id):
    try: movies_col.delete_one({"_id": ObjectId(id)})
    except: pass
    return redirect('/admin')

@app.route('/admin/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        if 'save_config' in request.form:
            settings_col.update_one({"type": "config"}, {"$set": {
                "api": request.form['api'], "limit": int(request.form['limit']), 
                "slider_limit": int(request.form['slider_limit']), "site_name": request.form.get('site_name', 'MoviePro')
            }}, upsert=True)
        elif 'add_ad' in request.form:
            settings_col.insert_one({"type": "ad_unit", "position": request.form['pos'], "code": request.form['code']})
        elif 'del_ad' in request.form:
            settings_col.delete_one({"_id": ObjectId(request.form['ad_id'])})
        return redirect('/admin/settings')
    return render_template_string("""
    <!DOCTYPE html><html><head>""" + COMMON_HEAD + """</head>
    <body class="p-6">""" + NAVBAR_HTML + """
        <div class="max-w-4xl mx-auto mt-10 space-y-10">
            <form method="POST" class="glass p-8 rounded-3xl">
                <h2 class="text-xl font-black mb-6 uppercase italic">Global Settings</h2>
                <div class="space-y-4">
                    <input name="site_name" value="{{ cfg.site_name }}" class="w-full bg-black/40 p-4 rounded-xl border border-gray-800 text-white">
                    <input name="api" value="{{ cfg.api }}" placeholder="Shortener API" class="w-full bg-black/40 p-4 rounded-xl border border-gray-800 text-xs text-blue-400">
                    <div class="grid grid-cols-2 gap-4">
                        <input name="limit" type="number" value="{{ cfg.limit }}" class="bg-black/40 p-4 rounded-xl border border-gray-800 text-white">
                        <input name="slider_limit" type="number" value="{{ cfg.slider_limit }}" class="bg-black/40 p-4 rounded-xl border border-gray-800 text-white">
                    </div>
                    <button name="save_config" class="w-full bg-blue-600 py-4 rounded-xl font-black">SAVE CONFIG</button>
                </div>
            </form>
            <div class="glass p-8 rounded-3xl">
                <h2 class="text-xl font-black mb-6 uppercase italic">Ads Inventory</h2>
                <form method="POST" class="space-y-4 mb-6">
                    <select name="pos" class="w-full bg-black/40 p-4 rounded-xl border border-gray-800 text-white">
                        <option value="top">Top Banner</option><option value="bottom">Bottom Banner</option><option value="popup">Popup Script</option>
                    </select>
                    <textarea name="code" class="w-full bg-black/40 p-4 rounded-xl border border-gray-800 text-white h-24" placeholder="Ad Code"></textarea>
                    <button name="add_ad" class="w-full bg-yellow-600 text-black py-4 rounded-xl font-black">ADD AD UNIT</button>
                </form>
                {% for ad in ads %}
                <div class="flex justify-between items-center bg-black/40 p-4 rounded-xl mb-2">
                    <span class="text-xs uppercase font-bold">{{ ad.position }}</span>
                    <form method="POST"><input type="hidden" name="ad_id" value="{{ ad._id }}"><button name="del_ad" class="text-red-500 font-bold text-xs">REMOVE</button></form>
                </div>
                {% endfor %}
            </div>
            <a href="/admin" class="block text-center text-xs text-gray-500 uppercase">Back to Dashboard</a>
        </div>
    </body></html>""")

if __name__ == '__main__':
    app.run(debug=True)
