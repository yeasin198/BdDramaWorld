import os
import requests
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# --- CONFIGURATION & SECURITY ---
# এই সিক্রেট কি গুলো ভার্সেল এনভায়রনমেন্টে সেট করবেন
app.secret_key = os.environ.get("SESSION_SECRET", "super_high_secure_long_secret_key_v100_final_2024")
RECOVERY_KEY = os.environ.get("RECOVERY_KEY", "admin@2024")

# --- MONGODB CONNECTION ---
try:
    # আপনার দেওয়া MongoDB কানেকশন লিঙ্ক
    MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client['app_hub_production_ultimate_system']
    apps_col = db['apps']
    users_col = db['users']
    ads_col = db['ads']
    settings_col = db['settings']
except Exception as e:
    print(f"DATABASE CONNECTION ERROR: {e}")

# --- DYNAMIC SITE HELPERS ---
def get_site_info():
    info = settings_col.find_one({"type": "site_info"})
    if not info:
        return {"name": "APPHUB PRO", "title": "Ultimate Premium App Store", "logo": "https://cdn-icons-png.flaticon.com/512/2589/2589127.png"}
    return info

def get_shortener():
    return settings_col.find_one({"type": "shortener"}) or {"url": "", "api": ""}

# --- HTML TEMPLATES (EXTENSIVE & DETAILED DESIGN) ---

# ডিজাইন এরর এড়াতে টেমপ্লেটগুলো f-string ছাড়াই রাখা হয়েছে
BASE_CSS = """
<script src="https://cdn.tailwindcss.com"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.css" />
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;700;800&display=swap');
    body { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #f8fafc; color: #0f172a; scroll-behavior: smooth; }
    .glass-nav { background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(15px); border-bottom: 1px solid rgba(226, 232, 240, 0.8); }
    .hero-gradient { background: linear-gradient(135deg, #4f46e5 0%, #1e1b4b 100%); }
    .pro-card { background: white; border: 1px solid #f1f5f9; border-radius: 2.5rem; transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1); }
    .pro-card:hover { transform: translateY(-10px); box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.1); border-color: #6366f1; }
    .sidebar-link { display: flex; align-items: center; gap: 12px; padding: 14px 20px; border-radius: 18px; font-weight: 600; color: #94a3b8; transition: 0.3s; }
    .sidebar-link:hover { background: rgba(99, 102, 241, 0.1); color: #6366f1; }
    .sidebar-active { background: #6366f1 !important; color: white !important; box-shadow: 0 10px 15px -3px rgba(99, 102, 241, 0.4); }
    .swiper { width: 100%; height: 450px; border-radius: 3rem; overflow: hidden; margin-bottom: 3rem; box-shadow: 0 20px 40px -10px rgba(0,0,0,0.3); }
    .line-clamp-2 { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
    .btn-main { background: #6366f1; color: white; padding: 12px 28px; border-radius: 18px; font-weight: 700; transition: 0.3s; display: inline-flex; align-items: center; gap: 8px; box-shadow: 0 4px 14px 0 rgba(99, 102, 241, 0.4); }
    .btn-main:hover { background: #4f46e5; transform: scale(1.05); }
    input, textarea, select { border: 2px solid #f1f5f9; border-radius: 18px; padding: 14px 18px; outline: none; transition: 0.3s; background: #fff; }
    input:focus { border-color: #6366f1; box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.1); }
    .footer-bg { background: #0f172a; color: #94a3b8; }
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
    <nav class="glass-nav h-20 sticky top-0 z-50">
        <div class="container mx-auto px-6 h-full flex items-center justify-between">
            <a href="/" class="flex items-center gap-3">
                <img src="{{ site.logo }}" class="w-10 h-10 rounded-xl">
                <span class="text-2xl font-black text-slate-900 tracking-tighter uppercase">{{ site.name }}</span>
            </a>
            <div class="hidden lg:flex flex-1 max-w-xl mx-12">
                <form action="/" method="GET" class="w-full flex bg-slate-100 rounded-2xl px-5 py-2.5 items-center border border-slate-200">
                    <input type="text" name="q" placeholder="Search apps, games, tools..." class="bg-transparent outline-none text-sm w-full font-medium" value="{{ q }}">
                    <button type="submit"><i class="fas fa-search text-indigo-600"></i></button>
                </form>
            </div>
            <div class="flex items-center gap-4">
                <div class="hidden sm:block text-[10px] font-black bg-indigo-600 text-white px-3 py-1.5 rounded-full uppercase tracking-widest">v10.0 Pro</div>
            </div>
        </div>
    </nav>
    {% endif %}

    <div class="{% if is_admin_route %}flex min-h-screen{% else %}container mx-auto px-6 py-12{% endif %}">
        {% if is_admin_route %}
        <!-- ADMIN SIDEBAR -->
        <div class="w-80 bg-slate-950 text-slate-400 p-8 flex flex-col sticky top-0 h-screen shadow-2xl">
            <div class="flex items-center gap-3 mb-12 border-b border-slate-900 pb-6">
                <img src="{{ site.logo }}" class="w-10 h-10 rounded-xl shadow-lg">
                <span class="text-xl font-black text-white uppercase tracking-tighter italic">{{ site.name }}</span>
            </div>
            <div class="flex-1 space-y-3">
                <a href="/admin/dashboard" class="sidebar-link {% if active == 'dashboard' %}sidebar-active{% endif %}"><i class="fas fa-chart-line"></i> Overview</a>
                <a href="/admin/apps" class="sidebar-link {% if active == 'apps' %}sidebar-active{% endif %}"><i class="fas fa-cube"></i> All Applications</a>
                <a href="/admin/ads" class="sidebar-link {% if active == 'ads' %}sidebar-active{% endif %}"><i class="fas fa-ad"></i> Ad Placements</a>
                <a href="/admin/settings" class="sidebar-link {% if active == 'settings' %}sidebar-active{% endif %}"><i class="fas fa-sliders-h"></i> System Settings</a>
            </div>
            <div class="pt-8 border-t border-slate-900 space-y-4">
                <a href="/" class="block text-emerald-400 font-black flex items-center gap-3"><i class="fas fa-external-link-alt"></i> OPEN LIVE SITE</a>
                <a href="/logout" class="block text-red-500 font-black flex items-center gap-3"><i class="fas fa-power-off"></i> LOGOUT</a>
            </div>
        </div>
        <div class="flex-1 bg-white p-12 overflow-y-auto">
            {% with messages = get_flashed_messages() %}
                {% if messages %}
                    {% for msg in messages %}
                        <div class="bg-indigo-600 text-white p-5 rounded-3xl mb-10 shadow-2xl animate-pulse flex justify-between">
                            <span><i class="fas fa-check-circle mr-2"></i> {{ msg }}</span>
                            <button onclick="this.parentElement.remove()"><i class="fas fa-times"></i></button>
                        </div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
            {% block admin_content %}{% endblock %}
        </div>
        {% else %}
        <!-- USER CONTENT -->
        <div class="w-full min-h-[70vh]">
            {% with messages = get_flashed_messages() %}
                {% if messages %}
                    {% for msg in messages %}
                        <div class="bg-indigo-100 text-indigo-700 p-5 rounded-3xl mb-10 border-l-8 border-indigo-600 shadow-sm">{{ msg }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
            {% block content %}{% endblock %}
        </div>
        {% endif %}
    </div>

    {% if not is_admin_route %}
    <footer class="footer-bg py-20 mt-20">
        <div class="container mx-auto px-6 grid grid-cols-1 md:grid-cols-3 gap-16">
            <div>
                <h3 class="text-white text-2xl font-black mb-6 uppercase">{{ site.name }}</h3>
                <p class="text-sm leading-relaxed mb-8">Ultimate platform for high-performance applications. Discover, search and download your favorite tools with maximum speed and security.</p>
                <div class="flex gap-4">
                    <div class="w-10 h-10 bg-slate-900 rounded-full flex items-center justify-center hover:bg-indigo-600 transition"><i class="fab fa-facebook-f text-white"></i></div>
                    <div class="w-10 h-10 bg-slate-900 rounded-full flex items-center justify-center hover:bg-indigo-600 transition"><i class="fab fa-twitter text-white"></i></div>
                    <div class="w-10 h-10 bg-slate-900 rounded-full flex items-center justify-center hover:bg-indigo-600 transition"><i class="fab fa-instagram text-white"></i></div>
                </div>
            </div>
            <div>
                <h4 class="text-white font-bold mb-6 uppercase tracking-widest">Explore Categories</h4>
                <ul class="space-y-3 text-sm">
                    <li><a href="#" class="hover:text-indigo-400 transition">Android Applications</a></li>
                    <li><a href="#" class="hover:text-indigo-400 transition">iOS Premium Tools</a></li>
                    <li><a href="#" class="hover:text-indigo-400 transition">Desktop Software</a></li>
                    <li><a href="#" class="hover:text-indigo-400 transition">Latest Games</a></li>
                </ul>
            </div>
            <div>
                <h4 class="text-white font-bold mb-6 uppercase tracking-widest">Support & Legal</h4>
                <ul class="space-y-3 text-sm">
                    <li><a href="#" class="hover:text-indigo-400 transition">Privacy Policy</a></li>
                    <li><a href="#" class="hover:text-indigo-400 transition">Terms of Service</a></li>
                    <li><a href="#" class="hover:text-indigo-400 transition">DMCA Takedown</a></li>
                    <li><a href="/admin-gate" class="hover:text-indigo-400 transition">Administrator Access</a></li>
                </ul>
            </div>
        </div>
        <div class="border-t border-slate-900 mt-16 pt-8 text-center text-[10px] font-bold uppercase tracking-[0.3em]">
            &copy; 2024 {{ site.name }} Ultimate PRO v10.0. All Rights Reserved.
        </div>
    </footer>
    {% endif %}

    <script src="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.js"></script>
    <script>
        const swiper = new Swiper('.swiper', {
            loop: true, autoplay: { delay: 4000, disableOnInteraction: false },
            pagination: { el: '.swiper-pagination', clickable: true },
            navigation: { nextEl: '.swiper-button-next', prevEl: '.swiper-button-prev' },
            effect: 'fade', fadeEffect: { crossFade: true }
        });
    </script>
</body>
</html>
"""

# --- ROUTES ---

@app.route('/')
def home():
    site = get_site_info()
    q = request.args.get('q', '')
    if q:
        apps = list(apps_col.find({"name": {"$regex": q, "$options": "i"}}).sort('_id', -1))
        featured = []
    else:
        apps = list(apps_col.find().sort('_id', -1))
        featured = list(apps_col.find({"featured": "on"}).limit(5))
    
    ads = list(ads_col.find())
    
    content = """
    <!-- HERO SLIDER SECTION -->
    {% if featured %}
    <div class="swiper mb-16 shadow-2xl">
        <div class="swiper-wrapper">
            {% for f in featured %}
            <div class="swiper-slide hero-gradient relative flex items-center p-10 md:p-20 text-white overflow-hidden">
                <div class="absolute inset-0 bg-indigo-950 opacity-20 z-0"></div>
                <div class="relative z-10 max-w-2xl">
                    <span class="bg-indigo-500 text-[10px] font-black px-4 py-1.5 rounded-full uppercase mb-6 inline-block tracking-widest shadow-xl">Top Featured Choice</span>
                    <h2 class="text-5xl md:text-7xl font-black mb-6 leading-tight tracking-tighter uppercase italic">{{ f.name }}</h2>
                    <p class="text-indigo-100 text-lg md:text-xl mb-10 line-clamp-2 opacity-80 font-medium leading-relaxed">{{ f.info }}</p>
                    <div class="flex flex-wrap gap-4">
                        <a href="/app/{{f._id}}" class="bg-white text-indigo-900 px-12 py-5 rounded-3xl font-black text-xl shadow-2xl hover:scale-105 transition transform flex items-center gap-3">
                            <i class="fas fa-info-circle"></i> EXPLORE DETAILS
                        </a>
                    </div>
                </div>
                <div class="absolute right-[-50px] top-1/2 -translate-y-1/2 hidden lg:block rotate-12 transition duration-1000">
                    <img src="{{f.logo}}" class="w-[450px] h-[450px] rounded-[5rem] shadow-2xl border-[15px] border-white/10 opacity-60">
                </div>
            </div>
            {% endfor %}
        </div>
        <div class="swiper-pagination"></div>
    </div>
    {% endif %}

    <!-- ADS PLACEMENTS -->
    <div class="max-w-4xl mx-auto mb-16 space-y-8">
        {% for ad in ads %}
        <div class="bg-white p-6 rounded-[2.5rem] border-2 border-slate-100 shadow-sm flex justify-center items-center overflow-hidden min-h-[100px]">
            {{ ad.code | safe }}
        </div>
        {% endfor %}
    </div>

    <!-- SEARCH & GRID SECTION -->
    <div class="flex flex-col md:flex-row items-center justify-between mb-12 gap-6">
        <div>
            <h2 class="text-4xl font-black text-slate-900 tracking-tighter uppercase italic">
                {% if q %}SEARCH RESULTS: "{{q}}"{% else %}LATEST DISCOVERIES{% endif %}
            </h2>
            <p class="text-slate-400 font-bold uppercase text-[10px] tracking-widest mt-1">Verified Premium Applications</p>
        </div>
        <span class="bg-indigo-50 text-indigo-600 px-6 py-2 rounded-full font-black text-xs border border-indigo-100 uppercase tracking-widest">
            {{ apps|length }} APPS FOUND
        </span>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-12">
        {% for app in apps %}
        <a href="/app/{{app._id}}" class="pro-card p-10 group text-center flex flex-col items-center">
            <div class="relative mb-8">
                <div class="absolute inset-0 bg-indigo-600 rounded-[3rem] blur-2xl opacity-0 group-hover:opacity-20 transition duration-500"></div>
                <img src="{{app.logo}}" class="w-32 h-32 rounded-[3rem] shadow-2xl relative z-10 group-hover:scale-110 transition duration-500 border-4 border-white">
                {% if app.featured == 'on' %}
                <div class="absolute -top-3 -right-3 bg-orange-500 text-white text-[9px] font-black px-3 py-1 rounded-full shadow-xl z-20 animate-bounce">PRO</div>
                {% endif %}
            </div>
            <h3 class="font-black text-2xl text-slate-800 mb-3 tracking-tighter line-clamp-1 uppercase">{{app.name}}</h3>
            <div class="flex gap-2 mb-6 font-black uppercase text-[9px] tracking-widest">
                <span class="bg-indigo-50 text-indigo-600 px-3 py-1 rounded-full border border-indigo-100">{{app.category}}</span>
                <span class="bg-slate-100 text-slate-500 px-3 py-1 rounded-full">VERSION {{app.version}}</span>
            </div>
            <p class="text-xs text-slate-400 line-clamp-2 h-10 mb-8 leading-relaxed font-semibold italic">{{app.info}}</p>
            <div class="btn-main w-full justify-center py-4 bg-slate-900 group-hover:bg-indigo-600 shadow-xl">
                DOWNLOAD NOW <i class="fas fa-bolt"></i>
            </div>
        </a>
        {% endfor %}
    </div>

    {% if not apps %}
    <div class="py-40 text-center">
        <i class="fas fa-search text-9xl text-slate-200 mb-8"></i>
        <h3 class="text-3xl font-black text-slate-400 uppercase tracking-tighter">No Applications Found</h3>
        <p class="text-slate-400 mt-4">Try searching with a different keyword.</p>
        <a href="/" class="inline-block mt-8 text-indigo-600 font-black underline">Back to Homepage</a>
    </div>
    {% endif %}
    """
    return render_template_string(BASE_LAYOUT.replace('{% block content %}{% endblock %}', content), site=site, apps=apps, featured=featured, ads=ads, q=q, is_admin_route=False)

@app.route('/app/<id>')
def details(id):
    site = get_site_info()
    app_data = apps_col.find_one({"_id": ObjectId(id)})
    if not app_data: return redirect('/')
    
    content = """
    <div class="max-w-6xl mx-auto">
        <div class="bg-white rounded-[4rem] shadow-2xl p-10 md:p-20 flex flex-col md:flex-row gap-20 items-center border border-slate-100 relative overflow-hidden">
            <div class="absolute -top-20 -right-20 p-20 opacity-[0.03] text-indigo-950 pointer-events-none rotate-12">
                <i class="fas fa-download text-[500px]"></i>
            </div>
            
            <div class="relative z-10 flex-shrink-0">
                <img src="{{app.logo}}" class="w-80 h-80 rounded-[5rem] shadow-2xl border-[15px] border-slate-50">
                <div class="absolute -bottom-8 -right-8 bg-emerald-500 text-white p-10 rounded-full shadow-2xl border-8 border-white">
                    <i class="fas fa-shield-halved text-4xl"></i>
                </div>
            </div>
            
            <div class="flex-1 text-center md:text-left z-10">
                <div class="flex flex-wrap gap-4 mb-8 justify-center md:justify-start">
                    <span class="bg-indigo-600 text-white px-8 py-2.5 rounded-full font-black text-xs uppercase tracking-widest shadow-lg">{{app.category}} Platform</span>
                    <span class="bg-emerald-50 text-emerald-600 px-8 py-2.5 rounded-full font-black text-xs uppercase tracking-widest border border-emerald-100">Version {{app.version}}</span>
                </div>
                
                <h1 class="text-7xl font-black text-slate-950 mb-10 leading-none tracking-tighter italic uppercase underline decoration-indigo-200 decoration-8 underline-offset-[10px]">{{app.name}}</h1>
                <p class="text-slate-500 text-2xl font-medium leading-relaxed mb-12 opacity-90 italic">"{{app.info}}"</p>
                
                <div class="grid grid-cols-2 md:grid-cols-3 gap-8 mb-16">
                    <div class="bg-slate-50 p-8 rounded-[2.5rem] border border-slate-200">
                        <p class="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2">Publish Date</p>
                        <p class="font-black text-slate-800 text-xl tracking-tighter uppercase">{{app.release_date}}</p>
                    </div>
                    <div class="bg-slate-50 p-8 rounded-[2.5rem] border border-slate-200">
                        <p class="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2">Platform Compatibility</p>
                        <p class="font-black text-indigo-600 text-xl tracking-tighter uppercase">{{app.category}}</p>
                    </div>
                    <div class="bg-emerald-50 p-8 rounded-[2.5rem] border border-emerald-100 hidden md:block">
                        <p class="text-[10px] font-black text-emerald-400 uppercase tracking-widest mb-2">Verification Status</p>
                        <p class="font-black text-emerald-600 text-xl tracking-tighter uppercase">Verified Safe</p>
                    </div>
                </div>

                <a href="/get/{{app._id}}" class="inline-flex items-center gap-6 bg-slate-900 text-white px-20 py-8 rounded-full font-black text-3xl shadow-2xl hover:bg-indigo-700 hover:scale-105 transition transform shadow-indigo-200">
                    <i class="fas fa-cloud-arrow-down animate-bounce"></i> SECURE DOWNLOAD
                </a>
                
                <div class="mt-12 flex items-center justify-center md:justify-start gap-3 text-slate-400 font-bold uppercase text-xs tracking-widest italic">
                    <i class="fas fa-lock text-emerald-500"></i> SSL Encrypted & Private Redirection Active
                </div>
            </div>
        </div>
    </div>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block content %}{% endblock %}', content), site=site, app=app_data, is_admin_route=False)

@app.route('/get/<id>')
def download_process(id):
    app_data = apps_col.find_one({"_id": ObjectId(id)})
    if not app_data: return redirect('/')
    cfg = get_shortener()
    target = app_data['download_link']
    
    if cfg.get('url') and cfg.get('api'):
        try:
            # External Shortener API Call
            api_endpoint = f"https://{cfg['url']}/api?api={cfg['api']}&url={target}"
            res = requests.get(api_endpoint, timeout=12).json()
            short_url = res.get('shortenedUrl') or res.get('shortedUrl')
            if short_url: return redirect(short_url)
        except Exception as e:
            print(f"SHORTENER ERROR: {e}")
            
    return redirect(target)

# --- ADMIN AUTHENTICATION (SECURE & HIDDEN) ---

@app.route('/admin-gate', methods=['GET', 'POST'])
def login():
    site = get_site_info()
    admin_user = users_col.find_one({"username": "admin"})
    if request.method == 'POST':
        pw = request.form.get('password')
        if not admin_user:
            users_col.insert_one({"username": "admin", "password": generate_password_hash(pw)})
            session['logged_in'] = True
            return redirect('/admin/dashboard')
        if check_password_hash(admin_user['password'], pw):
            session['logged_in'] = True
            return redirect('/admin/dashboard')
        flash("CRITICAL: Invalid Administrative Credentials Detected!")
    
    content = f"""
    <div class="max-w-lg mx-auto mt-32 bg-white p-20 rounded-[5rem] shadow-2xl border-4 border-slate-50 text-center">
        <div class="w-24 h-24 bg-indigo-600 rounded-[2.5rem] mx-auto mb-10 flex items-center justify-center shadow-2xl shadow-indigo-200">
            <i class="fas fa-user-shield text-white text-4xl"></i>
        </div>
        <h2 class="text-4xl font-black mb-10 text-slate-900 tracking-tighter uppercase italic underline decoration-indigo-100 underline-offset-8">Admin Auth</h2>
        <form method="POST" class="space-y-8">
            <input type="password" name="password" placeholder="ENTER ACCESS CODE" class="w-full bg-slate-50 p-6 rounded-[2rem] text-center mb-4 outline-none border-2 border-slate-100 focus:border-indigo-500 transition-all font-black text-2xl tracking-widest uppercase" required>
            <button class="bg-indigo-600 text-white w-full py-6 rounded-[2rem] font-black text-xl shadow-2xl shadow-indigo-100 hover:bg-slate-900 transition-all uppercase tracking-widest">Authenticate Access</button>
        </form>
        <div class="mt-10 pt-8 border-t border-slate-50"><a href="/forgot" class="text-xs font-bold text-slate-300 hover:text-red-500 uppercase tracking-widest transition">System Override Tool</a></div>
    </div>
    """
    return render_template_string(f"<!DOCTYPE html><html lang='en'><head>{BASE_CSS}</head><body class='bg-slate-100'>{content}</body></html>")

# --- ADMIN PANEL FUNCTIONALITY ---

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('logged_in'): return redirect('/admin-gate')
    site = get_site_info()
    stats = {
        "apps": apps_col.count_documents({}),
        "ads": ads_col.count_documents({}),
        "featured": apps_col.count_documents({"featured": "on"})
    }
    
    content = """
    <div class="mb-16">
        <h1 class="text-6xl font-black text-slate-950 tracking-tighter mb-4 uppercase italic">Overview</h1>
        <p class="text-slate-400 font-black uppercase tracking-widest text-xs ml-1">Platform Performance & Statistics</p>
    </div>
    
    <div class="grid grid-cols-1 md:grid-cols-3 gap-12 mb-20">
        <div class="bg-indigo-600 p-12 rounded-[4rem] text-white shadow-2xl shadow-indigo-200 flex flex-col justify-between h-80 relative overflow-hidden group">
            <i class="fas fa-cube absolute right-[-40px] bottom-[-40px] text-[200px] opacity-10 rotate-12 group-hover:rotate-0 transition duration-1000"></i>
            <div class="text-8xl font-black tracking-tighter">{{ stats.apps }}</div>
            <div>
                <p class="font-black uppercase tracking-widest text-xs opacity-70">Total Applications</p>
                <h4 class="text-xl font-bold">Synchronized in DB</h4>
            </div>
        </div>
        <div class="bg-slate-950 p-12 rounded-[4rem] text-white shadow-2xl shadow-slate-200 flex flex-col justify-between h-80 relative overflow-hidden group border-4 border-slate-900">
            <i class="fas fa-ad absolute right-[-40px] bottom-[-40px] text-[200px] opacity-10 rotate-12 group-hover:rotate-0 transition duration-1000"></i>
            <div class="text-8xl font-black tracking-tighter">{{ stats.ads }}</div>
            <div>
                <p class="font-black uppercase tracking-widest text-xs opacity-70">Active Ad Units</p>
                <h4 class="text-xl font-bold">Monetization Active</h4>
            </div>
        </div>
        <div class="bg-orange-500 p-12 rounded-[4rem] text-white shadow-2xl shadow-orange-100 flex flex-col justify-between h-80 relative overflow-hidden group">
            <i class="fas fa-star absolute right-[-40px] bottom-[-40px] text-[200px] opacity-10 rotate-12 group-hover:rotate-0 transition duration-1000"></i>
            <div class="text-8xl font-black tracking-tighter">{{ stats.featured }}</div>
            <div>
                <p class="font-black uppercase tracking-widest text-xs opacity-70">Slider Highlights</p>
                <h4 class="text-xl font-bold">Featured on Home</h4>
            </div>
        </div>
    </div>
    
    <div class="bg-slate-50 p-16 rounded-[5rem] border-4 border-dashed border-slate-200 flex items-center justify-between shadow-inner">
        <div class="max-w-2xl">
            <h2 class="text-4xl font-black text-slate-900 mb-6 tracking-tighter uppercase">Platform Master Console</h2>
            <p class="text-slate-500 text-xl font-medium leading-relaxed italic">"Administrator, your platform is operating at 100% capacity. Your database is healthy and all external APIs are responding within optimal latency. Manage your assets using the high-performance navigation menu."</p>
        </div>
        <img src="https://cdn-icons-png.flaticon.com/512/3649/3649460.png" class="w-64 hidden lg:block opacity-20 filter grayscale">
    </div>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block admin_content %}{% endblock %}', content), site=site, stats=stats, is_admin_route=True, active="dashboard")

@app.route('/admin/apps', methods=['GET', 'POST'])
def admin_apps():
    if not session.get('logged_in'): return redirect('/admin-gate')
    site = get_site_info()
    if request.method == 'POST':
        apps_col.insert_one({
            "name": request.form.get('name'), "logo": request.form.get('logo'),
            "category": request.form.get('category'), "release_date": request.form.get('release_date'),
            "version": request.form.get('version'), "info": request.form.get('info'),
            "download_link": request.form.get('download_link'), "featured": request.form.get('featured'),
            "created_at": datetime.now()
        })
        flash("Platform Update: New application entry published successfully.")
        return redirect('/admin/apps')
    
    q = request.args.get('q', '')
    query = {"name": {"$regex": q, "$options": "i"}} if q else {}
    apps = list(apps_col.find(query).sort('_id', -1))
    
    content = """
    <div class="flex flex-col xl:flex-row justify-between items-start xl:items-center mb-16 gap-10">
        <h1 class="text-6xl font-black tracking-tighter italic uppercase underline decoration-indigo-200 decoration-8">Content Lab</h1>
        <form class="bg-slate-100 px-10 py-4 rounded-full border-2 border-slate-200 flex items-center w-full xl:w-[500px] focus-within:border-indigo-600 transition shadow-inner">
            <input type="text" name="q" placeholder="Global search and manage apps..." class="bg-transparent outline-none text-lg w-full font-black text-slate-700 uppercase" value="{{q}}">
            <button type="submit"><i class="fas fa-search text-indigo-600 text-xl"></i></button>
        </form>
    </div>

    <div class="grid xl:grid-cols-12 gap-16">
        <!-- ADVANCED FORM -->
        <div class="xl:col-span-4 bg-white p-12 rounded-[4rem] shadow-2xl border-2 border-slate-50 h-fit sticky top-28">
            <h2 class="text-3xl font-black mb-10 text-indigo-700 italic border-b pb-6 uppercase tracking-tighter">Publish Content</h2>
            <form method="POST" class="space-y-6">
                <div>
                    <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-2 mb-2 block">Application Title</label>
                    <input name="name" placeholder="Enter Full Name" class="w-full font-bold text-lg" required>
                </div>
                <div>
                    <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-2 mb-2 block">Logo Resource URL</label>
                    <input name="logo" placeholder="Direct Link to Icon" class="w-full" required>
                </div>
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-2 mb-2 block">Release Date</label>
                        <input type="date" name="release_date" class="w-full" required>
                    </div>
                    <div>
                        <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-2 mb-2 block">Version</label>
                        <input name="version" placeholder="v1.0.0" class="w-full font-black" required>
                    </div>
                </div>
                <div>
                    <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-2 mb-2 block">Target Platform</label>
                    <select name="category" class="w-full font-bold uppercase tracking-widest text-xs">
                        <option>Mobile (Android)</option><option>iOS (Apple)</option><option>Desktop (PC)</option>
                    </select>
                </div>
                <div>
                    <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-2 mb-2 block">Meta Description</label>
                    <textarea name="info" placeholder="Detailed app info..." class="w-full h-32 leading-relaxed font-medium" required></textarea>
                </div>
                <div>
                    <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-2 mb-2 block">Redirect Destination URL</label>
                    <input name="download_link" placeholder="Final APK Link" class="w-full" required>
                </div>
                <label class="flex items-center gap-4 font-black text-indigo-700 bg-indigo-50 p-6 rounded-3xl cursor-pointer hover:bg-indigo-100 transition">
                    <input type="checkbox" name="featured" class="w-7 h-7 rounded-xl accent-indigo-600 border-none outline-none"> 
                    <span class="uppercase tracking-tighter text-sm">Synchronize with Home Slider</span>
                </label>
                <button class="btn-main w-full justify-center py-6 rounded-[2.5rem] uppercase font-black text-xl tracking-widest italic mt-4 shadow-indigo-200 shadow-2xl">PUBLISH ASSET</button>
            </form>
        </div>
        <!-- DATA TABLE -->
        <div class="xl:col-span-8 bg-white rounded-[4rem] border-4 border-slate-50 overflow-hidden shadow-2xl">
            <table class="w-full text-left">
                <thead class="bg-slate-900 text-white">
                    <tr><th class="p-8 font-black uppercase text-xs tracking-[0.3em]">Identity Details</th><th class="p-8 text-right font-black uppercase text-xs tracking-[0.3em]">Critical Operations</th></tr>
                </thead>
                <tbody>
                    {% for a in apps %}
                    <tr class="border-b border-slate-50 hover:bg-indigo-50/30 transition duration-500 group">
                        <td class="p-8 flex items-center gap-8">
                            <div class="relative flex-shrink-0">
                                <img src="{{a.logo}}" class="w-20 h-20 rounded-[2.5rem] shadow-2xl group-hover:scale-110 transition duration-700 object-cover border-4 border-white">
                                {% if a.featured %}<div class="absolute -top-3 -right-3 bg-orange-500 text-white text-[8px] font-black px-3 py-1 rounded-full shadow-xl animate-pulse">SLIDER</div>{% endif %}
                            </div>
                            <div>
                                <p class="font-black text-slate-950 text-2xl tracking-tighter mb-1 uppercase italic leading-none group-hover:text-indigo-600 transition">{{a.name}}</p>
                                <div class="flex items-center gap-3">
                                    <span class="text-[9px] font-black bg-indigo-600 text-white px-2.5 py-0.5 rounded-full uppercase tracking-widest">{{a.category}}</span>
                                    <span class="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest">v{{a.version}}</span>
                                </div>
                            </div>
                        </td>
                        <td class="p-8 text-right">
                            <a href="/del/app/{{a._id}}" class="text-red-500 font-black text-xs bg-red-50 px-10 py-4 rounded-[2rem] hover:bg-red-500 hover:text-white transition duration-500 shadow-xl shadow-red-100" onclick="return confirm('CRITICAL WARNING: This asset will be permanently purged from the database. Proceed?')">REMOVE ASSET</a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% if not apps %}
            <div class="p-40 text-center flex flex-col items-center">
                <i class="fas fa-folder-open text-9xl text-slate-100 mb-8"></i>
                <h3 class="text-3xl font-black text-slate-200 uppercase tracking-widest">No Database Entries</h3>
            </div>
            {% endif %}
        </div>
    </div>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block admin_content %}{% endblock %}', content), site=site, apps=apps, q=q, is_admin_route=True, active="apps")

@app.route('/admin/ads', methods=['GET', 'POST'])
def admin_ads():
    if not session.get('logged_in'): return redirect('/admin-gate')
    site = get_site_info()
    if request.method == 'POST':
        ads_col.insert_one({"name": request.form.get('name'), "code": request.form.get('code'), "created_at": datetime.now()})
        flash("Monetization Module: Ad unit snippet successfully integrated into server.")
        return redirect('/admin/ads')
    
    ads_list = list(ads_col.find())
    content = """
    <h1 class="text-6xl font-black mb-16 tracking-tighter italic uppercase underline decoration-emerald-200 decoration-8 underline-offset-8">Monetization Hub</h1>
    <div class="grid lg:grid-cols-12 gap-16">
        <div class="lg:col-span-5 bg-white p-12 rounded-[4rem] border-2 border-slate-50 shadow-2xl h-fit">
            <h2 class="text-3xl font-black mb-10 text-emerald-600 italic border-b pb-6 uppercase tracking-tighter">Inject New Script</h2>
            <form method="POST" class="space-y-6">
                <div>
                    <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-2 mb-2 block">Ad Unit Identity</label>
                    <input name="name" placeholder="Header / Interstitial / Sidebar" class="w-full font-bold" required>
                </div>
                <div>
                    <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-2 mb-2 block">JavaScript/HTML Code Snippet</label>
                    <textarea name="code" placeholder="Paste full script code here..." class="w-full h-80 font-mono text-xs focus:ring-4 ring-emerald-500/10 border-emerald-100 leading-relaxed" required></textarea>
                </div>
                <button class="btn-main w-full justify-center py-6 bg-emerald-600 hover:bg-emerald-700 shadow-emerald-200 uppercase font-black tracking-widest italic text-lg">DEPLOY AD UNIT</button>
            </form>
        </div>
        <div class="lg:col-span-7 space-y-8">
            <h2 class="text-3xl font-black text-slate-900 mb-10 tracking-tighter uppercase italic">Active Units ({{ ads|length }})</h2>
            {% for ad in ads %}
            <div class="flex justify-between items-center p-10 bg-white border-2 border-slate-50 rounded-[3rem] shadow-sm hover:shadow-2xl transition duration-500 group">
                <div class="flex items-center gap-8">
                    <div class="w-16 h-16 bg-emerald-100 text-emerald-600 rounded-[2rem] flex items-center justify-center text-2xl shadow-inner group-hover:bg-emerald-600 group-hover:text-white transition duration-500">
                        <i class="fas fa-ad"></i>
                    </div>
                    <div>
                        <p class="font-black text-slate-950 text-3xl tracking-tighter mb-1 uppercase">{{ ad.name }}</p>
                        <p class="text-xs font-black text-emerald-500 uppercase tracking-[0.2em] italic flex items-center gap-2">
                            <span class="w-2 h-2 bg-emerald-500 rounded-full animate-ping"></span> STATUS: LIVE & BROADCASTING
                        </p>
                    </div>
                </div>
                <a href="/del/ad/{{ad._id}}" class="text-red-500 font-black text-xs bg-red-50 px-10 py-4 rounded-full hover:bg-red-500 hover:text-white transition shadow-xl shadow-red-100">DISABLE UNIT</a>
            </div>
            {% endfor %}
        </div>
    </div>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block admin_content %}{% endblock %}', content), site=site, ads=ads, is_admin_route=True, active="ads")

@app.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    if not session.get('logged_in'): return redirect('/admin-gate')
    site = get_site_info()
    if request.method == 'POST':
        f_type = request.form.get('type')
        if f_type == "branding":
            settings_col.update_one({"type": "site_info"}, {"$set": {"name": request.form.get('name'), "title": request.form.get('title'), "logo": request.form.get('logo')}}, upsert=True)
            flash("System Lab: Site branding and UI assets have been re-synchronized across the server.")
        elif f_type == "shortener":
            settings_col.update_one({"type": "shortener"}, {"$set": {"url": request.form.get('url'), "api": request.form.get('api')}}, upsert=True)
            flash("Backend Update: External API Gateway and Redirection protocols updated.")
        return redirect('/admin/settings')

    cfg = get_shortener()
    content = """
    <h1 class="text-6xl font-black mb-20 tracking-tighter italic uppercase underline decoration-indigo-200 decoration-8 underline-offset-8">Global Configuration</h1>
    <div class="grid xl:grid-cols-2 gap-20">
        <!-- BRANDING SECTION -->
        <div class="bg-white p-16 rounded-[5rem] border shadow-2xl space-y-12 relative overflow-hidden">
            <div class="absolute top-[-50px] left-[-50px] opacity-[0.03] text-indigo-900 pointer-events-none italic font-black text-[250px]">UI</div>
            <h2 class="text-4xl font-black text-indigo-700 italic border-b-4 border-indigo-50 pb-6 uppercase tracking-tighter relative z-10">Site Identity</h2>
            <form method="POST" class="space-y-10 relative z-10">
                <input type="hidden" name="type" value="branding">
                <div>
                    <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-3 mb-4 block">Platform Display Name</label>
                    <input name="name" value="{{site.name}}" class="w-full font-black text-3xl uppercase tracking-tighter text-indigo-900 bg-slate-50 border-none" required>
                </div>
                <div>
                    <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-3 mb-4 block">SEO Metadata Browser Title</label>
                    <input name="title" value="{{site.title}}" class="w-full font-bold bg-slate-50 border-none" required>
                </div>
                <div>
                    <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-3 mb-4 block">Primary Brand Icon URL (PNG/JPG)</label>
                    <input name="logo" value="{{site.logo}}" class="w-full font-bold bg-slate-50 border-none" required>
                </div>
                <button class="btn-main w-full justify-center py-6 rounded-[2.5rem] font-black text-xl shadow-indigo-100 shadow-2xl">UPDATE SITE ASSETS</button>
            </form>
        </div>
        <!-- API SECTION -->
        <div class="bg-slate-950 p-16 rounded-[5rem] shadow-2xl space-y-12 text-white relative overflow-hidden">
            <div class="absolute top-[-50px] left-[-50px] opacity-10 text-emerald-400 pointer-events-none italic font-black text-[250px]">API</div>
            <h2 class="text-4xl font-black text-emerald-400 italic border-b-4 border-slate-900 pb-6 uppercase tracking-tighter relative z-10 underline decoration-emerald-900 decoration-8">Link Gateway</h2>
            <form method="POST" class="space-y-10 relative z-10">
                <input type="hidden" name="type" value="shortener">
                <div>
                    <label class="text-[10px] font-black text-slate-600 uppercase tracking-widest ml-3 mb-4 block">Shortener API Host Domain</label>
                    <input name="url" value="{{cfg.url}}" placeholder="domain.xyz" class="w-full bg-slate-900 border-2 border-slate-800 text-emerald-400 font-bold text-xl outline-none focus:border-emerald-400 transition shadow-inner" required>
                </div>
                <div>
                    <label class="text-[10px] font-black text-slate-600 uppercase tracking-widest ml-3 mb-4 block">Private API Access Token</label>
                    <input type="password" name="api" value="{{cfg.api}}" placeholder="Enter Secret API Key" class="w-full bg-slate-900 border-2 border-slate-800 text-emerald-400 font-bold outline-none focus:border-emerald-400 transition shadow-inner" required>
                </div>
                <button class="w-full bg-emerald-500 text-slate-950 py-7 rounded-[2.5rem] font-black text-xl uppercase tracking-widest hover:bg-emerald-400 transition shadow-emerald-900 shadow-2xl">CONFIGURE BACKEND REDIRECTION</button>
                <div class="bg-slate-900 p-8 rounded-3xl border border-slate-800">
                    <p class="text-[10px] text-slate-500 font-black leading-relaxed uppercase tracking-widest italic">Note: High-speed secure redirection will be automatically applied to all application download triggers across the platform using SSL encryption protocols.</p>
                </div>
            </form>
        </div>
    </div>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block admin_content %}{% endblock %}', content), site=site, cfg=cfg, is_admin_route=True, active="settings")

@app.route('/forgot', methods=['GET', 'POST'])
def forgot():
    if request.method == 'POST':
        if request.form.get('key') == RECOVERY_KEY:
            users_col.update_one({"username": "admin"}, {"$set": {"password": generate_password_hash(request.form.get('pw'))}}, upsert=True)
            flash("System Protocol: Administrative master password override successful. Please re-authenticate.")
            return redirect('/admin-gate')
        flash("CRITICAL: Unauthorized recovery attempt detected. Key mismatch.")
    
    content = """
    <div class="max-w-xl mx-auto mt-32 bg-white p-20 rounded-[5rem] shadow-2xl border-8 border-red-50 text-center">
        <div class="w-24 h-24 bg-red-600 rounded-[2.5rem] mx-auto mb-10 flex items-center justify-center shadow-2xl shadow-red-200">
            <i class="fas fa-exclamation-triangle text-white text-4xl"></i>
        </div>
        <h2 class="text-4xl font-black mb-10 text-red-600 tracking-tighter uppercase italic underline decoration-red-100 decoration-8 underline-offset-8">Master Reset</h2>
        <form method="POST" class="space-y-8">
            <div>
                <input name="key" placeholder="SYSTEM RECOVERY TOKEN" class="w-full border-none bg-slate-50 p-6 rounded-[2rem] text-center font-black text-lg outline-none focus:ring-4 ring-red-500/10 uppercase" required>
            </div>
            <div>
                <input type="password" name="pw" placeholder="NEW MASTER PASSCODE" class="w-full border-none bg-slate-50 p-6 rounded-[2rem] text-center font-black text-lg outline-none focus:ring-4 ring-red-500/10 uppercase" required>
            </div>
            <button class="bg-red-600 text-white w-full py-7 rounded-[2rem] font-black text-xl shadow-2xl shadow-red-200 hover:bg-slate-900 transition-all uppercase tracking-widest italic">Override Security Credentials</button>
        </form>
    </div>
    """
    return render_template_string(f"<!DOCTYPE html><html lang='en'><head>{BASE_CSS}</head><body class='bg-slate-100'>{content}</body></html>")

@app.route('/del/<type>/<id>')
def delete_entry(type, id):
    if not session.get('logged_in'): return redirect('/admin-gate')
    if type == 'app': apps_col.delete_one({"_id": ObjectId(id)})
    if type == 'ad': ads_col.delete_one({"_id": ObjectId(id)})
    flash("Database Synced: Entry purged permanently from server memory.")
    return redirect(request.referrer)

@app.route('/logout')
def logout():
    session.clear()
    flash("System Note: Administrative session terminated successfully.")
    return redirect('/')

# --- VERCEL DEPLOYMENT EXPORT ---
handler = app

if __name__ == '__main__':
    app.run(debug=True)
