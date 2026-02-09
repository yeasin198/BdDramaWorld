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
app.secret_key = os.environ.get("SESSION_SECRET", "super_high_secure_long_secret_key_v100_final_2024")
RECOVERY_KEY = os.environ.get("RECOVERY_KEY", "admin@2024")

# --- MONGODB CONNECTION (Fixed for Cloud Deployment) ---
try:
    ca = certifi.where()
    # আপনার দেওয়া MongoDB কানেকশন লিঙ্ক
    MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    client = MongoClient(MONGO_URI, tlsCAFile=ca, serverSelectionTimeoutMS=5000)
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

# --- HTML TEMPLATES ---

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
    
    /* স্লাইডার হাইট ছোট করা হয়েছে */
    .swiper { width: 100%; height: 320px; border-radius: 2rem; overflow: hidden; margin-bottom: 3rem; box-shadow: 0 20px 40px -10px rgba(0,0,0,0.3); }
    @media (max-width: 768px) { .swiper { height: 260px; border-radius: 1.5rem; } }

    .line-clamp-2 { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
    .btn-main { background: #6366f1; color: white; padding: 12px 28px; border-radius: 18px; font-weight: 700; transition: 0.3s; display: inline-flex; align-items: center; gap: 8px; box-shadow: 0 4px 14px 0 rgba(99, 102, 241, 0.4); }
    .btn-main:hover { background: #4f46e5; transform: scale(1.05); }
    input, textarea, select { border: 2px solid #f1f5f9; border-radius: 18px; padding: 14px 18px; outline: none; transition: 0.3s; background: #fff; }
    input:focus { border-color: #6366f1; box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.1); }
    .footer-bg { background: #0f172a; color: #94a3b8; }
    
    /* Admin Mobile Sidebar Scroll */
    @media (max-width: 1024px) {
        .admin-sidebar { height: auto !important; position: relative !important; width: 100% !important; }
        .sidebar-links-container { display: flex; overflow-x: auto; padding-bottom: 10px; gap: 10px; }
        .sidebar-link { white-space: nowrap; padding: 10px 15px; }
    }
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
    <nav class="glass-nav h-auto min-h-20 sticky top-0 z-50 py-3">
        <div class="container mx-auto px-6 flex flex-col lg:flex-row items-center justify-between gap-4">
            <div class="flex items-center justify-between w-full lg:w-auto">
                <a href="/" class="flex items-center gap-3">
                    <img src="{{ site.logo }}" class="w-8 h-8 md:w-10 md:h-10 rounded-xl">
                    <span class="text-xl md:text-2xl font-black text-slate-900 tracking-tighter uppercase">{{ site.name }}</span>
                </a>
                <div class="lg:hidden text-[10px] font-black bg-indigo-600 text-white px-3 py-1.5 rounded-full uppercase tracking-widest">v10.0 Pro</div>
            </div>
            
            <!-- মোবাইল ও ডেক্সটপ সার্চ বার (এখন সবসময় দৃশ্যমান) -->
            <div class="flex flex-1 w-full max-w-xl mx-0 lg:mx-12">
                <form action="/" method="GET" class="w-full flex bg-slate-100 rounded-2xl px-5 py-2.5 items-center border border-slate-200">
                    <input type="text" name="q" placeholder="Search apps, games, tools..." class="bg-transparent outline-none text-sm w-full font-medium" value="{{ q }}">
                    <button type="submit"><i class="fas fa-search text-indigo-600"></i></button>
                </form>
            </div>

            <div class="hidden lg:flex items-center gap-4">
                <div class="text-[10px] font-black bg-indigo-600 text-white px-3 py-1.5 rounded-full uppercase tracking-widest">v10.0 Pro</div>
            </div>
        </div>
    </nav>
    {% endif %}

    <div class="{% if is_admin_route %}flex flex-col lg:flex-row min-h-screen{% else %}container mx-auto px-6 py-6 md:py-12{% endif %}">
        {% if is_admin_route %}
        <div class="admin-sidebar w-80 bg-slate-950 text-slate-400 p-8 flex flex-col lg:sticky lg:top-0 lg:h-screen shadow-2xl">
            <div class="flex items-center gap-3 mb-8 lg:mb-12 border-b border-slate-900 pb-6">
                <img src="{{ site.logo }}" class="w-10 h-10 rounded-xl shadow-lg">
                <span class="text-xl font-black text-white uppercase tracking-tighter italic">{{ site.name }}</span>
            </div>
            <div class="sidebar-links-container flex-1 space-y-0 lg:space-y-3">
                <a href="/admin/dashboard" class="sidebar-link {% if active == 'dashboard' %}sidebar-active{% endif %}"><i class="fas fa-chart-line"></i> Dashboard</a>
                <a href="/admin/apps" class="sidebar-link {% if active == 'apps' %}sidebar-active{% endif %}"><i class="fas fa-cube"></i> Apps</a>
                <a href="/admin/ads" class="sidebar-link {% if active == 'ads' %}sidebar-active{% endif %}"><i class="fas fa-ad"></i> Ads</a>
                <a href="/admin/settings" class="sidebar-link {% if active == 'settings' %}sidebar-active{% endif %}"><i class="fas fa-sliders-h"></i> Settings</a>
            </div>
            <div class="pt-6 lg:pt-8 border-t border-slate-900 flex flex-row lg:flex-col gap-4 mt-4 lg:mt-0">
                <a href="/" class="text-emerald-400 font-black flex items-center gap-3 text-xs md:text-sm"><i class="fas fa-external-link-alt"></i> OPEN SITE</a>
                <a href="/logout" class="text-red-500 font-black flex items-center gap-3 text-xs md:text-sm"><i class="fas fa-power-off"></i> LOGOUT</a>
            </div>
        </div>
        <div class="flex-1 bg-white p-6 md:p-12 overflow-y-auto">
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
    <footer class="footer-bg py-16 md:py-20 mt-10 md:mt-20">
        <div class="container mx-auto px-6 grid grid-cols-1 md:grid-cols-3 gap-16">
            <div>
                <h3 class="text-white text-2xl font-black mb-6 uppercase">{{ site.name }}</h3>
                <p class="text-sm leading-relaxed mb-8">Ultimate platform for high-performance applications. Discover, search and download your favorite tools with maximum speed and security.</p>
                <div class="flex gap-4">
                    <div class="w-10 h-10 bg-slate-900 rounded-full flex items-center justify-center hover:bg-indigo-600 transition cursor-pointer"><i class="fab fa-facebook-f text-white"></i></div>
                    <div class="w-10 h-10 bg-slate-900 rounded-full flex items-center justify-center hover:bg-indigo-600 transition cursor-pointer"><i class="fab fa-twitter text-white"></i></div>
                    <div class="w-10 h-10 bg-slate-900 rounded-full flex items-center justify-center hover:bg-indigo-600 transition cursor-pointer"><i class="fab fa-instagram text-white"></i></div>
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
    {% if featured %}
    <div class="swiper mb-10 md:mb-16 shadow-2xl">
        <div class="swiper-wrapper">
            {% for f in featured %}
            <div class="swiper-slide hero-gradient relative flex items-center p-6 md:p-12 lg:p-20 text-white overflow-hidden">
                <div class="absolute inset-0 bg-indigo-950 opacity-20 z-0"></div>
                <div class="relative z-10 max-w-2xl">
                    <span class="bg-indigo-500 text-[8px] md:text-[10px] font-black px-4 py-1.5 rounded-full uppercase mb-4 md:mb-6 inline-block tracking-widest shadow-xl">Top Featured Choice</span>
                    <h2 class="text-3xl md:text-5xl lg:text-6xl font-black mb-4 md:mb-6 leading-tight tracking-tighter uppercase italic">{{ f.name }}</h2>
                    <p class="text-indigo-100 text-xs md:text-base lg:text-lg mb-6 md:mb-10 line-clamp-2 opacity-80 font-medium leading-relaxed">{{ f.info }}</p>
                    <div class="flex flex-wrap gap-4">
                        <a href="/app/{{f._id}}" class="bg-white text-indigo-900 px-6 py-3 md:px-10 md:py-4 rounded-2xl md:rounded-3xl font-black text-xs md:text-lg shadow-2xl hover:scale-105 transition transform flex items-center gap-2">
                            <i class="fas fa-info-circle"></i> EXPLORE DETAILS
                        </a>
                    </div>
                </div>
                <div class="absolute right-[-30px] top-1/2 -translate-y-1/2 hidden lg:block rotate-12 transition duration-1000">
                    <img src="{{f.logo}}" class="w-[300px] h-[300px] rounded-[4rem] shadow-2xl border-[15px] border-white/10 opacity-60">
                </div>
            </div>
            {% endfor %}
        </div>
        <div class="swiper-pagination"></div>
    </div>
    {% endif %}

    <div class="max-w-4xl mx-auto mb-10 md:mb-16 space-y-6">
        {% for ad in ads %}
        <div class="bg-white p-4 md:p-6 rounded-3xl border-2 border-slate-100 shadow-sm flex justify-center items-center overflow-hidden min-h-[80px]">
            {{ ad.code | safe }}
        </div>
        {% endfor %}
    </div>

    <div class="flex flex-col md:flex-row items-center justify-between mb-8 md:mb-12 gap-6">
        <div>
            <h2 class="text-2xl md:text-4xl font-black text-slate-900 tracking-tighter uppercase italic">
                {% if q %}SEARCH RESULTS: "{{q}}"{% else %}LATEST DISCOVERIES{% endif %}
            </h2>
            <p class="text-slate-400 font-bold uppercase text-[8px] md:text-[10px] tracking-widest mt-1">Verified Premium Applications</p>
        </div>
        <span class="bg-indigo-50 text-indigo-600 px-6 py-2 rounded-full font-black text-xs border border-indigo-100 uppercase tracking-widest">
            {{ apps|length }} APPS FOUND
        </span>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8 md:gap-12">
        {% for app in apps %}
        <a href="/app/{{app._id}}" class="pro-card p-6 md:p-10 group text-center flex flex-col items-center">
            <div class="relative mb-6 md:mb-8">
                <div class="absolute inset-0 bg-indigo-600 rounded-[3rem] blur-2xl opacity-0 group-hover:opacity-20 transition duration-500"></div>
                <img src="{{app.logo}}" class="w-24 h-24 md:w-32 md:h-32 rounded-[2.5rem] md:rounded-[3rem] shadow-2xl relative z-10 group-hover:scale-110 transition duration-500 border-4 border-white">
                {% if app.featured == 'on' %}
                <div class="absolute -top-3 -right-3 bg-orange-500 text-white text-[9px] font-black px-3 py-1 rounded-full shadow-xl z-20 animate-bounce">PRO</div>
                {% endif %}
            </div>
            <h3 class="font-black text-xl md:text-2xl text-slate-800 mb-3 tracking-tighter line-clamp-1 uppercase">{{app.name}}</h3>
            <div class="flex gap-2 mb-4 md:mb-6 font-black uppercase text-[9px] tracking-widest">
                <span class="bg-indigo-50 text-indigo-600 px-3 py-1 rounded-full border border-indigo-100">{{app.category}}</span>
                <span class="bg-slate-100 text-slate-500 px-3 py-1 rounded-full">V {{app.version}}</span>
            </div>
            <p class="text-xs text-slate-400 line-clamp-2 h-10 mb-6 md:mb-8 leading-relaxed font-semibold italic">{{app.info}}</p>
            <div class="btn-main w-full justify-center py-4 bg-slate-900 group-hover:bg-indigo-600 shadow-xl text-sm md:text-base">
                DOWNLOAD NOW <i class="fas fa-bolt"></i>
            </div>
        </a>
        {% endfor %}
    </div>

    {% if not apps %}
    <div class="py-20 md:py-40 text-center">
        <i class="fas fa-search text-7xl md:text-9xl text-slate-200 mb-8"></i>
        <h3 class="text-2xl md:text-3xl font-black text-slate-400 uppercase tracking-tighter">No Applications Found</h3>
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
        <div class="bg-white rounded-[2.5rem] md:rounded-[4rem] shadow-2xl p-6 md:p-10 lg:p-20 flex flex-col md:flex-row md:gap-10 lg:gap-20 items-center border border-slate-100 relative overflow-hidden">
            <div class="absolute -top-20 -right-20 p-20 opacity-[0.03] text-indigo-950 pointer-events-none rotate-12">
                <i class="fas fa-download text-[300px] md:text-[500px]"></i>
            </div>
            
            <div class="relative z-10 flex-shrink-0 mb-8 md:mb-0">
                <img src="{{app.logo}}" class="w-48 h-48 md:w-64 lg:w-80 md:h-64 lg:h-80 rounded-[3rem] md:rounded-[5rem] shadow-2xl border-[10px] md:border-[15px] border-slate-50">
                <div class="absolute -bottom-4 -right-4 md:-bottom-8 md:-right-8 bg-emerald-500 text-white p-6 md:p-10 rounded-full shadow-2xl border-4 md:border-8 border-white">
                    <i class="fas fa-shield-halved text-2xl md:text-4xl"></i>
                </div>
            </div>
            
            <div class="flex-1 text-center md:text-left z-10">
                <div class="flex flex-wrap gap-2 md:gap-4 mb-6 md:mb-8 justify-center md:justify-start">
                    <span class="bg-indigo-600 text-white px-5 md:px-8 py-2 md:py-2.5 rounded-full font-black text-[9px] md:text-xs uppercase tracking-widest shadow-lg">{{app.category}}</span>
                    <span class="bg-emerald-50 text-emerald-600 px-5 md:px-8 py-2 md:py-2.5 rounded-full font-black text-[9px] md:text-xs uppercase tracking-widest border border-emerald-100">Version {{app.version}}</span>
                </div>
                
                <h1 class="text-4xl md:text-5xl lg:text-7xl font-black text-slate-950 mb-6 md:mb-10 leading-none tracking-tighter italic uppercase underline decoration-indigo-200 decoration-4 md:decoration-8 underline-offset-[10px]">{{app.name}}</h1>
                <p class="text-slate-500 text-lg md:text-2xl font-medium leading-relaxed mb-8 md:mb-12 opacity-90 italic">"{{app.info}}"</p>
                
                <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 md:gap-8 mb-10 md:mb-16">
                    <div class="bg-slate-50 p-6 md:p-8 rounded-[2rem] md:rounded-[2.5rem] border border-slate-200">
                        <p class="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-2">Publish Date</p>
                        <p class="font-black text-slate-800 text-lg md:text-xl tracking-tighter uppercase">{{app.release_date}}</p>
                    </div>
                    <div class="bg-slate-50 p-6 md:p-8 rounded-[2rem] md:rounded-[2.5rem] border border-slate-200">
                        <p class="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-2">Category</p>
                        <p class="font-black text-indigo-600 text-lg md:text-xl tracking-tighter uppercase">{{app.category}}</p>
                    </div>
                    <div class="bg-emerald-50 p-6 md:p-8 rounded-[2rem] md:rounded-[2.5rem] border border-emerald-100 hidden sm:block">
                        <p class="text-[9px] font-black text-emerald-400 uppercase tracking-widest mb-2">Status</p>
                        <p class="font-black text-emerald-600 text-lg md:text-xl tracking-tighter uppercase">Verified Safe</p>
                    </div>
                </div>

                <a href="/get/{{app._id}}" class="inline-flex items-center gap-4 md:gap-6 bg-slate-900 text-white px-10 py-5 md:px-20 md:py-8 rounded-full font-black text-xl md:text-3xl shadow-2xl hover:bg-indigo-700 hover:scale-105 transition transform shadow-indigo-200">
                    <i class="fas fa-cloud-arrow-down animate-bounce"></i> DOWNLOAD
                </a>
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
            api_endpoint = f"https://{cfg['url']}/api?api={cfg['api']}&url={target}"
            res = requests.get(api_endpoint, timeout=12).json()
            short_url = res.get('shortenedUrl') or res.get('shortedUrl')
            if short_url: return redirect(short_url)
        except Exception as e:
            print(f"SHORTENER ERROR: {e}")
            
    return redirect(target)

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
    <div class="max-w-lg mx-auto mt-20 md:mt-32 bg-white p-10 md:p-20 rounded-[3rem] md:rounded-[5rem] shadow-2xl border-4 border-slate-50 text-center">
        <div class="w-20 h-20 md:w-24 md:h-24 bg-indigo-600 rounded-[2rem] md:rounded-[2.5rem] mx-auto mb-8 md:mb-10 flex items-center justify-center shadow-2xl shadow-indigo-200">
            <i class="fas fa-user-shield text-white text-3xl md:text-4xl"></i>
        </div>
        <h2 class="text-2xl md:text-4xl font-black mb-8 md:mb-10 text-slate-900 tracking-tighter uppercase italic underline decoration-indigo-100 underline-offset-8">Admin Auth</h2>
        <form method="POST" class="space-y-6 md:space-y-8">
            <input type="password" name="password" placeholder="ACCESS CODE" class="w-full bg-slate-50 p-5 md:p-6 rounded-[1.5rem] md:rounded-[2rem] text-center outline-none border-2 border-slate-100 focus:border-indigo-500 transition-all font-black text-xl md:text-2xl tracking-widest uppercase" required>
            <button class="bg-indigo-600 text-white w-full py-5 md:py-6 rounded-[1.5rem] md:rounded-[2rem] font-black text-lg md:text-xl shadow-2xl shadow-indigo-100 hover:bg-slate-900 transition-all uppercase tracking-widest">Authenticate Access</button>
        </form>
        <div class="mt-10 pt-8 border-t border-slate-50"><a href="/forgot" class="text-[10px] font-bold text-slate-300 hover:text-red-500 uppercase tracking-widest transition">System Override Tool</a></div>
    </div>
    """
    return render_template_string(f"<!DOCTYPE html><html lang='en'><head>{BASE_CSS}</head><body class='bg-slate-100 px-6'>{content}</body></html>")

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
    <div class="mb-10 md:mb-16">
        <h1 class="text-4xl md:text-6xl font-black text-slate-950 tracking-tighter mb-4 uppercase italic">Overview</h1>
        <p class="text-slate-400 font-black uppercase tracking-widest text-[10px] ml-1">Platform Performance & Statistics</p>
    </div>
    
    <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6 md:gap-12 mb-12 md:mb-20">
        <div class="bg-indigo-600 p-8 md:p-12 rounded-[2.5rem] md:rounded-[4rem] text-white shadow-2xl shadow-indigo-200 flex flex-col justify-between h-64 md:h-80 relative overflow-hidden group">
            <i class="fas fa-cube absolute right-[-40px] bottom-[-40px] text-[150px] md:text-[200px] opacity-10 rotate-12 group-hover:rotate-0 transition duration-1000"></i>
            <div class="text-6xl md:text-8xl font-black tracking-tighter">{{ stats.apps }}</div>
            <div>
                <p class="font-black uppercase tracking-widest text-[10px] opacity-70">Total Applications</p>
                <h4 class="text-lg md:text-xl font-bold">Synchronized</h4>
            </div>
        </div>
        <div class="bg-slate-950 p-8 md:p-12 rounded-[2.5rem] md:rounded-[4rem] text-white shadow-2xl shadow-slate-200 flex flex-col justify-between h-64 md:h-80 relative overflow-hidden group border-4 border-slate-900">
            <i class="fas fa-ad absolute right-[-40px] bottom-[-40px] text-[150px] md:text-[200px] opacity-10 rotate-12 group-hover:rotate-0 transition duration-1000"></i>
            <div class="text-6xl md:text-8xl font-black tracking-tighter">{{ stats.ads }}</div>
            <div>
                <p class="font-black uppercase tracking-widest text-[10px] opacity-70">Active Ad Units</p>
                <h4 class="text-lg md:text-xl font-bold">Monetization Active</h4>
            </div>
        </div>
        <div class="bg-orange-500 p-8 md:p-12 rounded-[2.5rem] md:rounded-[4rem] text-white shadow-2xl shadow-orange-100 flex flex-col justify-between h-64 md:h-80 relative overflow-hidden group">
            <i class="fas fa-star absolute right-[-40px] bottom-[-40px] text-[150px] md:text-[200px] opacity-10 rotate-12 group-hover:rotate-0 transition duration-1000"></i>
            <div class="text-6xl md:text-8xl font-black tracking-tighter">{{ stats.featured }}</div>
            <div>
                <p class="font-black uppercase tracking-widest text-[10px] opacity-70">Slider Highlights</p>
                <h4 class="text-lg md:text-xl font-bold">Featured Home</h4>
            </div>
        </div>
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
    <div class="flex flex-col xl:flex-row justify-between items-start xl:items-center mb-10 md:mb-16 gap-6 md:gap-10">
        <h1 class="text-4xl md:text-6xl font-black tracking-tighter italic uppercase underline decoration-indigo-200 decoration-8">Content Lab</h1>
        <form class="bg-slate-100 px-6 md:px-10 py-3 md:py-4 rounded-full border-2 border-slate-200 flex items-center w-full xl:w-[500px] focus-within:border-indigo-600 transition shadow-inner">
            <input type="text" name="q" placeholder="Global search apps..." class="bg-transparent outline-none text-sm md:text-lg w-full font-black text-slate-700 uppercase" value="{{q}}">
            <button type="submit"><i class="fas fa-search text-indigo-600 text-lg md:text-xl"></i></button>
        </form>
    </div>

    <div class="grid xl:grid-cols-12 gap-10 md:gap-16">
        <div class="xl:col-span-4 bg-white p-8 md:p-12 rounded-[2.5rem] md:rounded-[4rem] shadow-2xl border-2 border-slate-50 h-fit lg:sticky lg:top-28">
            <h2 class="text-2xl md:text-3xl font-black mb-8 md:mb-10 text-indigo-700 italic border-b pb-6 uppercase tracking-tighter">Publish Content</h2>
            <form method="POST" class="space-y-4 md:space-y-6">
                <div>
                    <label class="text-[9px] font-black text-slate-400 uppercase tracking-widest ml-2 mb-2 block">Application Title</label>
                    <input name="name" placeholder="Enter Full Name" class="w-full font-bold text-base md:text-lg" required>
                </div>
                <div>
                    <label class="text-[9px] font-black text-slate-400 uppercase tracking-widest ml-2 mb-2 block">Logo Resource URL</label>
                    <input name="logo" placeholder="Direct Link to Icon" class="w-full text-sm md:text-base" required>
                </div>
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="text-[9px] font-black text-slate-400 uppercase tracking-widest ml-2 mb-2 block">Release Date</label>
                        <input type="date" name="release_date" class="w-full text-sm md:text-base" required>
                    </div>
                    <div>
                        <label class="text-[9px] font-black text-slate-400 uppercase tracking-widest ml-2 mb-2 block">Version</label>
                        <input name="version" placeholder="v1.0.0" class="w-full font-black text-sm md:text-base" required>
                    </div>
                </div>
                <div>
                    <label class="text-[9px] font-black text-slate-400 uppercase tracking-widest ml-2 mb-2 block">Target Platform</label>
                    <select name="category" class="w-full font-bold uppercase tracking-widest text-xs">
                        <option>Mobile (Android)</option><option>iOS (Apple)</option><option>Desktop (PC)</option>
                    </select>
                </div>
                <div>
                    <label class="text-[9px] font-black text-slate-400 uppercase tracking-widest ml-2 mb-2 block">Meta Description</label>
                    <textarea name="info" placeholder="Detailed app info..." class="w-full h-24 md:h-32 leading-relaxed font-medium text-sm md:text-base" required></textarea>
                </div>
                <div>
                    <label class="text-[9px] font-black text-slate-400 uppercase tracking-widest ml-2 mb-2 block">Redirect URL</label>
                    <input name="download_link" placeholder="Final Link" class="w-full text-sm md:text-base" required>
                </div>
                <label class="flex items-center gap-4 font-black text-indigo-700 bg-indigo-50 p-4 md:p-6 rounded-2xl md:rounded-3xl cursor-pointer hover:bg-indigo-100 transition">
                    <input type="checkbox" name="featured" class="w-6 h-6 rounded-xl accent-indigo-600"> 
                    <span class="uppercase tracking-tighter text-[10px] md:text-sm">Home Slider</span>
                </label>
                <button class="btn-main w-full justify-center py-5 md:py-6 rounded-[2rem] md:rounded-[2.5rem] uppercase font-black text-lg md:text-xl tracking-widest italic shadow-indigo-200 shadow-2xl">PUBLISH ASSET</button>
            </form>
        </div>
        <div class="xl:col-span-8 bg-white rounded-[2.5rem] md:rounded-[4rem] border-4 border-slate-50 overflow-hidden shadow-2xl overflow-x-auto">
            <table class="w-full text-left min-w-[500px]">
                <thead class="bg-slate-900 text-white">
                    <tr><th class="p-6 md:p-8 font-black uppercase text-[10px] tracking-[0.3em]">Identity Details</th><th class="p-6 md:p-8 text-right font-black uppercase text-[10px] tracking-[0.3em]">Operations</th></tr>
                </thead>
                <tbody>
                    {% for a in apps %}
                    <tr class="border-b border-slate-50 hover:bg-indigo-50/30 transition duration-500 group">
                        <td class="p-6 md:p-8 flex items-center gap-4 md:gap-8">
                            <img src="{{a.logo}}" class="w-14 h-14 md:w-20 md:h-20 rounded-[1.5rem] md:rounded-[2.5rem] shadow-2xl object-cover border-4 border-white">
                            <div>
                                <p class="font-black text-slate-950 text-xl md:text-2xl tracking-tighter mb-1 uppercase italic leading-none group-hover:text-indigo-600 transition">{{a.name}}</p>
                                <span class="text-[8px] font-black bg-indigo-600 text-white px-2 py-0.5 rounded-full uppercase">{{a.category}}</span>
                            </div>
                        </td>
                        <td class="p-6 md:p-8 text-right">
                            <a href="/del/app/{{a._id}}" class="text-red-500 font-black text-[10px] bg-red-50 px-6 md:px-10 py-3 md:py-4 rounded-[1.5rem] md:rounded-[2rem] hover:bg-red-500 hover:text-white transition" onclick="return confirm('Delete this asset?')">REMOVE</a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
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
        flash("Ad unit integrated successfully.")
        return redirect('/admin/ads')
    
    ads_list = list(ads_col.find())
    content = """
    <h1 class="text-4xl md:text-6xl font-black mb-10 md:mb-16 tracking-tighter italic uppercase">Monetization Hub</h1>
    <div class="grid lg:grid-cols-12 gap-8 md:gap-16">
        <div class="lg:col-span-5 bg-white p-8 md:p-12 rounded-[2.5rem] md:rounded-[4rem] border-2 border-slate-50 shadow-2xl h-fit">
            <form method="POST" class="space-y-6">
                <input name="name" placeholder="Ad Unit Name" class="w-full text-sm md:text-base" required>
                <textarea name="code" placeholder="Paste script code here..." class="w-full h-60 md:h-80 text-sm md:text-base" required></textarea>
                <button class="btn-main w-full justify-center py-5 md:py-6 text-base md:text-xl">DEPLOY AD UNIT</button>
            </form>
        </div>
        <div class="lg:col-span-7 space-y-6 md:space-y-8">
            {% for ad in ads %}
            <div class="flex justify-between items-center p-6 md:p-10 bg-white border-2 border-slate-50 rounded-[2rem] md:rounded-[3rem] shadow-sm">
                <p class="font-black text-slate-950 text-xl md:text-3xl line-clamp-1">{{ ad.name }}</p>
                <a href="/del/ad/{{ad._id}}" class="text-red-500 font-black text-xs md:text-sm whitespace-nowrap">DISABLE</a>
            </div>
            {% endfor %}
        </div>
    </div>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block admin_content %}{% endblock %}', content), site=site, ads=ads_list, is_admin_route=True, active="ads")

@app.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    if not session.get('logged_in'): return redirect('/admin-gate')
    site = get_site_info()
    if request.method == 'POST':
        f_type = request.form.get('type')
        if f_type == "branding":
            settings_col.update_one({"type": "site_info"}, {"$set": {"name": request.form.get('name'), "title": request.form.get('title'), "logo": request.form.get('logo')}}, upsert=True)
        elif f_type == "shortener":
            settings_col.update_one({"type": "shortener"}, {"$set": {"url": request.form.get('url'), "api": request.form.get('api')}}, upsert=True)
        flash("Settings updated.")
        return redirect('/admin/settings')

    cfg = get_shortener()
    content = """
    <h1 class="text-4xl md:text-6xl font-black mb-10 md:mb-20 tracking-tighter italic uppercase">Configuration</h1>
    <div class="grid xl:grid-cols-2 gap-10 md:gap-20">
        <div class="bg-white p-8 md:p-16 rounded-[3rem] md:rounded-[5rem] border shadow-2xl">
            <h3 class="font-black mb-8 text-indigo-600 uppercase">Site Branding</h3>
            <form method="POST" class="space-y-6 md:space-y-10">
                <input type="hidden" name="type" value="branding">
                <input name="name" value="{{site.name}}" class="w-full text-sm md:text-base" placeholder="Site Name">
                <input name="title" value="{{site.title}}" class="w-full text-sm md:text-base" placeholder="Site Title">
                <input name="logo" value="{{site.logo}}" class="w-full text-sm md:text-base" placeholder="Logo URL">
                <button class="btn-main w-full justify-center py-5 md:py-6 text-base md:text-xl">UPDATE BRANDING</button>
            </form>
        </div>
        <div class="bg-slate-950 p-8 md:p-16 rounded-[3rem] md:rounded-[5rem] text-white">
            <h3 class="font-black mb-8 text-emerald-400 uppercase">URL Shortener (API)</h3>
            <form method="POST" class="space-y-6 md:space-y-10">
                <input type="hidden" name="type" value="shortener">
                <input name="url" value="{{cfg.url}}" placeholder="domain.xyz" class="w-full bg-slate-900 border-slate-800 text-sm md:text-base text-white">
                <input name="api" value="{{cfg.api}}" placeholder="API Key" class="w-full bg-slate-900 border-slate-800 text-sm md:text-base text-white">
                <button class="w-full bg-emerald-500 py-5 md:py-6 rounded-[1.5rem] md:rounded-[2rem] text-black font-black text-base md:text-xl">UPDATE API</button>
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
            flash("Password updated.")
            return redirect('/admin-gate')
    content = """
    <div class="max-w-xl mx-auto mt-20 md:mt-32 bg-white p-10 md:p-20 rounded-[3rem] md:rounded-[5rem] shadow-2xl text-center">
        <form method="POST" class="space-y-6 md:space-y-8">
            <input name="key" placeholder="RECOVERY TOKEN" class="w-full p-5 rounded-2xl border-2 border-slate-100" required>
            <input type="password" name="pw" placeholder="NEW PASSWORD" class="w-full p-5 rounded-2xl border-2 border-slate-100" required>
            <button class="bg-red-600 text-white w-full py-5 md:py-7 rounded-[1.5rem] md:rounded-[2rem] font-black uppercase">RESET NOW</button>
        </form>
    </div>
    """
    return render_template_string(f"<!DOCTYPE html><html><head>{BASE_CSS}</head><body class='bg-slate-100 px-6'>{content}</body></html>")

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

# --- DEPLOYMENT HANDLER ---
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
