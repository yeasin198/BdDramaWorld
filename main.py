import os
import requests
from flask import Flask, render_template_string, request, redirect, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = "movie_pro_ultra_unlimited_final_v5"

# --- MongoDB Connection ---
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client.movie_database
import os
import requests
from flask import Flask, render_template_string, request, redirect, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = "movie_pro_fixed_final_v100"

# --- MongoDB Connection ---
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client.movie_database
movies_col = db.movies
settings_col = db.settings

# --- Helper Functions ---
def shorten_link(url):
    """যেকোনো লিঙ্ক শর্টনার API সাপোর্ট করবে"""
    if not url or not url.strip(): return ""
    try:
        cfg = settings_col.find_one({"type": "config"})
        if cfg and cfg.get('api'):
            api_url = cfg.get('api').replace("{url}", url)
            r = requests.get(api_url, timeout=5)
            return r.text.strip() if r.status_code == 200 else url
    except: pass
    return url

# --- HTML Templates (Variables to avoid f-string conflicts) ---

HEAD_ASSETS = """
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<script src="https://cdn.tailwindcss.com"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.css" />
<script src="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.js"></script>
<style>
    body { background-color: #0b0f19; color: white; font-family: 'Inter', sans-serif; }
    .glass { background: rgba(255, 255, 255, 0.03); backdrop-filter: blur(15px); border: 1px solid rgba(255,255,255,0.05); }
    .corner-tag { position: absolute; padding: 2px 8px; font-size: 10px; font-weight: bold; border-radius: 4px; z-index: 10; }
    .swiper { width: 100%; height: 350px; border-radius: 20px; margin-bottom: 30px; }
    .swiper-slide img { width: 100%; height: 100%; object-fit: cover; }
    ::-webkit-scrollbar { display: none; }
</style>
"""

# --- USER PANEL ROUTES ---

@app.route('/')
def index():
    cfg = settings_col.find_one({"type": "config"}) or {"limit": 15, "slider_limit": 5}
    ads = list(settings_col.find({"type": "ad_unit"}))
    q = request.args.get('q')
    cat = request.args.get('cat')
    
    slider_movies = list(movies_col.find({"in_slider": "on"}).sort("_id", -1).limit(int(cfg.get('slider_limit', 5))))
    filter_q = {}
    if q: filter_q["name"] = {"$regex": q, "$options": "i"}
    if cat: filter_q["category"] = cat
    
    movies = list(movies_col.find(filter_q).sort("_id", -1).limit(int(cfg.get('limit', 15))))
    categories = movies_col.distinct("category")
    
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>"""+HEAD_ASSETS+"""<title>MoviePro - Home</title></head>
    <body>
        <nav class="p-4 glass sticky top-0 z-50 flex justify-between items-center px-6">
            <a href="/" class="text-2xl font-black text-blue-500 uppercase italic tracking-tighter">MoviePro</a>
            <div class="flex gap-4">
                <form action="/" class="hidden md:flex bg-gray-900 border border-gray-700 rounded-lg overflow-hidden">
                    <input name="q" placeholder="Search..." class="bg-transparent p-2 px-4 outline-none w-48 text-sm">
                    <button class="px-3 text-blue-500"><i class="fa fa-search"></i></button>
                </form>
                <a href="/admin" class="bg-blue-600 px-4 py-2 rounded-full text-xs font-bold uppercase">Admin</a>
            </div>
        </nav>

        <div class="max-w-7xl mx-auto p-4 md:p-6">
            <div class="mb-6 space-y-4">{% for ad in ads %}{% if ad.position == 'top' %}{{ ad.code | safe }}{% endif %}{% endfor %}</div>

            {% if slider_movies %}
            <div class="swiper mySwiper">
                <div class="swiper-wrapper">
                    {% for sm in slider_movies %}
                    <div class="swiper-slide relative">
                        <img src="{{ sm.poster }}">
                        <div class="absolute inset-0 bg-gradient-to-t from-black flex flex-col justify-end p-8">
                            <h2 class="text-3xl font-black italic">{{ sm.name }}</h2>
                            <a href="/movie/{{ sm._id }}" class="mt-4 bg-blue-600 w-max px-8 py-2 rounded-full font-bold">WATCH NOW</a>
                        </div>
                    </div>
                    {% endfor %}
                </div>
                <div class="swiper-pagination"></div>
            </div>
            {% endif %}

            <div class="flex gap-3 overflow-x-auto pb-6">
                <a href="/" class="bg-gray-800 px-6 py-2 rounded-full text-xs font-bold shrink-0">ALL</a>
                {% for c in categories %}<a href="/?cat={{ c }}" class="bg-blue-900/30 border border-blue-500/20 px-6 py-2 rounded-full text-xs font-bold shrink-0 uppercase">{{ c }}</a>{% endfor %}
            </div>

            <div class="grid grid-cols-2 md:grid-cols-5 gap-6">
                {% for m in movies %}
                <a href="/movie/{{ m._id }}" class="group relative rounded-2xl overflow-hidden aspect-[2/3] border border-white/5 bg-gray-900 block">
                    <span class="corner-tag top-2 left-2 bg-blue-600">{{ m.tag1 }}</span>
                    <span class="corner-tag top-2 right-2 bg-red-600">{{ m.tag2 }}</span>
                    <span class="corner-tag bottom-2 left-2 bg-yellow-500 text-black">{{ m.tag3 }}</span>
                    <span class="corner-tag bottom-2 right-2 bg-green-600">{{ m.tag4 }}</span>
                    <img src="{{ m.poster }}" class="w-full h-full object-cover group-hover:scale-110 transition duration-500">
                    <div class="absolute inset-0 bg-gradient-to-t from-black p-4 flex flex-col justify-end">
                        <div class="font-bold text-xs truncate">{{ m.name }}</div>
                        <div class="text-[9px] text-gray-500 uppercase">{{ m.year }} | {{ m.category }}</div>
                    </div>
                </a>
                {% endfor %}
            </div>

            <div class="mt-12 space-y-4">{% for ad in ads %}{% if ad.position == 'bottom' %}{{ ad.code | safe }}{% endif %}{% endfor %}</div>
        </div>
        {% for ad in ads %}{% if ad.position == 'popup' %}{{ ad.code | safe }}{% endif %}{% endfor %}
        <script>new Swiper(".mySwiper", { pagination: { el: ".swiper-pagination", clickable: true }, autoplay: { delay: 4000 }, loop: true });</script>
    </body>
    </html>
    """, cfg=cfg, ads=ads, movies=movies, slider_movies=slider_movies, categories=categories)

@app.route('/movie/<id>')
def movie_details(id):
    movie = movies_col.find_one({"_id": ObjectId(id)})
    ads = list(settings_col.find({"type": "ad_unit"}))
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>"""+HEAD_ASSETS+"""<title>{{ movie.name }}</title></head>
    <body class="p-4 md:p-10">
        <div class="max-w-5xl mx-auto">
            <div class="md:flex gap-10 glass p-8 rounded-3xl border border-white/10">
                <img src="{{ movie.poster }}" class="w-full md:w-80 rounded-2xl shadow-2xl mb-6">
                <div class="flex-grow">
                    <h1 class="text-4xl font-black mb-4">{{ movie.name }}</h1>
                    <p class="text-gray-400 leading-relaxed text-sm bg-black/20 p-5 rounded-xl border border-white/5 italic">"{{ movie.story }}"</p>
                </div>
            </div>

            <div class="mt-16 space-y-8">
                {% for ep in movie.episodes %}
                <div class="glass p-6 md:p-8 rounded-[2rem] border-l-8 border-blue-600 shadow-xl">
                    <h3 class="font-black text-xl mb-6 text-blue-400">Episode: {{ ep.ep_no }}</h3>
                    <div class="grid md:grid-cols-2 gap-4">
                        {% for link in ep.links %}
                        <div class="bg-black/40 p-5 rounded-2xl border border-gray-800">
                            <span class="text-[10px] uppercase text-gray-500 block mb-4 font-bold">Quality: {{ link.quality }}</span>
                            <div class="flex flex-wrap gap-2">
                                <a href="{{ link.stream }}" target="_blank" class="grow bg-blue-600 py-3 rounded-xl text-xs font-black text-center">STREAM</a>
                                <a href="{{ link.download }}" target="_blank" class="grow bg-green-600 py-3 rounded-xl text-xs font-black text-center">DOWNLOAD</a>
                                <a href="{{ link.telegram }}" target="_blank" class="bg-sky-500 px-6 py-3 rounded-xl text-xs"><i class="fab fa-telegram"></i></a>
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
    </body>
    </html>
    """, movie=movie, ads=ads)

# --- ADMIN PANEL ROUTES ---

@app.route('/admin')
def admin():
    q = request.args.get('q')
    filter_q = {"name": {"$regex": q, "$options": "i"}} if q else {}
    movies = list(movies_col.find(filter_q).sort("_id", -1))
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>"""+HEAD_ASSETS+"""<title>Admin Dashboard</title></head>
    <body class="p-6">
        <div class="max-w-6xl mx-auto">
            <div class="flex justify-between items-center mb-10">
                <h1 class="text-2xl font-black text-blue-500 uppercase italic">Admin Dashboard</h1>
                <div class="flex gap-4">
                    <a href="/admin/add" class="bg-green-600 p-3 px-6 rounded-xl font-bold text-xs uppercase">+ Add Movie</a>
                    <a href="/admin/settings" class="bg-gray-800 p-3 px-6 rounded-xl font-bold text-xs uppercase italic">Settings</a>
                </div>
            </div>
            <div class="grid gap-4">
                {% for m in movies %}
                <div class="glass p-4 rounded-2xl flex justify-between items-center border border-white/5 shadow-lg">
                    <div class="flex items-center gap-4">
                        <img src="{{ m.poster }}" class="w-12 h-16 object-cover rounded shadow-md">
                        <h3 class="font-bold text-sm">{{ m.name }}</h3>
                    </div>
                    <div class="flex gap-2">
                        <a href="/admin/edit/{{ m._id }}" class="p-3 text-yellow-500 font-bold"><i class="fa fa-edit"></i> Edit</a>
                        <a href="/admin/delete/{{ m._id }}" class="p-3 text-red-500" onclick="return confirm('Delete?')"><i class="fa fa-trash"></i></a>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
    </body>
    </html>
    """, movies=movies)

@app.route('/admin/add', methods=['GET', 'POST'])
@app.route('/admin/edit/<id>', methods=['GET', 'POST'])
def edit_movie(id=None):
    movie = movies_col.find_one({"_id": ObjectId(id)}) if id else None
    
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
            return redirect(url_for('edit_movie', id=id))
        else:
            data['episodes'] = []
            new_id = movies_col.insert_one(data).inserted_id
            return redirect(url_for('edit_movie', id=new_id))

    ep_to_edit = None
    ep_idx = request.args.get('ep_idx')
    if ep_idx is not None and movie and 'episodes' in movie:
        try: ep_to_edit = movie['episodes'][int(ep_idx)]
        except: pass

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>"""+HEAD_ASSETS+"""</head>
    <body class="p-6">
        <div class="max-w-6xl mx-auto grid md:grid-cols-2 gap-10">
            <form method="POST" class="glass p-8 rounded-[2.5rem] border border-white/10 h-max shadow-2xl">
                <h2 class="text-2xl font-black mb-8 italic text-blue-500 uppercase">Movie Details</h2>
                <div class="space-y-4">
                    <input name="name" value="{{ movie.name if movie else '' }}" placeholder="Movie Name" class="w-full bg-black/40 p-4 rounded-xl border border-gray-800 outline-none text-white" required>
                    <input name="poster" value="{{ movie.poster if movie else '' }}" placeholder="Poster URL" class="w-full bg-black/40 p-4 rounded-xl border border-gray-800 outline-none text-white">
                    <div class="grid grid-cols-2 gap-4">
                        <input name="category" value="{{ movie.category if movie else '' }}" placeholder="Category" class="bg-black/40 p-4 rounded-xl border border-gray-800 outline-none text-white">
                        <input name="year" value="{{ movie.year if movie else '' }}" placeholder="Year" class="bg-black/40 p-4 rounded-xl border border-gray-800 outline-none text-white">
                    </div>
                    <input name="lang" value="{{ movie.lang if movie else '' }}" placeholder="Language" class="w-full bg-black/40 p-4 rounded-xl border border-gray-800 outline-none text-white">
                    <div class="grid grid-cols-4 gap-2">
                        <input name="tag1" value="{{ movie.tag1 if movie else '' }}" placeholder="T-L" class="bg-black/40 p-2 rounded-lg border border-gray-800 text-[10px]">
                        <input name="tag2" value="{{ movie.tag2 if movie else '' }}" placeholder="T-R" class="bg-black/40 p-2 rounded-lg border border-gray-800 text-[10px]">
                        <input name="tag3" value="{{ movie.tag3 if movie else '' }}" placeholder="B-L" class="bg-black/40 p-2 rounded-lg border border-gray-800 text-[10px]">
                        <input name="tag4" value="{{ movie.tag4 if movie else '' }}" placeholder="B-R" class="bg-black/40 p-2 rounded-lg border border-gray-800 text-[10px]">
                    </div>
                    <textarea name="story" class="w-full bg-black/40 p-4 rounded-xl h-32 border border-gray-800 outline-none text-sm">{{ movie.story if movie else '' }}</textarea>
                    <label class="flex items-center gap-2 text-xs font-bold text-blue-400">
                        <input type="checkbox" name="in_slider" {{ 'checked' if movie and movie.in_slider == 'on' else '' }}> Feature in Slider
                    </label>
                </div>
                <button name="save_movie" class="w-full bg-blue-600 py-4 rounded-2xl font-black mt-8 uppercase tracking-widest">SAVE MOVIE</button>
            </form>

            {% if movie %}
            <div class="space-y-8">
                <form action="/admin/episode/save" method="POST" class="glass p-8 rounded-[2.5rem] border border-blue-500/20 shadow-2xl">
                    <h2 class="text-2xl font-black mb-6 italic text-green-500 uppercase">{{ 'Edit' if ep_to_edit else 'Add' }} Episode</h2>
                    <input type="hidden" name="mid" value="{{ movie._id }}">
                    <input type="hidden" name="idx" value="{{ ep_idx if ep_idx is not None else '' }}">
                    <input name="ep_no" value="{{ ep_to_edit.ep_no if ep_to_edit else '' }}" placeholder="Episode No (e.g. 01)" class="w-full bg-black/60 p-4 rounded-xl border border-blue-500/30 outline-none mb-6 font-black" required>
                    
                    {% for i in [1, 2] %}
                    <div class="bg-black/40 p-5 rounded-2xl border border-gray-800 mb-4 space-y-3">
                        <input name="q{{i}}_n" value="{{ ep_to_edit.links[i-1].quality if ep_to_edit else '' }}" placeholder="Quality (e.g. 1080p)" class="w-full bg-black/40 p-2 rounded-lg border border-gray-700 outline-none text-xs">
                        <input name="q{{i}}_s" value="{{ ep_to_edit.links[i-1].stream if ep_to_edit else '' }}" placeholder="Stream Link" class="w-full bg-black/40 p-2 rounded-lg border border-gray-700 outline-none text-xs">
                        <input name="q{{i}}_d" value="{{ ep_to_edit.links[i-1].download if ep_to_edit else '' }}" placeholder="Download Link" class="w-full bg-black/40 p-2 rounded-lg border border-gray-700 outline-none text-xs">
                        <input name="q{{i}}_t" value="{{ ep_to_edit.links[i-1].telegram if ep_to_edit else '' }}" placeholder="Telegram Link" class="w-full bg-black/40 p-2 rounded-lg border border-gray-700 outline-none text-xs">
                    </div>
                    {% endfor %}
                    <button class="w-full bg-green-600 py-4 rounded-2xl font-black uppercase tracking-widest">{{ 'Update' if ep_to_edit else 'Upload' }} Episode</button>
                    {% if ep_to_edit %}<a href="/admin/edit/{{ movie._id }}" class="block text-center mt-3 text-xs text-gray-500 underline italic">Cancel Edit</a>{% endif %}
                </form>

                <div class="glass p-6 rounded-[2.5rem] border border-white/5 space-y-3 shadow-xl">
                    <h3 class="font-bold text-sm uppercase text-gray-500 mb-4 italic">Episode List</h3>
                    {% if movie.episodes %}
                    {% for ep in movie.episodes %}
                    <div class="bg-gray-950 p-4 rounded-xl flex justify-between items-center border border-gray-800">
                        <span class="font-black italic text-sm text-blue-400 uppercase">EP {{ ep.ep_no }}</span>
                        <div class="flex gap-4 italic font-bold">
                            <a href="/admin/edit/{{ movie._id }}?ep_idx={{ loop.index0 }}" class="text-yellow-500 text-xs">Edit</a>
                            <a href="/admin/episode/delete/{{ movie._id }}/{{ loop.index0 }}" class="text-red-500 text-xs" onclick="return confirm('Delete?')">Delete</a>
                        </div>
                    </div>
                    {% endfor %}
                    {% else %}
                    <p class="text-xs text-gray-600 text-center italic">No episodes added yet.</p>
                    {% endif %}
                </div>
            </div>
            {% else %}
            <div class="glass p-10 rounded-[2.5rem] border border-dashed border-gray-800 flex items-center justify-center text-gray-700 font-bold italic">Save movie first to add episodes.</div>
            {% endif %}
        </div>
    </body>
    </html>
    """, movie=movie, ep_to_edit=ep_to_edit, ep_idx=ep_idx)

@app.route('/admin/episode/save', methods=['POST'])
def save_episode():
    mid = request.form['mid']
    idx = request.form.get('idx')
    links = []
    for i in [1, 2]:
        links.append({
            "quality": request.form.get(f'q{i}_n', 'HD'),
            "stream": shorten_link(request.form.get(f'q{i}_s', '')),
            "download": shorten_link(request.form.get(f'q{i}_d', '')),
            "telegram": shorten_link(request.form.get(f'q{i}_t', ''))
        })
    new_ep = {"ep_no": request.form['ep_no'], "links": links}
    movie = movies_col.find_one({"_id": ObjectId(mid)})
    if idx and idx.strip() != "":
        movie['episodes'][int(idx)] = new_ep
    else:
        if 'episodes' not in movie: movie['episodes'] = []
        movie['episodes'].append(new_ep)
    movies_col.update_one({"_id": ObjectId(mid)}, {"$set": {"episodes": movie['episodes']}})
    return redirect(url_for('edit_movie', id=mid))

@app.route('/admin/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        if 'save_config' in request.form:
            settings_col.update_one({"type": "config"}, {"$set": {"api": request.form['api'], "limit": request.form['limit'], "slider_limit": request.form['slider_limit']}}, upsert=True)
        elif 'add_ad' in request.form:
            settings_col.insert_one({"type": "ad_unit", "position": request.form['pos'], "code": request.form['code']})
        elif 'del_ad' in request.form:
            settings_col.delete_one({"_id": ObjectId(request.form['ad_id'])})
        return redirect('/admin/settings')
    
    cfg = settings_col.find_one({"type": "config"}) or {"limit": 15, "slider_limit": 5, "api": ""}
    ads = list(settings_col.find({"type": "ad_unit"}))
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>"""+HEAD_ASSETS+"""<title>Settings</title></head>
    <body class="p-6">
        <div class="max-w-5xl mx-auto grid md:grid-cols-2 gap-10">
            <form method="POST" class="glass p-8 rounded-[2.5rem] border border-white/5 h-max shadow-2xl">
                <h2 class="text-2xl font-black mb-8 italic text-blue-500 uppercase">Configuration</h2>
                <div class="space-y-6">
                    <div>
                        <label class="text-[10px] font-bold text-gray-500 uppercase mb-2 block tracking-widest">Shortener API (use {url})</label>
                        <input name="api" value="{{ cfg.api or '' }}" class="w-full bg-black/40 p-4 rounded-xl border border-gray-800 outline-none text-white text-xs">
                    </div>
                    <div class="grid grid-cols-2 gap-4">
                        <input name="limit" type="number" value="{{ cfg.limit or 15 }}" placeholder="Home Limit" class="bg-black/40 p-4 rounded-xl border border-gray-800 outline-none text-white text-xs">
                        <input name="slider_limit" type="number" value="{{ cfg.slider_limit or 5 }}" placeholder="Slider Limit" class="bg-black/40 p-4 rounded-xl border border-gray-800 outline-none text-white text-xs">
                    </div>
                    <button name="save_config" class="w-full bg-blue-600 py-4 rounded-2xl font-black uppercase tracking-widest shadow-xl">Save Config</button>
                </div>
            </form>

            <div class="space-y-8">
                <form method="POST" class="glass p-8 rounded-[2.5rem] border border-yellow-500/20 shadow-2xl">
                    <h2 class="text-2xl font-black mb-6 italic text-yellow-500 uppercase">Add Ad Slot</h2>
                    <select name="pos" class="w-full bg-black/60 p-4 rounded-xl border border-gray-800 outline-none mb-4 text-xs font-bold">
                        <option value="top">Top Banner</option>
                        <option value="bottom">Bottom Banner</option>
                        <option value="popup">Popup Script</option>
                    </select>
                    <textarea name="code" placeholder="Ad HTML/JS Code..." class="w-full bg-black/40 p-4 rounded-xl h-32 border border-gray-800 outline-none text-[10px] mb-4 font-mono text-white"></textarea>
                    <button name="add_ad" class="w-full bg-yellow-600 py-4 rounded-2xl font-black uppercase tracking-widest shadow-xl">Add Ad Code</button>
                </form>

                <div class="glass p-6 rounded-[2.5rem] border border-white/5 space-y-4 shadow-xl">
                    <h3 class="font-bold text-sm uppercase text-gray-500 mb-4 italic">Active Ad Units</h3>
                    {% for ad in ads %}
                    <div class="bg-gray-950 p-4 rounded-xl flex justify-between items-center border border-gray-800">
                        <div>
                            <span class="bg-blue-600/20 text-blue-400 px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-widest">{{ ad.position }}</span>
                            <p class="text-[8px] text-gray-600 mt-1 font-mono truncate w-32">{{ ad.code[:50] }}</p>
                        </div>
                        <form method="POST"><input type="hidden" name="ad_id" value="{{ ad._id }}"><button name="del_ad" class="text-red-500 text-xs font-bold italic">Delete</button></form>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>
    </body>
    </html>
    """, cfg=cfg, ads=ads)

@app.route('/admin/delete/<id>')
def delete_movie(id):
    movies_col.delete_one({"_id": ObjectId(id)})
    return redirect('/admin')

@app.route('/admin/episode/delete/<mid>/<int:idx>')
def delete_episode(mid, idx):
    movie = movies_col.find_one({"_id": ObjectId(mid)})
    movie['episodes'].pop(idx)
    movies_col.update_one({"_id": ObjectId(mid)}, {"$set": {"episodes": movie['episodes']}})
    return redirect(url_for('edit_movie', id=mid))

if __name__ == '__main__':
    app.run(debug=True)
