import os
from flask import Flask, render_template_string, request, redirect, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId
import requests

app = Flask(__name__)
app.secret_key = "movie_pro_final_unlimited_fixed"

# --- MongoDB Connection ---
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

client = MongoClient(MONGO_URI)
db = client.movie_database
movies_col = db.movies
settings_col = db.settings

# --- Helper Functions ---
def shorten_link(url):
    """লিঙ্ক শর্টনার এপিআই কল করার ফাংশন"""
    if not url or not url.strip():
        return ""
    try:
        config = settings_col.find_one({"type": "config"})
        if config and config.get('api'):
            api_url = config.get('api').replace("{url}", url)
            r = requests.get(api_url, timeout=5)
            if r.status_code == 200:
                return r.text.strip()
    except:
        pass
    return url

def get_site_data():
    ads = settings_col.find_one({"type": "ads"}) or {"top": "", "bottom": "", "popup": ""}
    cfg = settings_col.find_one({"type": "config"}) or {"limit": 15, "slider_limit": 5, "api": ""}
    return ads, cfg

# --- UI Assets (Head) ---
HEAD_HTML = """
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

# --- USER ROUTES ---

@app.route('/')
def index():
    ads, cfg = get_site_data()
    q = request.args.get('q')
    cat = request.args.get('cat')
    
    s_limit = int(cfg.get('slider_limit', 5))
    m_limit = int(cfg.get('limit', 15))
    
    slider_movies = list(movies_col.find({"in_slider": "on"}).sort("_id", -1).limit(s_limit))
    
    filter_q = {}
    if q: filter_q["name"] = {"$regex": q, "$options": "i"}
    if cat: filter_q["category"] = cat
    
    movies = list(movies_col.find(filter_q).sort("_id", -1).limit(m_limit))
    categories = movies_col.distinct("category")
    
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>"""+HEAD_HTML+"""<title>MoviePro - Home</title></head>
    <body>
        <nav class="p-4 glass sticky top-0 z-50 flex justify-between items-center px-6">
            <a href="/" class="text-2xl font-black text-blue-500">MOVIE<span class="text-white">PRO</span></a>
            <form action="/" class="hidden md:flex bg-gray-900 border border-gray-700 rounded-lg overflow-hidden">
                <input name="q" placeholder="Search..." class="bg-transparent p-2 px-4 outline-none w-64 text-sm text-white">
                <button class="px-4 text-blue-500"><i class="fa fa-search"></i></button>
            </form>
            <a href="/admin" class="bg-blue-600 px-5 py-2 rounded-full text-xs font-bold uppercase">Admin</a>
        </nav>

        <div class="max-w-7xl mx-auto p-4 md:p-6">
            <div class="mb-6 text-center">{{ ads['top'] | safe }}</div>

            {% if slider_movies %}
            <div class="swiper mySwiper">
                <div class="swiper-wrapper">
                    {% for sm in slider_movies %}
                    <div class="swiper-slide relative">
                        <img src="{{ sm.poster }}" loading="lazy">
                        <div class="absolute inset-0 bg-gradient-to-t from-black via-transparent flex flex-col justify-end p-8">
                            <h2 class="text-3xl font-black italic uppercase">{{ sm.name }}</h2>
                            <a href="/movie/{{ sm._id }}" class="mt-4 bg-blue-600 w-max px-8 py-2 rounded-full font-bold text-sm shadow-xl tracking-widest">WATCH NOW</a>
                        </div>
                    </div>
                    {% endfor %}
                </div>
                <div class="swiper-pagination"></div>
            </div>
            {% endif %}

            <div class="flex gap-3 overflow-x-auto pb-6">
                <a href="/" class="bg-gray-800 px-6 py-2 rounded-full text-xs font-bold uppercase shrink-0">ALL</a>
                {% for c in categories %}
                <a href="/?cat={{ c }}" class="bg-blue-900/30 border border-blue-500/20 px-6 py-2 rounded-full text-xs font-bold uppercase shrink-0">{{ c }}</a>
                {% endfor %}
            </div>

            <h2 class="text-xl font-bold mb-8 italic text-blue-500 border-l-4 border-blue-500 pl-3 uppercase">Latest Updates</h2>
            <div class="grid grid-cols-2 md:grid-cols-5 gap-6">
                {% for m in movies %}
                <a href="/movie/{{ m._id }}" class="group block relative rounded-2xl overflow-hidden shadow-2xl aspect-[2/3] border border-white/5 bg-gray-900">
                    <span class="corner-tag top-2 left-2 bg-blue-600">{{ m.tag1 or '' }}</span>
                    <span class="corner-tag top-2 right-2 bg-red-600">{{ m.tag2 or '' }}</span>
                    <span class="corner-tag bottom-2 left-2 bg-yellow-500 text-black">{{ m.tag3 or '' }}</span>
                    <span class="corner-tag bottom-2 right-2 bg-green-600">{{ m.tag4 or '' }}</span>
                    <img src="{{ m.poster }}" class="w-full h-full object-cover group-hover:scale-110 transition duration-500" loading="lazy">
                    <div class="absolute inset-0 bg-gradient-to-t from-black via-transparent p-4 flex flex-col justify-end">
                        <div class="font-bold text-xs truncate">{{ m.name }}</div>
                        <div class="text-[9px] text-gray-500 mt-1 uppercase">{{ m.year }} | {{ m.category }}</div>
                    </div>
                </a>
                {% endfor %}
            </div>
            
            <div class="mt-12 text-center">{{ ads['bottom'] | safe }}</div>
        </div>
        {{ ads['popup'] | safe }}

        <script>
            var swiper = new Swiper(".mySwiper", {
                pagination: { el: ".swiper-pagination", clickable: true },
                autoplay: { delay: 4000 },
                loop: true
            });
        </script>
    </body>
    </html>
    """, ads=ads, movies=movies, slider_movies=slider_movies, categories=categories)

@app.route('/movie/<id>')
def movie_details(id):
    try:
        movie = movies_col.find_one({"_id": ObjectId(id)})
        ads, _ = get_site_data()
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>"""+HEAD_HTML+"""<title>{{ movie.name }}</title></head>
        <body class="p-4 md:p-10">
            <div class="max-w-5xl mx-auto">
                <div class="md:flex gap-10 glass p-8 rounded-[2.5rem] border border-white/10 shadow-2xl">
                    <img src="{{ movie.poster }}" class="w-full md:w-80 rounded-2xl shadow-2xl mb-6">
                    <div class="flex-grow">
                        <h1 class="text-4xl md:text-5xl font-black mb-4 tracking-tighter">{{ movie.name }}</h1>
                        <div class="flex flex-wrap gap-4 mb-8">
                            <span class="text-blue-500 font-black uppercase text-xs tracking-widest">{{ movie.category }}</span>
                            <span class="text-gray-500 font-bold text-xs">{{ movie.year }}</span>
                            <span class="text-gray-500 font-bold text-xs uppercase">{{ movie.lang }}</span>
                        </div>
                        <div class="bg-black/20 p-6 rounded-2xl border border-white/5">
                            <h3 class="text-[10px] font-black text-blue-600 uppercase mb-2 tracking-[0.2em]">Storyline</h3>
                            <p class="text-gray-400 leading-relaxed text-sm italic">"{{ movie.story }}"</p>
                        </div>
                    </div>
                </div>

                <div class="mt-12 text-center">{{ ads['top'] | safe }}</div>

                <h2 class="text-2xl font-black mt-16 mb-8 italic flex items-center gap-4 text-blue-500">
                    <span class="w-10 h-1 bg-blue-600 rounded-full"></span> EPISODES & DOWNLOAD
                </h2>
                <div class="space-y-6">
                    {% for ep in movie.episodes %}
                    <div class="glass p-6 md:p-8 rounded-[2rem] border-l-[10px] border-blue-600 shadow-xl">
                        <h3 class="font-black text-xl mb-6 italic">Episode: {{ ep.ep_no }}</h3>
                        <div class="grid md:grid-cols-2 gap-6">
                            {% for link in ep.links %}
                            <div class="bg-black/40 p-5 rounded-2xl border border-gray-800">
                                <span class="text-[10px] uppercase text-gray-500 block mb-4 font-black tracking-widest">Server Quality: {{ link.quality }}</span>
                                <div class="flex flex-wrap gap-3">
                                    <a href="{{ link.stream }}" target="_blank" class="flex-grow bg-blue-600 hover:bg-blue-700 py-3 rounded-xl text-xs font-black text-center shadow-lg">STREAM</a>
                                    <a href="{{ link.download }}" target="_blank" class="flex-grow bg-green-600 hover:bg-green-700 py-3 rounded-xl text-xs font-black text-center shadow-lg">DOWNLOAD</a>
                                    <a href="{{ link.telegram }}" target="_blank" class="bg-sky-500 hover:bg-sky-600 px-6 py-3 rounded-xl text-xs font-black text-center"><i class="fab fa-telegram"></i></a>
                                </div>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                    {% endfor %}
                </div>
                <div class="mt-12 text-center">{{ ads['bottom'] | safe }}</div>
            </div>
            {{ ads['popup'] | safe }}
        </body>
        </html>
        """, movie=movie, ads=ads)
    except:
        return redirect('/')

# --- ADMIN ROUTES ---

@app.route('/admin')
def admin_dash():
    q = request.args.get('q')
    filter_q = {"name": {"$regex": q, "$options": "i"}} if q else {}
    movies = list(movies_col.find(filter_q).sort("_id", -1))
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>"""+HEAD_HTML+"""<title>Admin Dashboard</title></head>
    <body class="p-6">
        <div class="max-w-6xl mx-auto">
            <div class="flex flex-col md:flex-row justify-between items-center mb-12 gap-6">
                <h1 class="text-3xl font-black italic text-blue-500 uppercase">Admin Panel</h1>
                <div class="flex gap-4 w-full md:w-auto">
                    <form action="/admin" class="flex flex-grow bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
                        <input name="q" placeholder="Search movies..." class="bg-transparent p-3 px-5 outline-none text-sm w-full text-white">
                        <button class="px-6 text-blue-500"><i class="fa fa-search"></i></button>
                    </form>
                    <a href="/admin/add" class="bg-green-600 p-3 px-8 rounded-xl font-black text-xs uppercase tracking-widest">+ Add Movie</a>
                    <a href="/admin/settings" class="bg-gray-800 p-3 px-6 rounded-xl font-black text-xs uppercase"><i class="fa fa-cog"></i></a>
                </div>
            </div>
            <div class="grid gap-4">
                {% for m in movies %}
                <div class="glass p-4 rounded-2xl flex justify-between items-center border border-white/5 shadow-lg">
                    <div class="flex items-center gap-4">
                        <img src="{{ m.poster }}" class="w-12 h-16 object-cover rounded shadow-md">
                        <div>
                            <h3 class="font-bold text-sm">{{ m.name }}</h3>
                            <span class="text-[9px] font-bold text-blue-400 uppercase">{{ m.category }}</span>
                        </div>
                    </div>
                    <div class="flex gap-2">
                        <a href="/admin/edit/{{ m._id }}" class="p-3 text-yellow-500 hover:bg-yellow-500/10 rounded-xl"><i class="fa fa-edit"></i></a>
                        <a href="/admin/delete/{{ m._id }}" class="p-3 text-red-500 hover:bg-red-500/10 rounded-xl" onclick="return confirm('Delete?')"><i class="fa fa-trash"></i></a>
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
def manage_movie(id=None):
    movie = movies_col.find_one({"_id": ObjectId(id)}) if id else None
    if request.method == 'POST':
        data = {
            "name": request.form['name'], "poster": request.form['poster'],
            "year": request.form['year'], "lang": request.form['lang'],
            "category": request.form['category'].strip().upper(),
            "tag1": request.form['tag1'], "tag2": request.form['tag2'],
            "tag3": request.form['tag3'], "tag4": request.form['tag4'],
            "story": request.form['story'],
            "in_slider": request.form.get('in_slider', 'off')
        }
        if id:
            movies_col.update_one({"_id": ObjectId(id)}, {"$set": data})
        else:
            data['episodes'] = []
            movies_col.insert_one(data)
        return redirect('/admin')
    
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>"""+HEAD_HTML+"""</head>
    <body class="p-6">
        <form method="POST" class="max-w-4xl mx-auto glass p-10 rounded-[3rem] border border-white/10 shadow-2xl">
            <h2 class="text-3xl font-black mb-10 italic text-blue-500 uppercase tracking-tighter">Movie Configuration</h2>
            <div class="grid md:grid-cols-2 gap-6 mb-8">
                <input name="name" value="{{ movie.name if movie else '' }}" placeholder="Movie Name" class="w-full bg-black/40 p-4 rounded-2xl border border-gray-800 outline-none text-white focus:border-blue-500" required>
                <input name="poster" value="{{ movie.poster if movie else '' }}" placeholder="Poster URL" class="w-full bg-black/40 p-4 rounded-2xl border border-gray-800 outline-none text-white focus:border-blue-500">
                <input name="category" value="{{ movie.category if movie else '' }}" placeholder="Category (e.g. ACTION)" class="w-full bg-black/40 p-4 rounded-2xl border border-gray-800 outline-none text-white">
                <div class="flex gap-4">
                    <input name="year" value="{{ movie.year if movie else '' }}" placeholder="Year" class="w-full bg-black/40 p-4 rounded-2xl border border-gray-800 outline-none text-white w-1/2">
                    <input name="lang" value="{{ movie.lang if movie else '' }}" placeholder="Lang" class="w-full bg-black/40 p-4 rounded-2xl border border-gray-800 outline-none text-white w-1/2">
                </div>
            </div>
            <div class="flex items-center gap-4 mb-8 bg-blue-600/10 p-5 rounded-2xl border border-blue-500/20">
                <input type="checkbox" name="in_slider" {{ 'checked' if movie and movie.in_slider == 'on' else '' }} class="w-6 h-6 rounded">
                <label class="font-bold text-sm text-blue-400">Featured in Home Slider</label>
            </div>
            <div class="grid grid-cols-4 gap-4 mb-8">
                <input name="tag1" value="{{ movie.tag1 if movie else '' }}" placeholder="Tag 1" class="bg-black/40 p-3 rounded-xl border border-gray-800 text-[10px]">
                <input name="tag2" value="{{ movie.tag2 if movie else '' }}" placeholder="Tag 2" class="bg-black/40 p-3 rounded-xl border border-gray-800 text-[10px]">
                <input name="tag3" value="{{ movie.tag3 if movie else '' }}" placeholder="Tag 3" class="bg-black/40 p-3 rounded-xl border border-gray-800 text-[10px]">
                <input name="tag4" value="{{ movie.tag4 if movie else '' }}" placeholder="Tag 4" class="bg-black/40 p-3 rounded-xl border border-gray-800 text-[10px]">
            </div>
            <textarea name="story" placeholder="Storyline..." class="w-full bg-black/40 p-5 rounded-2xl h-40 border border-gray-800 outline-none mb-10 text-sm text-white">{{ movie.story if movie else '' }}</textarea>
            <div class="flex flex-col md:flex-row gap-4">
                <button class="bg-blue-600 py-5 px-12 rounded-3xl font-black grow shadow-2xl uppercase tracking-widest">SAVE MOVIE</button>
                {% if movie %}
                <a href="/admin/episodes/{{ movie._id }}" class="bg-gray-800 px-12 py-5 rounded-3xl font-black text-blue-400 text-center uppercase tracking-widest">MANAGE EPISODES</a>
                {% endif %}
            </div>
        </form>
    </body>
    </html>
    """, movie=movie)

@app.route('/admin/episodes/<mid>')
def episode_list(mid):
    movie = movies_col.find_one({"_id": ObjectId(mid)})
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>"""+HEAD_HTML+"""</head>
    <body class="p-6">
        <div class="max-w-4xl mx-auto">
            <div class="flex justify-between items-center mb-10">
                <h2 class="text-2xl font-black italic text-blue-500 uppercase tracking-tighter">Episodes: {{ movie.name }}</h2>
                <a href="/admin/episode/add/{{ mid }}" class="bg-green-600 p-3 px-8 rounded-2xl font-bold text-xs uppercase shadow-xl">+ NEW EPISODE</a>
            </div>
            <div class="grid gap-4">
                {% for ep in movie.episodes %}
                <div class="glass p-6 rounded-[2rem] flex justify-between items-center border border-white/5 shadow-lg">
                    <span class="font-black italic uppercase text-sm tracking-widest text-blue-400">Episode {{ ep.ep_no }}</span>
                    <div class="flex gap-4">
                        <a href="/admin/episode/edit/{{ mid }}/{{ loop.index0 }}" class="text-yellow-500 hover:scale-125 transition"><i class="fa fa-edit"></i></a>
                        <a href="/admin/episode/delete/{{ mid }}/{{ loop.index0 }}" class="text-red-500 hover:scale-125 transition" onclick="return confirm('Delete?')"><i class="fa fa-trash"></i></a>
                    </div>
                </div>
                {% endfor %}
            </div>
            <div class="mt-12"><a href="/admin" class="text-gray-500 font-bold underline italic">← BACK TO DASHBOARD</a></div>
        </div>
    </body>
    </html>
    """, movie=movie, mid=mid)

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
    
    if idx and idx.strip():
        movie['episodes'][int(idx)] = new_ep
    else:
        if 'episodes' not in movie: movie['episodes'] = []
        movie['episodes'].append(new_ep)
    
    movies_col.update_one({"_id": ObjectId(mid)}, {"$set": {"episodes": movie['episodes']}})
    return redirect(url_for('episode_list', mid=mid))

@app.route('/admin/episode/add/<mid>')
@app.route('/admin/episode/edit/<mid>/<int:idx>')
def episode_form(mid, idx=None):
    movie = movies_col.find_one({"_id": ObjectId(mid)})
    ep = movie['episodes'][idx] if idx is not None else None
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>"""+HEAD_HTML+"""</head>
    <body class="p-6">
        <form method="POST" action="/admin/episode/save" class="max-w-2xl mx-auto glass p-10 rounded-[3rem] border border-white/10 shadow-2xl">
            <input type="hidden" name="mid" value="{{ mid }}">
            <input type="hidden" name="idx" value="{{ idx if idx is not None else '' }}">
            <h2 class="text-2xl font-black italic mb-10 uppercase text-blue-500 tracking-tighter">Episode Editor</h2>
            <input name="ep_no" value="{{ ep.ep_no if ep else '' }}" placeholder="Episode (e.g. 01)" class="w-full bg-black/40 p-5 rounded-2xl mb-8 border border-blue-500/30 outline-none text-white font-black" required>
            
            {% for i in [1, 2] %}
            <div class="bg-black/30 p-8 rounded-3xl border border-gray-800 mb-8 shadow-inner">
                <h3 class="text-blue-500 font-black text-[10px] uppercase italic tracking-widest mb-6 opacity-60">Slot {{ i }} (Quality)</h3>
                <input name="q{{i}}_n" value="{{ ep.links[i-1].quality if ep else '' }}" placeholder="Quality (e.g. 1080p)" class="w-full bg-black/40 p-4 rounded-xl border border-gray-800 outline-none text-sm text-white mb-4">
                <div class="space-y-4">
                    <input name="q{{i}}_s" value="{{ ep.links[i-1].stream if ep else '' }}" placeholder="Stream Link" class="w-full bg-black/40 p-3 rounded-xl text-xs border border-gray-800 outline-none text-white">
                    <input name="q{{i}}_d" value="{{ ep.links[i-1].download if ep else '' }}" placeholder="Download Link" class="w-full bg-black/40 p-3 rounded-xl text-xs border border-gray-800 outline-none text-white">
                    <input name="q{{i}}_t" value="{{ ep.links[i-1].telegram if ep else '' }}" placeholder="Telegram Link" class="w-full bg-black/40 p-3 rounded-xl text-xs border border-gray-800 outline-none text-white">
                </div>
            </div>
            {% endfor %}
            <button class="w-full bg-blue-600 p-5 rounded-3xl font-black shadow-2xl uppercase tracking-widest transition transform hover:scale-105">SAVE EPISODE</button>
        </form>
    </body>
    </html>
    """, mid=mid, ep=ep, idx=idx)

@app.route('/admin/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        settings_col.update_one({"type": "config"}, {"$set": {"api": request.form['api'], "limit": request.form['limit'], "slider_limit": request.form['slider_limit']}}, upsert=True)
        settings_col.update_one({"type": "ads"}, {"$set": {"top": request.form['top'], "bottom": request.form['bottom'], "popup": request.form['popup']}}, upsert=True)
        return redirect('/admin')
    cfg = settings_col.find_one({"type": "config"}) or {}
    ads = settings_col.find_one({"type": "ads"}) or {}
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>"""+HEAD_HTML+"""</head>
    <body class="p-6">
        <form method="POST" class="max-w-4xl mx-auto glass p-12 rounded-[3.5rem] space-y-10 border border-white/5 shadow-2xl">
            <h2 class="text-3xl font-black italic text-blue-500 uppercase tracking-tighter">Site Settings</h2>
            <div class="grid md:grid-cols-3 gap-6">
                <div class="md:col-span-2">
                    <label class="text-[10px] font-black text-gray-500 uppercase ml-2 tracking-widest">Shortener API (use {{url}})</label>
                    <input name="api" value="{{ cfg.api or '' }}" placeholder="https://api.com/st?api=KEY&url={{url}}" class="w-full bg-black/40 p-4 rounded-2xl border border-gray-800 mt-2 outline-none text-white shadow-inner">
                </div>
                <div>
                    <label class="text-[10px] font-black text-gray-500 uppercase ml-2 tracking-widest">Page Limit</label>
                    <input name="limit" type="number" value="{{ cfg.limit or 15 }}" class="w-full bg-black/40 p-4 rounded-2xl border border-gray-800 mt-2 outline-none text-white shadow-inner">
                </div>
                <div class="md:col-span-3">
                    <label class="text-[10px] font-black text-gray-500 uppercase ml-2 tracking-widest">Slider Limit</label>
                    <input name="slider_limit" type="number" value="{{ cfg.slider_limit or 5 }}" class="w-full bg-black/40 p-4 rounded-2xl border border-gray-800 mt-2 outline-none text-white shadow-inner">
                </div>
            </div>
            <div class="grid md:grid-cols-2 gap-8">
                <div class="col-span-2 md:col-span-1">
                    <label class="text-[10px] font-black text-yellow-500 uppercase ml-2 italic">Top Ad Code</label>
                    <textarea name="top" class="w-full bg-black/40 p-5 rounded-2xl h-40 border border-gray-800 mt-2 text-[10px] font-mono text-white">{{ ads.top or '' }}</textarea>
                </div>
                <div class="col-span-2 md:col-span-1">
                    <label class="text-[10px] font-black text-yellow-500 uppercase ml-2 italic">Bottom Ad Code</label>
                    <textarea name="bottom" class="w-full bg-black/40 p-5 rounded-2xl h-40 border border-gray-800 mt-2 text-[10px] font-mono text-white">{{ ads.bottom or '' }}</textarea>
                </div>
                <div class="col-span-2">
                    <label class="text-[10px] font-black text-red-500 uppercase ml-2 italic">Popup JS Code</label>
                    <textarea name="popup" class="w-full bg-black/40 p-5 rounded-2xl h-32 border border-gray-800 mt-2 text-[10px] font-mono text-white">{{ ads.popup or '' }}</textarea>
                </div>
            </div>
            <button class="w-full bg-blue-600 p-6 rounded-3xl font-black shadow-2xl uppercase tracking-widest transition transform hover:scale-105">SAVE CONFIGURATION</button>
        </form>
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
    return redirect(url_for('episode_list', mid=mid))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
