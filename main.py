import os
import requests
import certifi
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# --- CONFIGURATION & SECURITY ---
app.secret_key = os.environ.get("SESSION_SECRET", "ultimate_secure_key_2024_v10")
RECOVERY_KEY = os.environ.get("RECOVERY_KEY", "admin@2024")

# --- MONGODB CONNECTION ---
try:
    ca = certifi.where()
    # আপনার দেওয়া কানেকশন স্ট্রিং
    MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    client = MongoClient(MONGO_URI, tlsCAFile=ca, serverSelectionTimeoutMS=5000)
    db = client['app_hub_production_ultimate_system']
    apps_col = db['apps']
    users_col = db['users']
    ads_col = db['ads']
    settings_col = db['settings']
    categories_col = db['categories']
    media_col = db['media']
except Exception as e:
    print(f"DATABASE CONNECTION ERROR: {e}")

# --- HELPERS ---
def get_site_info():
    info = settings_col.find_one({"type": "site_info"})
    if not info:
        return {
            "name": "APPHUB PRO", 
            "title": "Ultimate App Store", 
            "logo": "https://cdn-icons-png.flaticon.com/512/2589/2589127.png",
            "desc": "Premium platform for high-performance applications and tools.",
            "copyright": "2024 APPHUB PRO - All Rights Reserved",
            "fb": "#", "tw": "#", "ig": "#"
        }
    return info

def get_shortener():
    return settings_col.find_one({"type": "shortener"}) or {"url": "", "api": ""}

# --- CSS & UI COMPONENTS ---
BASE_CSS = """
<script src="https://cdn.tailwindcss.com"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;700;800&display=swap');
    body { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #f8fafc; color: #0f172a; scroll-behavior: smooth; }
    .glass-nav { background: rgba(255, 255, 255, 0.9); backdrop-filter: blur(10px); border-bottom: 1px solid #e2e8f0; }
    .pro-card { background: white; border: 1px solid #f1f5f9; border-radius: 1.5rem; transition: 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
    .pro-card:hover { transform: translateY(-5px); box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1); border-color: #6366f1; }
    .sidebar-link { display: flex; align-items: center; gap: 12px; padding: 12px 20px; border-radius: 12px; font-weight: 600; color: #94a3b8; transition: 0.3s; }
    .sidebar-active { background: #6366f1 !important; color: white !important; box-shadow: 0 10px 15px -3px rgba(99, 102, 241, 0.3); }
    input, textarea, select { border: 2px solid #f1f5f9; border-radius: 12px; padding: 12px 16px; outline: none; width: 100%; transition: 0.3s; }
    input:focus { border-color: #6366f1; }
    .btn-main { background: #6366f1; color: white; padding: 12px 24px; border-radius: 12px; font-weight: 700; display: inline-block; text-align: center; cursor: pointer; }
    .media-banner { width: 100%; height: 200px; object-fit: cover; border-radius: 1.5rem; }
    .line-clamp-1 { display: -webkit-box; -webkit-line-clamp: 1; -webkit-box-orient: vertical; overflow: hidden; }
</style>
"""

BASE_LAYOUT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ site.name }} - {{ site.title }}</title>
    """ + BASE_CSS + """
</head>
<body>
    {% if not is_admin_route %}
    <nav class="glass-nav sticky top-0 z-50 py-4">
        <div class="container mx-auto px-6 flex flex-col lg:flex-row items-center justify-between gap-4">
            <a href="/" class="flex items-center gap-3">
                <img src="{{ site.logo }}" class="w-10 h-10 rounded-xl">
                <span class="text-2xl font-black text-slate-900 tracking-tighter uppercase">{{ site.name }}</span>
            </a>
            <form action="/" method="GET" class="flex bg-slate-100 rounded-xl px-4 py-2 w-full max-w-md border border-slate-200">
                <input type="text" name="q" placeholder="Search for apps, games..." class="bg-transparent border-none p-0 w-full text-sm font-medium">
                <button type="submit"><i class="fas fa-search text-indigo-600"></i></button>
            </form>
        </div>
    </nav>
    {% endif %}

    <div class="{% if is_admin_route %}flex flex-col lg:flex-row min-h-screen{% else %}container mx-auto px-6 py-8{% endif %}">
        {% if is_admin_route %}
        <!-- ADMIN SIDEBAR -->
        <div class="w-full lg:w-72 bg-slate-950 text-slate-400 p-6 flex flex-col lg:h-screen lg:sticky lg:top-0">
            <div class="flex items-center gap-3 mb-10 border-b border-slate-900 pb-6">
                <img src="{{ site.logo }}" class="w-8 h-8 rounded-lg">
                <span class="text-white font-black uppercase italic">{{ site.name }}</span>
            </div>
            <div class="space-y-1 flex-1 overflow-y-auto">
                <a href="/admin/dashboard" class="sidebar-link {% if active == 'dashboard' %}sidebar-active{% endif %}"><i class="fas fa-chart-pie"></i> Dashboard</a>
                <a href="/admin/categories" class="sidebar-link {% if active == 'categories' %}sidebar-active{% endif %}"><i class="fas fa-tags"></i> Categories</a>
                <a href="/admin/apps" class="sidebar-link {% if active == 'apps' %}sidebar-active{% endif %}"><i class="fas fa-layer-group"></i> Apps Manager</a>
                <a href="/admin/media" class="sidebar-link {% if active == 'media' %}sidebar-active{% endif %}"><i class="fas fa-photo-video"></i> Media Center</a>
                <a href="/admin/ads" class="sidebar-link {% if active == 'ads' %}sidebar-active{% endif %}"><i class="fas fa-bullhorn"></i> Ads Manager</a>
                <a href="/admin/layout" class="sidebar-link {% if active == 'layout' %}sidebar-active{% endif %}"><i class="fas fa-swatchbook"></i> Site Layout</a>
                <a href="/admin/settings" class="sidebar-link {% if active == 'settings' %}sidebar-active{% endif %}"><i class="fas fa-cogs"></i> System Settings</a>
            </div>
            <div class="mt-6 pt-6 border-t border-slate-900">
                <a href="/" class="text-emerald-400 font-bold block mb-4"><i class="fas fa-external-link-alt"></i> VIEW SITE</a>
                <a href="/logout" class="text-red-500 font-bold"><i class="fas fa-power-off"></i> LOGOUT</a>
            </div>
        </div>
        <!-- ADMIN CONTENT -->
        <div class="flex-1 p-6 lg:p-12 bg-white">
            {% with messages = get_flashed_messages() %}{% if messages %}{% for m in messages %}
            <div class="bg-indigo-600 text-white p-4 rounded-xl mb-8 flex justify-between shadow-lg">
                <span><i class="fas fa-info-circle mr-2"></i> {{ m }}</span>
                <button onclick="this.parentElement.remove()"><i class="fas fa-times"></i></button>
            </div>
            {% endfor %}{% endif %}{% endwith %}
            {% block admin_content %}{% endblock %}
        </div>
        {% else %}
        <!-- USER CONTENT -->
        <div class="min-h-screen">
            {% block content %}{% endblock %}
        </div>
        {% endif %}
    </div>

    {% if not is_admin_route %}
    <footer class="bg-slate-950 text-slate-500 py-16 mt-12">
        <div class="container mx-auto px-6 grid grid-cols-1 md:grid-cols-3 gap-12">
            <div>
                <h3 class="text-white text-xl font-black mb-6 uppercase tracking-tighter">{{ site.name }}</h3>
                <p class="text-sm leading-relaxed">{{ site.desc }}</p>
            </div>
            <div>
                <h4 class="text-white font-bold mb-6 uppercase text-sm tracking-widest">Support</h4>
                <div class="flex flex-col gap-3 text-sm">
                    <a href="#" class="hover:text-white transition">Privacy Policy</a>
                    <a href="#" class="hover:text-white transition">Terms of Service</a>
                    <a href="#" class="hover:text-white transition">DMCA Notice</a>
                </div>
            </div>
            <div>
                <h4 class="text-white font-bold mb-6 uppercase text-sm tracking-widest">Connect</h4>
                <div class="flex gap-4">
                    <a href="{{ site.fb }}" class="w-10 h-10 bg-slate-900 rounded-full flex items-center justify-center hover:bg-indigo-600 transition"><i class="fab fa-facebook-f text-white"></i></a>
                    <a href="{{ site.ig }}" class="w-10 h-10 bg-slate-900 rounded-full flex items-center justify-center hover:bg-indigo-600 transition"><i class="fab fa-instagram text-white"></i></a>
                </div>
            </div>
        </div>
        <div class="container mx-auto px-6 border-t border-slate-900 mt-12 pt-8 text-center text-[11px] font-bold uppercase tracking-[0.2em]">
            &copy; {{ site.copyright }}
        </div>
    </footer>
    {% endif %}
</body>
</html>
"""

# --- PUBLIC ROUTES ---

@app.route('/')
def home():
    site = get_site_info()
    q = request.args.get('q', '')
    
    # মিডিয়া এবং ক্যাটাগরি ডেটা
    all_media = list(media_col.find().sort('_id', -1))
    all_categories = list(categories_col.find().sort('name', 1))
    
    if q:
        apps_found = list(apps_col.find({"name": {"$regex": q, "$options": "i"}}).sort('_id', -1))
        home_data = [{"cat_name": f"Search results for: {q}", "apps": apps_found}]
        all_media = [] # সার্চ দিলে মিডিয়া হাইড
    else:
        home_data = []
        for cat in all_categories:
            limit = int(cat.get('limit', 4))
            cat_apps = list(apps_col.find({"category": cat['name']}).sort('_id', -1).limit(limit))
            if cat_apps:
                home_data.append({"cat_name": cat['name'], "apps": cat_apps})

    content = """
    {% if all_media %}
    <div class="mb-12">
        <h2 class="text-xl font-black uppercase mb-6 flex items-center gap-2"><i class="fas fa-fire text-orange-500"></i> Featured Today</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {% for m in all_media %}
            <a href="{{ m.link }}" target="_blank" class="pro-card relative group overflow-hidden">
                <img src="{{ m.url }}" class="media-banner group-hover:scale-105 transition duration-700">
                <div class="absolute inset-0 bg-gradient-to-t from-black/90 via-transparent to-transparent flex flex-col justify-end p-6">
                    <h3 class="text-white font-black text-lg italic uppercase line-clamp-1">{{ m.title }}</h3>
                    <p class="text-white/60 text-xs font-bold uppercase">Explore Now <i class="fas fa-arrow-right ml-1"></i></p>
                </div>
            </a>
            {% endfor %}
        </div>
    </div>
    {% endif %}

    {% for section in home_data %}
    <div class="mb-16">
        <div class="flex justify-between items-end mb-8 border-b-2 border-slate-100 pb-4">
            <h2 class="text-2xl font-black uppercase italic tracking-tighter text-slate-800">{{ section.cat_name }}</h2>
            <a href="#" class="text-indigo-600 font-black text-xs uppercase tracking-widest">See All <i class="fas fa-chevron-right ml-1"></i></a>
        </div>
        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-6">
            {% for app in section.apps %}
            <a href="/app/{{app._id}}" class="pro-card p-6 flex flex-col items-center text-center group">
                <div class="relative mb-4">
                    <img src="{{app.logo}}" class="w-20 h-20 rounded-2xl shadow-xl group-hover:rotate-3 transition">
                    <span class="absolute -top-2 -right-2 bg-indigo-600 text-white text-[8px] font-black px-2 py-1 rounded-full uppercase">NEW</span>
                </div>
                <h3 class="font-black text-slate-800 text-sm mb-3 line-clamp-1 uppercase italic">{{app.name}}</h3>
                <div class="w-full bg-slate-100 group-hover:bg-indigo-600 group-hover:text-white text-slate-500 py-2.5 rounded-xl text-[9px] font-black uppercase transition">DOWNLOAD</div>
            </a>
            {% endfor %}
        </div>
    </div>
    {% endfor %}
    """
    return render_template_string(BASE_LAYOUT.replace('{% block content %}{% endblock %}', content), site=site, home_data=home_data, all_media=all_media, is_admin_route=False)

@app.route('/app/<id>')
def details(id):
    site = get_site_info()
    app_data = apps_col.find_one({"_id": ObjectId(id)})
    if not app_data: return redirect('/')
    content = """
    <div class="bg-white rounded-[2.5rem] p-8 lg:p-16 shadow-2xl border flex flex-col lg:flex-row gap-12 items-center lg:items-start">
        <img src="{{app.logo}}" class="w-56 h-56 rounded-[3rem] shadow-2xl border-8 border-slate-50">
        <div class="flex-1 text-center lg:text-left">
            <h1 class="text-4xl lg:text-6xl font-black mb-6 uppercase italic tracking-tighter text-slate-900">{{app.name}}</h1>
            <p class="text-slate-500 text-lg mb-8 leading-relaxed font-medium">"{{app.info}}"</p>
            <div class="flex flex-wrap justify-center lg:justify-start gap-4 mb-10">
                <div class="bg-indigo-50 border border-indigo-100 text-indigo-600 px-6 py-2 rounded-full font-black text-xs uppercase">{{app.category}}</div>
                <div class="bg-emerald-50 border border-emerald-100 text-emerald-600 px-6 py-2 rounded-full font-black text-xs uppercase italic">Version {{app.version}}</div>
                <div class="bg-slate-50 border border-slate-100 text-slate-600 px-6 py-2 rounded-full font-black text-xs uppercase">Verified Secure</div>
            </div>
            <a href="/get/{{app._id}}" class="bg-slate-950 text-white px-12 py-5 rounded-2xl font-black text-xl inline-block shadow-2xl hover:bg-indigo-600 transition transform hover:scale-105">FREE DOWNLOAD</a>
        </div>
    </div>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block content %}{% endblock %}', content), site=site, app=app_data, is_admin_route=False)

# --- DOWNLOAD PROCESS (SHORTENER) ---
@app.route('/get/<id>')
def download_process(id):
    app_data = apps_col.find_one({"_id": ObjectId(id)})
    if not app_data: return redirect('/')
    cfg = get_shortener()
    target = app_data['download_link']
    
    if cfg.get('url') and cfg.get('api'):
        try:
            api_endpoint = f"https://{cfg['url']}/api?api={cfg['api']}&url={target}"
            res = requests.get(api_endpoint, timeout=10).json()
            short_url = res.get('shortenedUrl') or res.get('shortedUrl')
            if short_url: return redirect(short_url)
        except Exception as e:
            print(f"Shortener API Error: {e}")
    
    return redirect(target)

# --- ADMIN ROUTES ---

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('logged_in'): return redirect('/admin-gate')
    site = get_site_info()
    stats = {
        "apps": apps_col.count_documents({}),
        "cats": categories_col.count_documents({}),
        "media": media_col.count_documents({}),
        "ads": ads_col.count_documents({})
    }
    content = """
    <h1 class="text-4xl font-black mb-10 uppercase italic">System Stats</h1>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div class="bg-indigo-600 p-8 rounded-3xl text-white shadow-lg">
            <div class="text-5xl font-black">{{ stats.apps }}</div><p class="font-bold uppercase opacity-60 text-xs">Total Apps</p>
        </div>
        <div class="bg-slate-900 p-8 rounded-3xl text-white shadow-lg">
            <div class="text-5xl font-black">{{ stats.cats }}</div><p class="font-bold uppercase opacity-60 text-xs">Categories</p>
        </div>
        <div class="bg-emerald-500 p-8 rounded-3xl text-white shadow-lg">
            <div class="text-5xl font-black">{{ stats.media }}</div><p class="font-bold uppercase opacity-60 text-xs">Media Items</p>
        </div>
        <div class="bg-orange-500 p-8 rounded-3xl text-white shadow-lg">
            <div class="text-5xl font-black">{{ stats.ads }}</div><p class="font-bold uppercase opacity-60 text-xs">Active Ads</p>
        </div>
    </div>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block admin_content %}{% endblock %}', content), site=site, stats=stats, is_admin_route=True, active="dashboard")

@app.route('/admin/categories', methods=['GET', 'POST'])
def admin_categories():
    if not session.get('logged_in'): return redirect('/admin-gate')
    if request.method == 'POST':
        name = request.form.get('name')
        limit = request.form.get('limit', 6)
        categories_col.update_one({"name": name}, {"$set": {"name": name, "limit": int(limit)}}, upsert=True)
        flash(f"Category '{name}' updated.")
        return redirect('/admin/categories')
    
    cats = list(categories_col.find().sort('name', 1))
    site = get_site_info()
    content = """
    <h1 class="text-4xl font-black mb-8 italic uppercase">Categories</h1>
    <div class="grid lg:grid-cols-12 gap-10">
        <form method="POST" class="lg:col-span-4 bg-slate-50 p-8 rounded-3xl border h-fit space-y-4">
            <h2 class="font-black text-indigo-600 uppercase">Add/Edit Category</h2>
            <input name="name" placeholder="Category Name (e.g. Games)" required>
            <input type="number" name="limit" placeholder="Home Post Limit (e.g. 12)" required>
            <button class="btn-main w-full py-4">SAVE CATEGORY</button>
        </form>
        <div class="lg:col-span-8 bg-white border rounded-3xl overflow-hidden">
            <table class="w-full text-left">
                <thead class="bg-slate-950 text-white text-[10px] uppercase font-bold">
                    <tr><th class="p-5">Category Name</th><th class="p-5 text-center">Post Limit</th><th class="p-5 text-right">Action</th></tr>
                </thead>
                <tbody class="text-sm">
                    {% for c in cats %}
                    <tr class="border-t hover:bg-slate-50">
                        <td class="p-5 font-bold text-slate-800">{{ c.name }}</td>
                        <td class="p-5 text-center font-black text-indigo-600">{{ c.limit }}</td>
                        <td class="p-5 text-right">
                            <a href="/admin/del-cat/{{ c._id }}" class="text-red-500 font-black hover:underline" onclick="return confirm('Delete category?')">DELETE</a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block admin_content %}{% endblock %}', content), site=site, cats=cats, is_admin_route=True, active="categories")

@app.route('/admin/media', methods=['GET', 'POST'])
def admin_media():
    if not session.get('logged_in'): return redirect('/admin-gate')
    if request.method == 'POST':
        media_col.insert_one({
            "title": request.form.get('title'), "url": request.form.get('url'),
            "link": request.form.get('link'), "created_at": datetime.now()
        })
        flash("New media added.")
        return redirect('/admin/media')
    
    media_list = list(media_col.find().sort('_id', -1))
    site = get_site_info()
    content = """
    <h1 class="text-4xl font-black mb-8 italic uppercase">Media Center</h1>
    <div class="grid lg:grid-cols-12 gap-10">
        <form method="POST" class="lg:col-span-4 bg-slate-50 p-8 rounded-3xl border h-fit space-y-4">
            <h2 class="font-black text-emerald-600 uppercase">New Banner/Media</h2>
            <input name="title" placeholder="Banner Title" required>
            <input name="url" placeholder="Image URL (Banner)" required>
            <input name="link" placeholder="Redirect Link" required>
            <button class="bg-emerald-600 text-white w-full py-4 rounded-xl font-bold">PUBLISH MEDIA</button>
        </form>
        <div class="lg:col-span-8 grid grid-cols-1 md:grid-cols-2 gap-6">
            {% for m in media_list %}
            <div class="bg-white border rounded-3xl overflow-hidden shadow-sm flex flex-col">
                <img src="{{ m.url }}" class="h-40 w-full object-cover">
                <div class="p-5">
                    <h3 class="font-black uppercase text-sm truncate mb-1">{{ m.title }}</h3>
                    <p class="text-[10px] text-slate-400 truncate mb-4">{{ m.link }}</p>
                    <a href="/admin/del-media/{{ m._id }}" class="text-red-500 text-xs font-black" onclick="return confirm('Remove media?')">REMOVE ITEM</a>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block admin_content %}{% endblock %}', content), site=site, media_list=media_list, is_admin_route=True, active="media")

@app.route('/admin/apps', methods=['GET', 'POST'])
def admin_apps():
    if not session.get('logged_in'): return redirect('/admin-gate')
    site = get_site_info()
    cats = list(categories_col.find().sort('name', 1))
    if request.method == 'POST':
        apps_col.insert_one({
            "name": request.form.get('name'), "logo": request.form.get('logo'),
            "category": request.form.get('category'), "version": request.form.get('version'),
            "info": request.form.get('info'), "download_link": request.form.get('download_link'),
            "created_at": datetime.now()
        })
        flash("Application published.")
        return redirect('/admin/apps')
    
    all_apps = list(apps_col.find().sort('_id', -1))
    content = """
    <h1 class="text-4xl font-black mb-8 italic uppercase">Apps Manager</h1>
    <div class="grid lg:grid-cols-12 gap-10">
        <form method="POST" class="lg:col-span-4 bg-slate-50 p-8 rounded-3xl border h-fit space-y-3">
            <h2 class="font-black text-indigo-600 uppercase">App Details</h2>
            <input name="name" placeholder="App Title" required>
            <input name="logo" placeholder="Logo Link" required>
            <select name="category" required>
                {% for c in cats %}<option value="{{c.name}}">{{c.name}}</option>{% endfor %}
            </select>
            <input name="version" placeholder="Version (e.g. 1.5.0)">
            <textarea name="info" placeholder="Short Description" class="h-24" required></textarea>
            <input name="download_link" placeholder="Final Download URL" required>
            <button class="btn-main w-full py-4 mt-2">PUBLISH APPLICATION</button>
        </form>
        <div class="lg:col-span-8 bg-white border rounded-3xl overflow-hidden">
            <table class="w-full text-left">
                <thead class="bg-slate-950 text-white text-[10px] uppercase">
                    <tr><th class="p-5">App Details</th><th class="p-5">Category</th><th class="p-5 text-right">Action</th></tr>
                </thead>
                <tbody class="text-xs">
                    {% for a in all_apps %}
                    <tr class="border-t">
                        <td class="p-5 flex items-center gap-3">
                            <img src="{{a.logo}}" class="w-10 h-10 rounded-xl border">{{a.name}}
                        </td>
                        <td class="p-5 uppercase font-bold text-slate-400">{{a.category}}</td>
                        <td class="p-5 text-right">
                            <a href="/del/app/{{a._id}}" class="text-red-500 font-black" onclick="return confirm('Delete app?')">DELETE</a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block admin_content %}{% endblock %}', content), site=site, all_apps=all_apps, cats=cats, is_admin_route=True, active="apps")

@app.route('/admin/ads', methods=['GET', 'POST'])
def admin_ads():
    if not session.get('logged_in'): return redirect('/admin-gate')
    if request.method == 'POST':
        ads_col.insert_one({"name": request.form.get('name'), "code": request.form.get('code'), "created_at": datetime.now()})
        flash("Ad integrated.")
        return redirect('/admin/ads')
    ads_list = list(ads_col.find())
    site = get_site_info()
    content = """
    <h1 class="text-4xl font-black mb-8 italic uppercase text-slate-800">Ads Management</h1>
    <div class="grid lg:grid-cols-2 gap-10">
        <form method="POST" class="bg-slate-50 p-8 rounded-3xl border space-y-4">
            <input name="name" placeholder="Ad Spot Name (e.g. Footer Ad)" required>
            <textarea name="code" placeholder="Paste Ad HTML/JS Script Code" class="h-64 font-mono text-sm" required></textarea>
            <button class="btn-main w-full py-4">DEPLOY AD CODE</button>
        </form>
        <div class="space-y-4">
            {% for ad in ads_list %}
            <div class="bg-white border p-6 rounded-2xl flex justify-between items-center">
                <span class="font-black uppercase text-sm italic">{{ ad.name }}</span>
                <a href="/del/ad/{{ ad._id }}" class="text-red-500 font-bold">REMOVE</a>
            </div>
            {% endfor %}
        </div>
    </div>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block admin_content %}{% endblock %}', content), site=site, ads_list=ads_list, is_admin_route=True, active="ads")

@app.route('/admin/layout', methods=['GET', 'POST'])
def admin_layout():
    if not session.get('logged_in'): return redirect('/admin-gate')
    site = get_site_info()
    if request.method == 'POST':
        settings_col.update_one({"type": "site_info"}, {"$set": {
            "name": request.form.get('name'), "logo": request.form.get('logo'), 
            "title": request.form.get('title'), "desc": request.form.get('desc'), 
            "copyright": request.form.get('copyright'), "fb": request.form.get('fb'), "ig": request.form.get('ig')
        }}, upsert=True)
        flash("Layout and Branding updated.")
        return redirect('/admin/layout')
    
    content = """
    <h1 class="text-4xl font-black mb-8 italic uppercase">Site Branding</h1>
    <form method="POST" class="bg-white p-10 rounded-3xl border shadow-sm max-w-4xl space-y-6">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div><label class="text-[10px] font-black uppercase ml-2 text-slate-400">Site Name</label><input name="name" value="{{site.name}}"></div>
            <div><label class="text-[10px] font-black uppercase ml-2 text-slate-400">Logo URL</label><input name="logo" value="{{site.logo}}"></div>
            <div><label class="text-[10px] font-black uppercase ml-2 text-slate-400">Meta Title</label><input name="title" value="{{site.title}}"></div>
            <div><label class="text-[10px] font-black uppercase ml-2 text-slate-400">Copyright Text</label><input name="copyright" value="{{site.copyright}}"></div>
        </div>
        <div><label class="text-[10px] font-black uppercase ml-2 text-slate-400">Footer Description</label><textarea name="desc" class="h-24">{{site.desc}}</textarea></div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div><label class="text-[10px] font-black uppercase ml-2 text-slate-400">Facebook URL</label><input name="fb" value="{{site.fb}}"></div>
            <div><label class="text-[10px] font-black uppercase ml-2 text-slate-400">Instagram URL</label><input name="ig" value="{{site.ig}}"></div>
        </div>
        <button class="btn-main w-full py-5 text-lg">SAVE ALL CHANGES</button>
    </form>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block admin_content %}{% endblock %}', content), site=site, is_admin_route=True, active="layout")

@app.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    if not session.get('logged_in'): return redirect('/admin-gate')
    site = get_site_info()
    if request.method == 'POST':
        settings_col.update_one({"type": "shortener"}, {"$set": {"url": request.form.get('url'), "api": request.form.get('api')}}, upsert=True)
        flash("API Settings Saved.")
        return redirect('/admin/settings')
    
    cfg = get_shortener()
    content = """
    <h1 class="text-4xl font-black mb-8 italic uppercase">API Settings</h1>
    <div class="bg-slate-950 p-12 rounded-[3rem] shadow-2xl">
        <h2 class="text-white font-black mb-6 uppercase tracking-widest text-sm text-emerald-400">Url Shortener Integration</h2>
        <form method="POST" class="space-y-6">
            <input name="url" value="{{cfg.url}}" placeholder="Domain Name (e.g. gplinks.in)" class="bg-slate-900 border-slate-800 text-white font-bold p-5">
            <input name="api" value="{{cfg.api}}" placeholder="Secret API Key" class="bg-slate-900 border-slate-800 text-white font-bold p-5">
            <button class="bg-emerald-500 text-black w-full py-5 rounded-2xl font-black text-lg">UPDATE SYSTEM CONFIG</button>
        </form>
    </div>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block admin_content %}{% endblock %}', content), site=site, cfg=cfg, is_admin_route=True, active="settings")

# --- AUTH ROUTES ---

@app.route('/admin-gate', methods=['GET', 'POST'])
def login():
    site = get_site_info()
    if request.method == 'POST':
        pw = request.form.get('password')
        admin = users_col.find_one({"username": "admin"})
        if not admin:
            # প্রথমবার লগইনে পাসওয়ার্ড সেট হবে
            users_col.insert_one({"username": "admin", "password": generate_password_hash(pw)})
            session['logged_in'] = True
            return redirect('/admin/dashboard')
        if check_password_hash(admin['password'], pw):
            session['logged_in'] = True
            return redirect('/admin/dashboard')
        flash("Access Denied!")
    
    return render_template_string(f"""
    <!DOCTYPE html><html><head>{BASE_CSS}</head>
    <body class="bg-slate-100 flex items-center justify-center min-h-screen p-6">
        <form method="POST" class="bg-white p-10 lg:p-16 rounded-[3rem] shadow-2xl w-full max-w-md text-center border-4 border-white">
            <img src="{site['logo']}" class="w-20 h-20 rounded-2xl mx-auto mb-8 shadow-xl">
            <h2 class="text-3xl font-black mb-10 uppercase italic tracking-tighter">Admin Auth</h2>
            <input type="password" name="password" class="text-center font-black text-2xl mb-8 p-5" placeholder="••••••••" required>
            <button class="bg-slate-950 text-white w-full py-5 rounded-2xl font-black text-xl shadow-2xl hover:bg-indigo-600 transition">LOG IN</button>
            <a href="/forgot" class="block mt-6 text-xs font-bold text-slate-400 uppercase tracking-widest">Forgot Password?</a>
        </form>
    </body></html>
    """)

@app.route('/forgot', methods=['GET', 'POST'])
def forgot():
    if request.method == 'POST':
        if request.form.get('key') == RECOVERY_KEY:
            users_col.update_one({"username": "admin"}, {"$set": {"password": generate_password_hash(request.form.get('pw'))}}, upsert=True)
            flash("Password Reset Successful.")
            return redirect('/admin-gate')
    return render_template_string(f"<!DOCTYPE html><html><head>{BASE_CSS}</head><body class='bg-slate-50 flex items-center justify-center min-h-screen'><form method='POST' class='bg-white p-12 rounded-[3rem] shadow-xl w-full max-w-md space-y-6'><h2 class='font-black uppercase text-center italic'>Reset Security</h2><input name='key' placeholder='Recovery Key' required><input type='password' name='pw' placeholder='New Password' required><button class='btn-main w-full py-4'>RESET NOW</button></form></body></html>")

# --- DELETE UTILS ---

@app.route('/admin/del-cat/<id>')
def delete_cat(id):
    if not session.get('logged_in'): return redirect('/admin-gate')
    categories_col.delete_one({"_id": ObjectId(id)})
    flash("Category deleted.")
    return redirect('/admin/categories')

@app.route('/admin/del-media/<id>')
def delete_media(id):
    if not session.get('logged_in'): return redirect('/admin-gate')
    media_col.delete_one({"_id": ObjectId(id)})
    flash("Media removed.")
    return redirect('/admin/media')

@app.route('/del/<type>/<id>')
def delete_entry(type, id):
    if not session.get('logged_in'): return redirect('/admin-gate')
    if type == 'app': apps_col.delete_one({"_id": ObjectId(id)})
    if type == 'ad': ads_col.delete_one({"_id": ObjectId(id)})
    flash("Deleted successfully.")
    return redirect(request.referrer)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# --- START SERVER ---
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
