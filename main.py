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

# --- Helper Functions ---

def shorten_link(url):
    """যেকোনো লিঙ্ক শর্টনার API সাপোর্ট করবে"""
    if not url or not url.strip(): return ""
    try:
        cfg = settings_col.find_one({"type": "config"})
        if cfg and cfg.get('api'):
            api_url = cfg.get('api').replace("{url}", url)
            r = requests.get(api_url, timeout=5)
            if r.status_code == 200:
                return r.text.strip()
    except Exception as e:
        print(f"Shortener Error: {e}")
    return url

def get_site_settings():
    """কনফিগারেশন এবং অ্যাড লোড করা"""
    cfg = settings_col.find_one({"type": "config"}) or {
        "limit": 15, 
        "slider_limit": 5, 
        "api": "",
        "site_name": "MoviePro"
    }
    ads = list(settings_col.find({"type": "ad_unit"}))
    return cfg, ads

# --- HTML TEMPLATES (Separated to avoid 500 Error) ---

# Common Header/Styles
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
    .swiper { width: 100%; height: 400px; border-radius: 24px; margin-bottom: 30px; }
    .swiper-slide img { width: 100%; height: 100%; object-fit: cover; }
    .movie-card:hover img { transform: scale(1.1); transition: 0.6s cubic-bezier(0.4, 0, 0.2, 1); }
    ::-webkit-scrollbar { display: none; }
</style>
"""

# Navbar
NAVBAR_HTML = """
<nav class="p-4 glass sticky top-0 z-50 border-b border-white/5">
    <div class="max-w-7xl mx-auto flex justify-between items-center px-4">
        <a href="/" class="text-3xl font-black text-blue-500 uppercase italic tracking-tighter">
            {{ cfg.site_name }}<span class="text-white">PRO</span>
        </a>
        <div class="flex items-center gap-6">
            <form action="/" class="hidden md:flex bg-gray-950/50 border border-gray-800 rounded-full px-4 py-1">
                <input name="q" placeholder="Search movies..." class="bg-transparent outline-none text-sm p-1 w-48">
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
    cfg, ads = get_site_settings()
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
    <html lang="en">
    <head>""" + COMMON_HEAD + """<title>{{ cfg.site_name }} - Home</title></head>
    <body>
        """ + NAVBAR_HTML + """
        <div class="max-w-7xl mx-auto p-4 md:p-6">
            <!-- Header Ads -->
            <div class="mb-8 space-y-4 text-center">
                {% for ad in ads %}{% if ad.position == 'top' %}{{ ad.code | safe }}{% endif %}{% endfor %}
            </div>

            {% if slider_movies %}
            <div class="swiper mySwiper shadow-2xl border border-white/5">
                <div class="swiper-wrapper">
                    {% for sm in slider_movies %}
                    <div class="swiper-slide relative">
                        <img src="{{ sm.poster }}" alt="{{ sm.name }}">
                        <div class="absolute inset-0 bg-gradient-to-t from-black via-black/20 to-transparent flex flex-col justify-end p-8 md:p-16">
                            <span class="bg-blue-600 w-max px-3 py-1 rounded text-[10px] font-bold uppercase mb-3 tracking-widest">Featured</span>
                            <h2 class="text-4xl md:text-6xl font-black italic uppercase tracking-tighter leading-tight">{{ sm.name }}</h2>
                            <div class="flex gap-4 mt-6">
                                <a href="/movie/{{ sm._id }}" class="bg-white text-black px-10 py-3 rounded-full font-black text-sm hover:bg-blue-500 hover:text-white transition uppercase">Watch Now</a>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
                <div class="swiper-pagination"></div>
            </div>
            {% endif %}

            <div class="flex gap-3 overflow-x-auto pb-8 no-scrollbar">
                <a href="/" class="bg-blue-600 px-8 py-2.5 rounded-full text-xs font-black uppercase tracking-widest">All</a>
                {% for c in categories %}
                <a href="/?cat={{ c }}" class="glass border border-white/10 hover:border-blue-500/50 px-8 py-2.5 rounded-full text-xs font-black uppercase tracking-widest transition shrink-0 italic">{{ c }}</a>
                {% endfor %}
            </div>

            <h2 class="text-2xl font-black mb-8 italic text-blue-500 border-l-8 border-blue-600 pl-4 uppercase tracking-tighter">Latest Releases</h2>
            <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-6 md:gap-10">
                {% for m in movies %}
                <a href="/movie/{{ m._id }}" class="group relative rounded-3xl overflow-hidden aspect-[2/3] border border-white/5 bg-gray-900 block movie-card shadow-xl">
                    <span class="corner-tag top-3 left-3 bg-blue-600 shadow-lg">{{ m.tag1 }}</span>
                    <span class="corner-tag top-3 right-3 bg-red-600 shadow-lg">{{ m.tag2 }}</span>
                    <span class="corner-tag bottom-3 left-3 bg-yellow-500 text-black shadow-lg">{{ m.tag3 }}</span>
                    <span class="corner-tag bottom-3 right-3 bg-green-600 shadow-lg">{{ m.tag4 }}</span>
                    
                    <img src="{{ m.poster }}" class="w-full h-full object-cover">
                    
                    <div class="absolute inset-0 bg-gradient-to-t from-black via-transparent p-5 flex flex-col justify-end">
                        <div class="font-black text-sm md:text-base leading-tight">{{ m.name }}</div>
                        <div class="text-[10px] text-gray-400 mt-2 font-bold uppercase tracking-widest">{{ m.year }} | {{ m.lang }}</div>
                    </div>
                </a>
                {% endfor %}
            </div>

            <!-- Footer Ads -->
            <div class="mt-20 space-y-6 text-center">
                {% for ad in ads %}{% if ad.position == 'bottom' %}{{ ad.code | safe }}{% endif %}{% endfor %}
            </div>
        </div>

        {% for ad in ads %}{% if ad.position == 'popup' %}{{ ad.code | safe }}{% endif %}{% endfor %}

        <script>
            new Swiper(".mySwiper", { 
                pagination: { el: ".swiper-pagination", clickable: true }, 
                autoplay: { delay: 5000 }, 
                loop: true,
                effect: 'fade',
                fadeEffect: { crossFade: true }
            });
        </script>
    </body>
    </html>
    """, cfg=cfg, ads=ads, movies=movies, slider_movies=slider_movies, categories=categories)

@app.route('/movie/<id>')
def movie_details(id):
    try:
        movie = movies_col.find_one({"_id": ObjectId(id)})
        cfg, ads = get_site_settings()
    except: return redirect('/')
    
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>""" + COMMON_HEAD + """<title>{{ movie.name }} - Watch Online</title></head>
    <body class="p-4 md:p-10">
        <div class="max-w-6xl mx-auto">
            <a href="/" class="inline-flex items-center gap-2 text-gray-500 hover:text-white mb-10 font-bold transition">
                <i class="fa fa-arrow-left"></i> Back to Home
            </a>
            
            <div class="md:flex gap-12 glass p-8 md:p-12 rounded-[3rem] border border-white/10 shadow-2xl relative overflow-hidden">
                <div class="absolute top-0 right-0 p-20 bg-blue-600/5 rounded-full -mr-20 -mt-20 blur-3xl"></div>
                <img src="{{ movie.poster }}" class="w-full md:w-80 rounded-[2rem] shadow-2xl mb-8 md:mb-0 border border-white/10 relative z-10">
                <div class="flex-grow relative z-10">
                    <h1 class="text-4xl md:text-6xl font-black mb-6 tracking-tighter uppercase italic leading-tight">{{ movie.name }}</h1>
                    <div class="flex flex-wrap gap-4 mb-8">
                        <span class="bg-blue-600 text-white px-5 py-1.5 rounded-full text-xs font-black uppercase italic tracking-widest">{{ movie.category }}</span>
                        <span class="bg-gray-800 text-gray-400 px-5 py-1.5 rounded-full text-xs font-black tracking-widest">{{ movie.year }}</span>
                        <span class="bg-gray-800 text-gray-400 px-5 py-1.5 rounded-full text-xs font-black tracking-widest">{{ movie.lang }}</span>
                    </div>
                    <div class="bg-black/40 p-8 rounded-3xl border border-white/5 shadow-inner">
                        <h3 class="text-[11px] font-black text-blue-500 uppercase mb-4 tracking-[0.3em] italic">The Storyline</h3>
                        <p class="text-gray-400 leading-relaxed text-sm md:text-base italic font-medium">"{{ movie.story }}"</p>
                    </div>
                </div>
            </div>

            <!-- Ad Units -->
            <div class="my-16 space-y-6 text-center">
                {% for ad in ads %}{% if ad.position == 'top' %}{{ ad.code | safe }}{% endif %}{% endfor %}
            </div>

            <h2 class="text-3xl font-black mt-20 mb-12 italic flex items-center gap-6 text-blue-500 uppercase tracking-tighter">
                <span class="w-16 h-1.5 bg-blue-600 rounded-full shadow-lg shadow-blue-600/50"></span> Download & Watch
            </h2>
            
            <div class="grid gap-10">
                {% for ep in movie.episodes %}
                <div class="glass p-8 md:p-12 rounded-[3.5rem] border-l-[12px] border-blue-600 shadow-2xl relative group">
                    <div class="flex justify-between items-center mb-8">
                        <h3 class="font-black text-2xl md:text-3xl italic text-white uppercase tracking-tighter group-hover:text-blue-400 transition">Episode: {{ ep.ep_no }}</h3>
                        <div class="h-px flex-grow mx-8 bg-white/5"></div>
                    </div>
                    
                    <div class="grid md:grid-cols-2 gap-8">
                        {% for link in ep.links %}
                        <div class="bg-black/60 p-6 rounded-3xl border border-white/5 hover:border-blue-500/30 transition shadow-inner">
                            <span class="text-[11px] uppercase text-gray-500 block mb-5 font-black tracking-[0.2em] italic">Server Quality: {{ link.quality }}</span>
                            <div class="flex flex-wrap gap-4">
                                <a href="{{ link.stream }}" target="_blank" class="flex-grow bg-blue-600 hover:bg-blue-700 py-4 rounded-2xl text-xs font-black text-center shadow-xl transition uppercase tracking-widest italic">Stream Online</a>
                                <a href="{{ link.download }}" target="_blank" class="flex-grow bg-green-600 hover:bg-green-700 py-4 rounded-2xl text-xs font-black text-center text-white transition uppercase tracking-widest italic">Direct Download</a>
                                <a href="{{ link.telegram }}" target="_blank" class="bg-sky-500 hover:bg-sky-600 px-8 py-4 rounded-2xl text-xs text-center transition"><i class="fab fa-telegram text-lg"></i></a>
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                </div>
                {% endfor %}
            </div>

            <div class="my-20 space-y-6 text-center">
                {% for ad in ads %}{% if ad.position == 'bottom' %}{{ ad.code | safe }}{% endif %}{% endfor %}
            </div>
        </div>
        {% for ad in ads %}{% if ad.position == 'popup' %}{{ ad.code | safe }}{% endif %}{% endfor %}
    </body>
    </html>
    """, movie=movie, cfg=cfg, ads=ads)

# --- ADMIN ROUTES ---

@app.route('/admin')
def admin_dash():
    q = request.args.get('q')
    filter_q = {"name": {"$regex": q, "$options": "i"}} if q else {}
    movies = list(movies_col.find(filter_q).sort("_id", -1))
    cfg, _ = get_site_settings()
    
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>""" + COMMON_HEAD + """<title>Admin Panel</title></head>
    <body class="p-6">
        <div class="max-w-6xl mx-auto">
            <div class="flex flex-col md:flex-row justify-between items-center mb-16 gap-8">
                <div class="flex items-center gap-4">
                    <div class="w-12 h-12 bg-blue-600 rounded-2xl flex items-center justify-center shadow-lg"><i class="fa fa-user-shield text-xl"></i></div>
                    <h1 class="text-3xl font-black italic text-white uppercase tracking-tighter">Control Center</h1>
                </div>
                <div class="flex gap-4 w-full md:w-auto">
                    <form action="/admin" class="flex flex-grow bg-gray-950 border border-gray-800 rounded-2xl overflow-hidden shadow-inner">
                        <input name="q" placeholder="Search database..." class="bg-transparent p-3 px-6 outline-none text-sm w-full text-white">
                        <button class="px-6 text-blue-500 hover:bg-blue-600/10 transition"><i class="fa fa-search"></i></button>
                    </form>
                    <a href="/admin/add" class="bg-green-600 hover:bg-green-700 p-4 px-8 rounded-2xl font-black text-xs uppercase shadow-xl transition">+ Add</a>
                    <a href="/admin/settings" class="bg-gray-800 hover:bg-gray-700 p-4 px-6 rounded-2xl font-black text-xs uppercase transition"><i class="fa fa-cog"></i></a>
                </div>
            </div>

            <div class="grid gap-6">
                {% for m in movies %}
                <div class="glass p-5 rounded-3xl flex justify-between items-center border border-white/5 hover:border-blue-500/20 transition shadow-xl group">
                    <div class="flex items-center gap-6">
                        <img src="{{ m.poster }}" class="w-16 h-20 object-cover rounded-xl shadow-lg border border-white/10 group-hover:scale-105 transition">
                        <div>
                            <h3 class="font-black text-lg group-hover:text-blue-400 transition">{{ m.name }}</h3>
                            <div class="flex gap-3 mt-2">
                                <span class="text-[10px] font-black text-gray-500 uppercase tracking-widest">{{ m.category }}</span>
                                <span class="text-[10px] font-black text-gray-500 uppercase tracking-widest">{{ m.year }}</span>
                            </div>
                        </div>
                    </div>
                    <div class="flex gap-3">
                        <a href="/admin/edit/{{ m._id }}" class="p-4 bg-yellow-500/10 text-yellow-500 rounded-2xl hover:bg-yellow-500 hover:text-white transition font-black text-xs uppercase">Edit</a>
                        <a href="/admin/delete/{{ m._id }}" class="p-4 bg-red-500/10 text-red-500 rounded-2xl hover:bg-red-500 hover:text-white transition" onclick="return confirm('Delete permanently?')"><i class="fa fa-trash"></i></a>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
    </body>
    </html>
    """, movies=movies, cfg=cfg)

@app.route('/admin/add', methods=['GET', 'POST'])
@app.route('/admin/edit/<id>', methods=['GET', 'POST'])
def manage_movie(id=None):
    movie = movies_col.find_one({"_id": ObjectId(id)}) if id else None
    cfg, _ = get_site_settings()
    
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

    # ইপিসোড ডাটা যদি এডিট মোড হয়
    ep_to_edit = None
    ep_idx = request.args.get('ep_idx')
    if ep_idx is not None and movie and 'episodes' in movie:
        try: ep_to_edit = movie['episodes'][int(ep_idx)]
        except: pass

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>""" + COMMON_HEAD + """</head>
    <body class="p-6">
        <div class="max-w-7xl mx-auto grid lg:grid-cols-2 gap-12">
            <!-- Movie Form -->
            <form method="POST" class="glass p-10 rounded-[3rem] border border-white/10 h-max shadow-2xl relative overflow-hidden">
                <div class="absolute top-0 left-0 w-2 h-full bg-blue-600"></div>
                <h2 class="text-3xl font-black mb-10 italic text-blue-500 uppercase tracking-tighter">Movie Setup</h2>
                <div class="space-y-6">
                    <div class="grid gap-2">
                        <label class="text-[10px] font-black text-gray-500 uppercase tracking-widest ml-1">Title</label>
                        <input name="name" value="{{ movie.name if movie else '' }}" class="w-full bg-black/40 p-4 rounded-2xl border border-gray-800 outline-none text-white focus:border-blue-500 transition" required>
                    </div>
                    <div class="grid gap-2">
                        <label class="text-[10px] font-black text-gray-500 uppercase tracking-widest ml-1">Poster Image URL</label>
                        <input name="poster" value="{{ movie.poster if movie else '' }}" class="w-full bg-black/40 p-4 rounded-2xl border border-gray-800 outline-none text-white focus:border-blue-500 transition">
                    </div>
                    <div class="grid grid-cols-2 gap-6">
                        <div class="grid gap-2">
                            <label class="text-[10px] font-black text-gray-500 uppercase tracking-widest ml-1">Category</label>
                            <input name="category" value="{{ movie.category if movie else '' }}" placeholder="ACTION" class="bg-black/40 p-4 rounded-2xl border border-gray-800 outline-none">
                        </div>
                        <div class="grid gap-2">
                            <label class="text-[10px] font-black text-gray-500 uppercase tracking-widest ml-1">Year</label>
                            <input name="year" value="{{ movie.year if movie else '' }}" placeholder="2025" class="bg-black/40 p-4 rounded-2xl border border-gray-800 outline-none">
                        </div>
                    </div>
                    <div class="grid gap-2">
                        <label class="text-[10px] font-black text-gray-500 uppercase tracking-widest ml-1">Language</label>
                        <input name="lang" value="{{ movie.lang if movie else '' }}" placeholder="Hindi / Bangla" class="w-full bg-black/40 p-4 rounded-2xl border border-gray-800 outline-none">
                    </div>
                    <div class="grid grid-cols-4 gap-3">
                        {% for i in range(1, 5) %}
                        <input name="tag{{i}}" value="{{ movie['tag'~i] if movie else '' }}" placeholder="Tag {{i}}" class="bg-black/40 p-3 rounded-xl border border-gray-800 text-[10px] outline-none focus:border-blue-500">
                        {% endfor %}
                    </div>
                    <div class="grid gap-2">
                        <label class="text-[10px] font-black text-gray-500 uppercase tracking-widest ml-1">Storyline</label>
                        <textarea name="story" class="w-full bg-black/40 p-6 rounded-3xl h-40 border border-gray-800 outline-none text-sm leading-relaxed italic">{{ movie.story if movie else '' }}</textarea>
                    </div>
                    <label class="flex items-center gap-3 text-xs font-black text-blue-400 uppercase tracking-widest cursor-pointer bg-blue-600/5 p-4 rounded-2xl border border-blue-500/20">
                        <input type="checkbox" name="in_slider" {{ 'checked' if movie and movie.in_slider == 'on' else '' }} class="w-5 h-5 rounded-lg"> Show in Home Slider
                    </label>
                </div>
                <button name="save_movie" class="w-full bg-blue-600 hover:bg-blue-700 py-5 rounded-[2rem] font-black mt-10 shadow-2xl shadow-blue-600/30 uppercase tracking-[0.2em] transition transform hover:scale-[1.02]">Save & Update</button>
            </form>

            <!-- Episode Section -->
            {% if movie %}
            <div class="space-y-10">
                <form action="/admin/episode/save" method="POST" class="glass p-10 rounded-[3rem] border border-blue-500/20 shadow-2xl relative">
                    <div class="absolute top-0 left-0 w-2 h-full bg-green-600"></div>
                    <h2 class="text-2xl font-black mb-8 italic text-green-500 uppercase tracking-tighter">{{ 'Edit' if ep_to_edit else 'Add New' }} Episode</h2>
                    <input type="hidden" name="mid" value="{{ movie._id }}">
                    <input type="hidden" name="idx" value="{{ ep_idx if ep_idx is not None else '' }}">
                    
                    <div class="grid gap-2 mb-8">
                        <label class="text-[10px] font-black text-gray-500 uppercase tracking-widest ml-1">Episode Number</label>
                        <input name="ep_no" value="{{ ep_to_edit.ep_no if ep_to_edit else '' }}" placeholder="01" class="w-full bg-black/60 p-5 rounded-2xl border border-blue-500/30 outline-none font-black italic shadow-inner" required>
                    </div>
                    
                    {% for i in [1, 2] %}
                    <div class="bg-black/40 p-8 rounded-[2.5rem] border border-gray-800 mb-6 space-y-4 shadow-inner">
                        <h3 class="text-blue-500 font-black text-[10px] uppercase italic tracking-[0.3em] mb-6 opacity-60">Link Slot {{ i }}</h3>
                        <input name="q{{i}}_n" value="{{ ep_to_edit.links[i-1].quality if ep_to_edit else '' }}" placeholder="720p WEB-DL" class="w-full bg-black/40 p-3 rounded-xl border border-gray-700 outline-none text-xs">
                        <div class="grid gap-3">
                            <input name="q{{i}}_s" value="{{ ep_to_edit.links[i-1].stream if ep_to_edit else '' }}" placeholder="Streaming Link" class="w-full bg-black/40 p-3 rounded-xl border border-gray-700 outline-none text-[10px] font-mono">
                            <input name="q{{i}}_d" value="{{ ep_to_edit.links[i-1].download if ep_to_edit else '' }}" placeholder="Download Link" class="w-full bg-black/40 p-3 rounded-xl border border-gray-700 outline-none text-[10px] font-mono">
                            <input name="q{{i}}_t" value="{{ ep_to_edit.links[i-1].telegram if ep_to_edit else '' }}" placeholder="Telegram Link" class="w-full bg-black/40 p-3 rounded-xl border border-gray-700 outline-none text-[10px] font-mono">
                        </div>
                    </div>
                    {% endfor %}
                    
                    <button class="w-full bg-green-600 hover:bg-green-700 py-5 rounded-[2rem] font-black uppercase tracking-[0.2em] shadow-xl transition transform hover:scale-[1.02]">{{ 'Update' if ep_to_edit else 'Upload' }} Episode</button>
                    {% if ep_to_edit %}<a href="/admin/edit/{{ movie._id }}" class="block text-center mt-5 text-xs text-gray-500 underline font-black uppercase">Cancel Edit</a>{% endif %}
                </form>

                <div class="glass p-8 rounded-[3rem] border border-white/5 shadow-2xl">
                    <h3 class="font-black text-sm uppercase text-gray-500 mb-8 italic tracking-widest border-b border-white/5 pb-4">Episode Database</h3>
                    <div class="space-y-4">
                        {% for ep in movie.episodes %}
                        <div class="bg-gray-950 p-5 rounded-2xl flex justify-between items-center border border-gray-800 group hover:border-blue-500/50 transition">
                            <span class="font-black italic text-sm tracking-widest text-blue-400">EPISODE {{ ep.ep_no }}</span>
                            <div class="flex gap-6 font-black uppercase text-[10px] tracking-widest">
                                <a href="/admin/edit/{{ movie._id }}?ep_idx={{ loop.index0 }}" class="text-yellow-500 hover:text-white transition">Edit</a>
                                <a href="/admin/episode/delete/{{ movie._id }}/{{ loop.index0 }}" class="text-red-500 hover:text-white transition" onclick="return confirm('Delete permanently?')">Delete</a>
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                </div>
            </div>
            {% else %}
            <div class="glass p-20 rounded-[3rem] border-4 border-dashed border-gray-800 flex flex-col items-center justify-center text-gray-700 font-black italic">
                <i class="fa fa-lock text-4xl mb-4 opacity-20"></i>
                <p class="uppercase tracking-widest text-center">Save movie first to enable episodes</p>
            </div>
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
    return redirect(url_for('manage_movie', id=mid))

@app.route('/admin/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        if 'save_config' in request.form:
            settings_col.update_one({"type": "config"}, {"$set": {
                "api": request.form['api'], 
                "limit": request.form['limit'], 
                "slider_limit": request.form['slider_limit'],
                "site_name": request.form.get('site_name', 'MoviePro')
            }}, upsert=True)
        elif 'add_ad' in request.form:
            settings_col.insert_one({"type": "ad_unit", "position": request.form['pos'], "code": request.form['code']})
        elif 'del_ad' in request.form:
            settings_col.delete_one({"_id": ObjectId(request.form['ad_id'])})
        return redirect('/admin/settings')
    
    cfg, ads = get_site_settings()
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>""" + COMMON_HEAD + """<title>Settings Center</title></head>
    <body class="p-6">
        <div class="max-w-6xl mx-auto grid md:grid-cols-2 gap-12">
            <!-- Site Global Config -->
            <form method="POST" class="glass p-10 rounded-[3rem] border border-white/5 h-max shadow-2xl">
                <h2 class="text-3xl font-black mb-10 italic text-blue-500 uppercase tracking-tighter italic">Global Config</h2>
                <div class="space-y-8">
                    <div class="grid gap-2">
                        <label class="text-[10px] font-black text-gray-500 uppercase tracking-widest ml-1">Site Brand Name</label>
                        <input name="site_name" value="{{ cfg.site_name or 'MoviePro' }}" class="w-full bg-black/40 p-4 rounded-2xl border border-gray-800 outline-none font-bold text-white shadow-inner">
                    </div>
                    <div class="grid gap-2">
                        <label class="text-[10px] font-black text-gray-500 uppercase tracking-widest ml-1 italic">Link Shortener API (use {url})</label>
                        <input name="api" value="{{ cfg.api or '' }}" placeholder="https://api.com/st?api=KEY&url={url}" class="w-full bg-black/40 p-4 rounded-2xl border border-gray-800 outline-none text-xs font-mono text-blue-400">
                    </div>
                    <div class="grid grid-cols-2 gap-6">
                        <div class="grid gap-2">
                            <label class="text-[10px] font-black text-gray-500 uppercase tracking-widest ml-1">Page Limit</label>
                            <input name="limit" type="number" value="{{ cfg.limit or 15 }}" class="bg-black/40 p-4 rounded-2xl border border-gray-800 outline-none font-black text-white">
                        </div>
                        <div class="grid gap-2">
                            <label class="text-[10px] font-black text-gray-500 uppercase tracking-widest ml-1">Slider Limit</label>
                            <input name="slider_limit" type="number" value="{{ cfg.slider_limit or 5 }}" class="bg-black/40 p-4 rounded-2xl border border-gray-800 outline-none font-black text-white">
                        </div>
                    </div>
                    <button name="save_config" class="w-full bg-blue-600 hover:bg-blue-700 py-5 rounded-[2rem] font-black uppercase tracking-[0.2em] shadow-2xl shadow-blue-600/30 transition transform hover:scale-105">Apply Changes</button>
                </div>
            </form>

            <!-- Multi-Ad Unit Management -->
            <div class="space-y-10">
                <form method="POST" class="glass p-10 rounded-[3rem] border border-yellow-500/20 shadow-2xl">
                    <h2 class="text-3xl font-black mb-8 italic text-yellow-500 uppercase tracking-tighter">New Ad Slot</h2>
                    <select name="pos" class="w-full bg-black/60 p-5 rounded-2xl border border-gray-800 outline-none mb-6 text-xs font-black uppercase tracking-widest shadow-inner">
                        <option value="top">Header / Top Banner</option>
                        <option value="bottom">Footer / Bottom Banner</option>
                        <option value="popup">Direct Link / Popup Script</option>
                    </select>
                    <textarea name="code" placeholder="Paste Ad HTML / JS Script here..." class="w-full bg-black/40 p-6 rounded-3xl h-44 border border-gray-800 outline-none text-[10px] mb-8 font-mono text-white"></textarea>
                    <button name="add_ad" class="w-full bg-yellow-600 hover:bg-yellow-700 py-5 rounded-[2rem] font-black uppercase tracking-[0.2em] shadow-2xl shadow-yellow-600/30 transition transform hover:scale-105">Deploy Ad Unit</button>
                </form>

                <div class="glass p-8 rounded-[3rem] border border-white/5 space-y-6 shadow-2xl">
                    <h3 class="font-black text-xs uppercase text-gray-500 mb-6 italic tracking-[0.3em] border-b border-white/5 pb-4">Active Ad Inventory</h3>
                    {% if ads %}
                    {% for ad in ads %}
                    <div class="bg-gray-950 p-5 rounded-2xl flex justify-between items-center border border-gray-800 shadow-md">
                        <div>
                            <span class="bg-blue-600/20 text-blue-400 px-3 py-1 rounded text-[9px] font-black uppercase tracking-widest italic">{{ ad.position }}</span>
                            <p class="text-[8px] text-gray-700 mt-2 font-mono truncate w-40 tracking-tighter">{{ ad.code[:60] }}</p>
                        </div>
                        <form method="POST"><input type="hidden" name="ad_id" value="{{ ad._id }}"><button name="del_ad" class="text-red-500 hover:text-white font-black text-[10px] uppercase tracking-widest italic transition">Remove</button></form>
                    </div>
                    {% endfor %}
                    {% else %}
                    <p class="text-[10px] text-gray-600 text-center italic font-bold">Your ad database is currently empty.</p>
                    {% endif %}
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
    if movie and 'episodes' in movie:
        movie['episodes'].pop(idx)
        movies_col.update_one({"_id": ObjectId(mid)}, {"$set": {"episodes": movie['episodes']}})
    return redirect(url_for('manage_movie', id=mid))

if __name__ == '__main__':
    # লোকাল রান করার জন্য
    app.run(debug=True)
