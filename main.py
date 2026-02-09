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
app.secret_key = os.environ.get("SESSION_SECRET", "super_high_secure_long_secret_key_ultimate_v2024")
RECOVERY_KEY = os.environ.get("RECOVERY_KEY", "admin@2024")

# --- MONGODB CONNECTION ---
try:
    ca = certifi.where()
    MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    client = MongoClient(MONGO_URI, tlsCAFile=ca, serverSelectionTimeoutMS=5000)
    db = client['app_hub_production_ultimate_system']
    
    apps_col = db['apps']
    users_col = db['users']
    ads_col = db['ads']
    settings_col = db['settings']
    categories_col = db['categories']
    badges_col = db['badges'] 
    versions_col = db['versions'] # New Collection for App Versions
    media_col = db['media']
    
except Exception as e:
    print(f"DATABASE CONNECTION ERROR: {e}")

# --- HELPERS: DYNAMIC DATA ---
def get_site_info():
    info = settings_col.find_one({"type": "site_info"})
    if not info:
        return {
            "name": "APPHUB PRO", 
            "title": "Ultimate Premium App Store", 
            "logo": "https://cdn-icons-png.flaticon.com/512/2589/2589127.png",
            "desc": "The ultimate platform for high-performance applications and games. Discover and download with maximum speed.",
            "copyright": "2024 APPHUB PRO Ultimate Edition v10.0",
            "fb": "#", "ig": "#", "tw": "#"
        }
    return info

def get_shortener():
    return settings_col.find_one({"type": "shortener"}) or {"url": "", "api": ""}

def get_legal_content(page_type):
    content = settings_col.find_one({"type": "legal_page", "page": page_type})
    if not content: return f"The {page_type} content is not set yet. Please update from admin panel."
    return content['text']

# --- NEW HELPER: FETCH ALL ADS ---
def get_ads():
    all_ads = list(ads_col.find())
    ad_map = {}
    for ad in all_ads:
        ad_map[ad['name']] = ad['code']
    return ad_map

# --- UI ASSETS (CSS & SCRIPTS) ---
BASE_CSS = """
<script src="https://cdn.tailwindcss.com"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.css" />
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    
    :root { --bg: #f8fafc; --text: #0f172a; --card: #ffffff; --border: #e2e8f0; --glass: rgba(255, 255, 255, 0.9); --title: #1e293b; }
    .dark-mode { --bg: #0f172a; --text: #f8fafc; --card: #1e293b; --border: #334155; --glass: rgba(15, 23, 42, 0.9); --title: #ffffff; }

    body { font-family: 'Plus Jakarta Sans', sans-serif; background-color: var(--bg); color: var(--text); overflow-x: hidden; transition: 0.3s ease; }
    .glass-nav { background: var(--glass); backdrop-filter: blur(12px); border-bottom: 1px solid var(--border); }
    
    .pro-card { background: var(--card); border: 1px solid var(--border); border-radius: 2rem; transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1); position: relative; overflow: hidden; }
    .pro-card:hover { transform: translateY(-8px); box-shadow: 0 25px 50px -12px rgba(99, 102, 241, 0.2); border-color: #6366f1; }
    
    /* POSTER BADGE */
    .app-badge { position: absolute; top: 12px; right: 12px; background: #6366f1; color: white !important; padding: 4px 12px; border-radius: 8px; font-size: 10px; font-weight: 800; z-index: 10; text-transform: uppercase; box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3); }

    .sidebar-link { display: flex; align-items: center; gap: 12px; padding: 14px 20px; border-radius: 18px; font-weight: 600; color: #94a3b8; transition: 0.3s; }
    .sidebar-active { background: #6366f1 !important; color: white !important; box-shadow: 0 10px 20px -5px rgba(99, 102, 241, 0.4); }
    .btn-main { background: #6366f1; color: white !important; padding: 12px 28px; border-radius: 18px; font-weight: 800; display: inline-flex; align-items: center; gap: 8px; transition: 0.3s; }
    
    input, textarea, select { border: 2px solid var(--border); border-radius: 18px; padding: 14px 18px; outline: none; background: var(--card); color: var(--text); width: 100%; transition: 0.3s; }
    input:focus { border-color: #6366f1; }
    
    .swiper { width: 100%; border-radius: 2.5rem; height: 350px; margin-bottom: 3rem; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.2); }
    @media (min-width: 768px) { .swiper { height: 450px; } }
    .swiper-slide img { width: 100%; height: 100%; object-fit: cover; border-radius: 2.5rem; }
    
    .text-title { color: var(--title); }
    .line-clamp-1 { display: -webkit-box; -webkit-line-clamp: 1; -webkit-box-orient: vertical; overflow: hidden; }
    
    /* Translator Styles Hidden */
    #google_translate_element { display: none; }
    .goog-te-banner-frame.skiptranslate { display: none !important; }
    body { top: 0px !important; }

    /* AD SLOT WRAPPER */
    .ad-slot-wrapper { display: flex; justify-content: center; align-items: center; margin: 25px 0; overflow: hidden; width: 100%; }
</style>
"""

BASE_LAYOUT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ site.name }} - {{ site.title }}</title>
    """ + BASE_CSS + """
    
    {# Global Ads: Popunder / Social Bar (Head) #}
    {{ ads['GlobalHeader'] | safe if ads and 'GlobalHeader' in ads }}
    {{ ads['Popunder'] | safe if ads and 'Popunder' in ads }}
    {{ ads['SocialBar'] | safe if ads and 'SocialBar' in ads }}

</head>
<body id="pageBody">
    {% if not is_admin_route %}
    <nav class="glass-nav sticky top-0 z-50 py-4">
        <div class="container mx-auto px-6 flex flex-col lg:flex-row items-center justify-between gap-4">
            <div class="flex items-center justify-between w-full lg:w-auto">
                <a href="/" class="flex items-center gap-3">
                    <img src="{{ site.logo }}" class="w-10 h-10 rounded-xl shadow-lg">
                    <span class="text-2xl font-black text-title tracking-tighter uppercase italic">{{ site.name }}</span>
                </a>
                <div class="flex items-center gap-4 lg:hidden">
                     <button onclick="toggleTheme()" class="w-10 h-10 rounded-xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-indigo-600"><i id="themeIconMobile" class="fas fa-moon"></i></button>
                </div>
            </div>

            <div class="flex items-center gap-4 w-full max-w-2xl">
                <form action="/" method="GET" class="flex bg-slate-100 dark:bg-slate-800 rounded-2xl px-5 py-2 w-full border border-slate-200 dark:border-slate-700">
                    <input type="text" name="q" placeholder="Search apps, games, tools..." class="bg-transparent border-none p-0 w-full text-sm font-semibold outline-none text-slate-800 dark:text-white" value="{{ q if q }}">
                    <button type="submit"><i class="fas fa-search text-indigo-600 text-lg"></i></button>
                </form>
                
                <button onclick="toggleTheme()" class="hidden lg:flex w-12 h-11 rounded-2xl bg-slate-100 dark:bg-slate-800 items-center justify-center text-indigo-600 border border-slate-200 dark:border-slate-700 transition">
                    <i id="themeIcon" class="fas fa-moon"></i>
                </button>
            </div>
        </div>
    </nav>
    
    {# Banner 728x90 or 320x50 (Top) #}
    <div class="ad-slot-wrapper">
        {{ ads['TopBanner_728x90'] | safe if ads and 'TopBanner_728x90' in ads }}
    </div>
    {% endif %}

    <div class="{% if is_admin_route %}flex flex-col lg:flex-row min-h-screen{% else %}container mx-auto px-6 py-10{% endif %}">
        {% if is_admin_route %}
        <div class="w-full lg:w-80 bg-slate-950 text-slate-400 p-8 flex flex-col lg:h-screen lg:sticky lg:top-0">
            <div class="flex items-center gap-4 mb-10 border-b border-slate-900 pb-8">
                <img src="{{ site.logo }}" class="w-10 h-10 rounded-xl">
                <div>
                    <h2 class="text-white font-black uppercase text-xl italic leading-none">{{ site.name }}</h2>
                    <span class="text-[10px] font-bold text-indigo-400 tracking-[0.2em]">ADMIN PANEL</span>
                </div>
            </div>
            <div class="space-y-2 flex-1 overflow-y-auto pr-2">
                <a href="/admin/dashboard" class="sidebar-link {% if active == 'dashboard' %}sidebar-active{% endif %}"><i class="fas fa-chart-line"></i> Dashboard</a>
                <a href="/admin/categories" class="sidebar-link {% if active == 'categories' %}sidebar-active{% endif %}"><i class="fas fa-tags"></i> Categories</a>
                <a href="/admin/badges" class="sidebar-link {% if active == 'badges' %}sidebar-active{% endif %}"><i class="fas fa-certificate"></i> Poster Badges</a>
                <a href="/admin/versions" class="sidebar-link {% if active == 'versions' %}sidebar-active{% endif %}"><i class="fas fa-code-branch"></i> App Versions</a>
                <a href="/admin/apps" class="sidebar-link {% if active == 'apps' %}sidebar-active{% endif %}"><i class="fas fa-rocket"></i> Apps Manager</a>
                <a href="/admin/media" class="sidebar-link {% if active == 'media' %}sidebar-active{% endif %}"><i class="fas fa-photo-video"></i> Media Center</a>
                <a href="/admin/ads" class="sidebar-link {% if active == 'ads' %}sidebar-active{% endif %}"><i class="fas fa-ad"></i> Ads Manager</a>
                <a href="/admin/layout" class="sidebar-link {% if active == 'layout' %}sidebar-active{% endif %}"><i class="fas fa-window-restore"></i> Site Layout</a>
                <a href="/admin/settings" class="sidebar-link {% if active == 'settings' %}sidebar-active{% endif %}"><i class="fas fa-user-shield"></i> Settings</a>
            </div>
            <div class="mt-8 pt-6 border-t border-slate-900">
                <a href="/" target="_blank" class="text-emerald-400 font-black block mb-5 flex items-center gap-3"><i class="fas fa-external-link-alt"></i> VIEW SITE</a>
                <a href="/logout" class="text-red-500 font-black flex items-center gap-3"><i class="fas fa-power-off"></i> LOGOUT SYSTEM</a>
            </div>
        </div>
        <div class="flex-1 p-6 lg:p-12 bg-white dark:bg-slate-900 transition-colors duration-300">
            {% with messages = get_flashed_messages() %}{% if messages %}{% for m in messages %}
            <div class="bg-indigo-600 text-white p-5 rounded-3xl mb-10 shadow-xl flex justify-between items-center animate-bounce">
                <span class="font-bold"><i class="fas fa-check-circle mr-2"></i> {{ m }}</span>
                <button onclick="this.parentElement.remove()"><i class="fas fa-times"></i></button>
            </div>
            {% endfor %}{% endif %}{% endwith %}
            {% block admin_content %}{% endblock %}
        </div>
        {% else %}
        <div class="min-h-[80vh]">
            {% block content %}{% endblock %}
        </div>
        {% endif %}
    </div>

    {% if not is_admin_route %}
    {# Bottom Banner Ad Slot #}
    <div class="ad-slot-wrapper">
        {{ ads['BottomBanner_468x60'] | safe if ads and 'BottomBanner_468x60' in ads }}
    </div>

    <footer class="bg-slate-950 text-slate-500 py-20 mt-20">
        <div class="container mx-auto px-6 grid grid-cols-1 md:grid-cols-3 gap-16">
            <div>
                <h3 class="text-white text-3xl font-black mb-6 uppercase italic tracking-tighter">{{ site.name }}</h3>
                <p class="text-sm leading-relaxed mb-8">{{ site.desc }}</p>
                <div class="flex gap-4">
                    <a href="{{ site.fb }}" class="w-12 h-12 bg-slate-900 rounded-2xl flex items-center justify-center hover:bg-indigo-600 transition hover:-translate-y-2"><i class="fab fa-facebook-f text-white text-xl"></i></a>
                    <a href="{{ site.ig }}" class="w-12 h-12 bg-slate-900 rounded-2xl flex items-center justify-center hover:bg-indigo-600 transition hover:-translate-y-2"><i class="fab fa-instagram text-white text-xl"></i></a>
                </div>
            </div>
            <div>
                <h4 class="text-white font-bold mb-8 uppercase text-sm tracking-widest">Legal & Policy</h4>
                <div class="flex flex-col gap-4 font-bold text-sm">
                    <a href="/p/privacy" class="hover:text-white transition">Privacy Policy</a>
                    <a href="/p/terms" class="hover:text-white transition">Terms of Service</a>
                </div>
            </div>
            <div>
                <h4 class="text-white font-bold mb-8 uppercase text-sm tracking-widest">Support</h4>
                <div class="bg-slate-900 p-6 rounded-3xl border border-slate-800">
                    <span class="text-white font-black text-xs">Day & Night Mode Optimized</span>
                </div>
            </div>
        </div>
        <div class="container mx-auto px-6 border-t border-slate-900 mt-20 pt-10 text-center text-[11px] font-black uppercase tracking-[0.3em]">
            &copy; {{ site.copyright }}
        </div>
    </footer>
    {% endif %}

    <div id="google_translate_element"></div>

    <script src="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.js"></script>
    <script type="text/javascript">
        function googleTranslateElementInit() {
            new google.translate.TranslateElement({pageLanguage: 'en', includedLanguages: 'en,bn,hi'}, 'google_translate_element');
        }
    </script>
    <script type="text/javascript" src="//translate.google.com/translate_a/element.js?cb=googleTranslateElementInit"></script>

    <script>
        function toggleTheme() {
            const body = document.getElementById('pageBody');
            const icon = document.getElementById('themeIcon');
            const iconMobile = document.getElementById('themeIconMobile');
            body.classList.toggle('dark-mode');
            
            const isDark = body.classList.contains('dark-mode');
            const iconClass = isDark ? 'fa-sun' : 'fa-moon';
            if(icon) icon.className = 'fas ' + iconClass;
            if(iconMobile) iconMobile.className = 'fas ' + iconClass;
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
        }

        document.addEventListener('DOMContentLoaded', function () {
            if(localStorage.getItem('theme') === 'dark') {
                document.getElementById('pageBody').classList.add('dark-mode');
                const icon = document.getElementById('themeIcon');
                const iconMobile = document.getElementById('themeIconMobile');
                if(icon) icon.className = 'fas fa-sun';
                if(iconMobile) iconMobile.className = 'fas fa-sun';
            }
            const swiper = new Swiper('.swiper', {
                loop: true, autoplay: { delay: 4000, disableOnInteraction: false },
                pagination: { el: '.swiper-pagination', clickable: true },
                navigation: { nextEl: '.swiper-button-next', prevEl: '.swiper-button-prev' },
            });
        });
    </script>
</body>
</html>
"""

# --- USER ROUTES ---

@app.route('/')
def home():
    site = get_site_info()
    ads = get_ads()
    q = request.args.get('q', '')
    all_media = list(media_col.find().sort('_id', -1))
    all_categories = list(categories_col.find().sort('name', 1))
    
    if q:
        apps = list(apps_col.find({"name": {"$regex": q, "$options": "i"}}).sort('_id', -1))
        home_data = [{"cat_name": f"Search Results: {q}", "apps": apps}]
        all_media = []
    else:
        home_data = []
        for cat in all_categories:
            limit = int(cat.get('limit', 6))
            cat_apps = list(apps_col.find({"category": cat['name']}).sort('_id', -1).limit(limit))
            if cat_apps:
                home_data.append({"cat_name": cat['name'], "apps": cat_apps})

    content = """
    {% if all_media %}
    <div class="swiper">
        <div class="swiper-wrapper">
            {% for m in all_media %}
            <div class="swiper-slide relative group">
                <img src="{{ m.url }}" class="w-full h-full object-cover">
                <div class="absolute inset-0 bg-gradient-to-t from-slate-950 via-transparent to-transparent flex flex-col justify-end p-12 text-left">
                    <h2 class="text-white text-4xl md:text-6xl font-black uppercase italic tracking-tighter mb-4">{{ m.title }}</h2>
                    <a href="{{ m.link }}" target="_blank" class="bg-indigo-600 text-white px-10 py-4 rounded-2xl font-black inline-block w-fit shadow-2xl">EXPLORE NOW</a>
                </div>
            </div>
            {% endfor %}
        </div>
        <div class="swiper-pagination"></div>
        <div class="swiper-button-next"></div>
        <div class="swiper-button-prev"></div>
    </div>
    {% endif %}

    {% for section in home_data %}
    <div class="mb-20">
        <div class="flex justify-between items-end mb-10 border-b-4 border-slate-50 dark:border-slate-800 pb-5">
            <h2 class="text-3xl font-black uppercase italic tracking-tighter text-title">{{ section.cat_name }}</h2>
            <a href="/category/{{ section.cat_name }}" class="text-indigo-600 font-black text-xs uppercase tracking-widest bg-indigo-50 dark:bg-indigo-900/30 px-6 py-2 rounded-full">View All</a>
        </div>
        
        {# In-Feed / Native Ad Between Category Rows #}
        <div class="ad-slot-wrapper">
            {{ ads['InFeed_Native'] | safe if ads and 'InFeed_Native' in ads }}
        </div>

        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-8">
            {% for app in section.apps %}
            <a href="/app/{{app._id}}" class="pro-card p-6 flex flex-col items-center text-center group">
                {% if app.badge %}<div class="app-badge">{{ app.badge }}</div>{% endif %}
                <div class="relative mb-6">
                    <img src="{{app.logo}}" class="w-24 h-24 rounded-[2rem] shadow-2xl group-hover:rotate-6 transition duration-500 border-4 border-white dark:border-slate-700">
                </div>
                <h3 class="font-black text-title text-base mb-4 line-clamp-1 uppercase italic">{{app.name}}</h3>
                <div class="w-full bg-slate-950 dark:bg-indigo-600 text-white py-3.5 rounded-2xl text-[10px] font-black uppercase tracking-widest group-hover:bg-indigo-700 transition">DOWNLOAD</div>
            </a>
            {% endfor %}
        </div>
    </div>
    {% endfor %}
    """
    return render_template_string(BASE_LAYOUT.replace('{% block content %}{% endblock %}', content), site=site, home_data=home_data, all_media=all_media, q=q, ads=ads, is_admin_route=False)

@app.route('/app/<id>')
def details(id):
    site = get_site_info()
    ads = get_ads()
    app_data = apps_col.find_one({"_id": ObjectId(id)})
    if not app_data: return redirect('/')
    content = """
    <div class="bg-white dark:bg-slate-800 rounded-[4rem] p-10 lg:p-20 shadow-2xl flex flex-col lg:flex-row gap-16 items-center lg:items-start border border-slate-100 dark:border-slate-700">
        <img src="{{app.logo}}" class="w-64 h-64 rounded-[4rem] shadow-2xl border-[12px] border-slate-50 dark:border-slate-900">
        <div class="flex-1 text-center lg:text-left">
            <h1 class="text-5xl lg:text-7xl font-black mb-8 uppercase italic tracking-tighter text-title">{{app.name}}</h1>
            <p class="text-slate-500 dark:text-slate-400 text-2xl mb-12 font-medium leading-relaxed">"{{app.info}}"</p>
            
            {# Rectangular Ad Slot in Details Page #}
            <div class="ad-slot-wrapper !justify-start mb-8">
                {{ ads['Details_300x250'] | safe if ads and 'Details_300x250' in ads }}
            </div>

            <div class="flex flex-wrap justify-center lg:justify-start gap-5 mb-12">
                <div class="bg-indigo-600 text-white px-10 py-3 rounded-full font-black text-xs uppercase shadow-xl">{{app.category}}</div>
                <div class="bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 px-10 py-3 rounded-full font-black text-xs uppercase italic">Ver: {{app.version}}</div>
            </div>
            <a href="/get/{{app._id}}" class="bg-slate-950 dark:bg-indigo-600 text-white px-16 py-7 rounded-[2.5rem] font-black text-2xl inline-block shadow-2xl hover:bg-indigo-600 transition transform hover:scale-105 uppercase tracking-tighter italic">Get Download Link</a>
        </div>
    </div>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block content %}{% endblock %}', content), site=site, app=app_data, ads=ads, is_admin_route=False)

@app.route('/p/<slug>')
def legal_pages(slug):
    site = get_site_info()
    ads = get_ads()
    if slug not in ["privacy", "terms", "dmca"]: return redirect('/')
    content = get_legal_content(slug)
    page_html = f"""
    <div class="max-w-4xl mx-auto bg-white dark:bg-slate-800 p-12 lg:p-24 rounded-[4rem] shadow-2xl border dark:border-slate-700">
        <h1 class="text-5xl font-black mb-10 uppercase italic tracking-tighter text-indigo-600 border-b-4 border-slate-50 dark:border-slate-900 pb-6 text-title">{{slug}} Policy</h1>
        <div class="text-slate-600 dark:text-slate-400 text-xl leading-loose whitespace-pre-line font-medium">{content}</div>
    </div>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block content %}{% endblock %}', page_html), site=site, ads=ads, is_admin_route=False)

# --- ADMIN: DASHBOARD ---

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
    <h1 class="text-5xl font-black mb-12 uppercase italic tracking-tighter">System Analytics</h1>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
        <div class="bg-indigo-600 p-10 rounded-[3rem] text-white shadow-2xl">
            <div class="text-7xl font-black mb-2">{{ stats.apps }}</div>
            <p class="font-bold uppercase opacity-60 text-xs tracking-[0.2em]">Total Applications</p>
        </div>
        <div class="bg-slate-900 p-10 rounded-[3rem] text-white shadow-2xl border-4 border-slate-800">
            <div class="text-7xl font-black mb-2">{{ stats.cats }}</div>
            <p class="font-bold uppercase opacity-60 text-xs tracking-[0.2em]">Active Categories</p>
        </div>
        <div class="bg-emerald-50 p-10 rounded-[3rem] text-white shadow-2xl">
            <div class="text-7xl font-black mb-2">{{ stats.media }}</div>
            <p class="font-bold uppercase opacity-60 text-xs tracking-[0.2em]">Media Banners</p>
        </div>
        <div class="bg-orange-500 p-10 rounded-[3rem] text-white shadow-2xl">
            <div class="text-7xl font-black mb-2">{{ stats.ads }}</div>
            <p class="font-bold uppercase opacity-60 text-xs tracking-[0.2em]">Integrated Ads</p>
        </div>
    </div>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block admin_content %}{% endblock %}', content), site=site, stats=stats, is_admin_route=True, ads={}, active="dashboard")

# --- ADMIN: CATEGORIES ---

@app.route('/admin/categories', methods=['GET', 'POST'])
def admin_categories():
    if not session.get('logged_in'): return redirect('/admin-gate')
    if request.method == 'POST':
        name = request.form.get('name')
        limit = request.form.get('limit', 6)
        categories_col.update_one({"name": name}, {"$set": {"name": name, "limit": int(limit)}}, upsert=True)
        flash(f"Category updated.")
        return redirect('/admin/categories')
    
    cats = list(categories_col.find().sort('name', 1))
    site = get_site_info()
    content = """
    <h1 class="text-5xl font-black mb-12 uppercase italic tracking-tighter">Category Manager</h1>
    <div class="grid lg:grid-cols-12 gap-12">
        <form method="POST" class="lg:col-span-4 bg-slate-50 p-10 rounded-[3rem] border-2 border-dashed border-slate-200 h-fit space-y-5">
            <h2 class="font-black text-indigo-600 uppercase italic">Add / Edit Category</h2>
            <input name="name" placeholder="Category Name" required>
            <input type="number" name="limit" placeholder="Post Limit" required>
            <button class="btn-main w-full py-5 text-lg">SAVE CATEGORY</button>
        </form>
        <div class="lg:col-span-8 bg-white border-2 rounded-[3rem] overflow-hidden shadow-xl">
            <table class="w-full text-left">
                <thead class="bg-slate-950 text-white text-[11px] uppercase font-bold tracking-widest">
                    <tr><th class="p-6">Category Name</th><th class="p-6 text-center">Post Limit</th><th class="p-6 text-right">Actions</th></tr>
                </thead>
                <tbody class="text-sm font-bold">
                    {% for c in cats %}
                    <tr class="border-t hover:bg-slate-50 transition">
                        <td class="p-6 text-slate-800">{{ c.name }}</td>
                        <td class="p-6 text-center font-black text-indigo-600">{{ c.limit }}</td>
                        <td class="p-6 text-right">
                            <a href="/admin/del-cat/{{ c._id }}" class="text-red-500 hover:underline" onclick="return confirm('Confirm deletion?')">DELETE</a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block admin_content %}{% endblock %}', content), site=site, cats=cats, is_admin_route=True, ads={}, active="categories")

# --- ADMIN: POSTER BADGES ---

@app.route('/admin/badges', methods=['GET', 'POST'])
def admin_badges():
    if not session.get('logged_in'): return redirect('/admin-gate')
    if request.method == 'POST':
        name = request.form.get('name')
        badges_col.update_one({"name": name}, {"$set": {"name": name}}, upsert=True)
        flash("Badge saved successfully.")
        return redirect('/admin/badges')
    
    badges = list(badges_col.find().sort('name', 1))
    site = get_site_info()
    content = """
    <h1 class="text-5xl font-black mb-12 uppercase italic tracking-tighter">Poster Badge Manager</h1>
    <div class="grid lg:grid-cols-12 gap-12">
        <form method="POST" class="lg:col-span-4 bg-slate-50 p-10 rounded-[3rem] border-2 border-dashed border-slate-200 h-fit space-y-5">
            <h2 class="font-black text-indigo-600 uppercase italic">Add New Badge</h2>
            <input name="name" placeholder="Badge Name (MOD, PREMIUM, NEW)" required>
            <button class="btn-main w-full py-5 text-lg">SAVE BADGE</button>
        </form>
        <div class="lg:col-span-8 bg-white border-2 rounded-[3rem] overflow-hidden shadow-xl">
            <table class="w-full text-left">
                <thead class="bg-slate-950 text-white text-[11px] uppercase font-bold tracking-widest">
                    <tr><th class="p-6">Badge Text</th><th class="p-6 text-right">Actions</th></tr>
                </thead>
                <tbody class="text-sm font-bold">
                    {% for b in badges %}
                    <tr class="border-t hover:bg-slate-50 transition">
                        <td class="p-6 text-slate-800 font-black uppercase italic">{{ b.name }}</td>
                        <td class="p-6 text-right">
                            <a href="/admin/del-badge/{{ b._id }}" class="text-red-500 hover:underline" onclick="return confirm('Delete badge?')">DELETE</a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block admin_content %}{% endblock %}', content), site=site, badges=badges, is_admin_route=True, ads={}, active="badges")

# --- ADMIN: APP VERSIONS (NEW) ---

@app.route('/admin/versions', methods=['GET', 'POST'])
def admin_versions():
    if not session.get('logged_in'): return redirect('/admin-gate')
    if request.method == 'POST':
        name = request.form.get('name')
        versions_col.update_one({"name": name}, {"$set": {"name": name}}, upsert=True)
        flash("Version tag saved successfully.")
        return redirect('/admin/versions')
    
    vers = list(versions_col.find().sort('name', -1))
    site = get_site_info()
    content = """
    <h1 class="text-5xl font-black mb-12 uppercase italic tracking-tighter">Version Manager</h1>
    <div class="grid lg:grid-cols-12 gap-12">
        <form method="POST" class="lg:col-span-4 bg-slate-50 p-10 rounded-[3rem] border-2 border-dashed border-slate-200 h-fit space-y-5">
            <h2 class="font-black text-emerald-600 uppercase italic">Add Version Tag</h2>
            <input name="name" placeholder="Version (e.g. v1.0.2, Lastest)" required>
            <button class="btn-main w-full py-5 text-lg bg-emerald-600">SAVE VERSION</button>
        </form>
        <div class="lg:col-span-8 bg-white border-2 rounded-[3rem] overflow-hidden shadow-xl">
            <table class="w-full text-left">
                <thead class="bg-slate-950 text-white text-[11px] uppercase font-bold tracking-widest">
                    <tr><th class="p-6">Version Name</th><th class="p-6 text-right">Actions</th></tr>
                </thead>
                <tbody class="text-sm font-bold">
                    {% for v in vers %}
                    <tr class="border-t hover:bg-slate-50 transition">
                        <td class="p-6 text-slate-800 font-black">{{ v.name }}</td>
                        <td class="p-6 text-right">
                            <a href="/admin/del-version/{{ v._id }}" class="text-red-500 hover:underline" onclick="return confirm('Delete version?')">DELETE</a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block admin_content %}{% endblock %}', content), site=site, vers=vers, is_admin_route=True, ads={}, active="versions")

# --- ADMIN: APPS MANAGER ---

@app.route('/admin/apps', methods=['GET', 'POST'])
def admin_apps():
    if not session.get('logged_in'): return redirect('/admin-gate')
    site = get_site_info()
    cats = list(categories_col.find().sort('name', 1))
    all_badges = list(badges_col.find().sort('name', 1))
    all_vers = list(versions_col.find().sort('name', -1))
    
    admin_q = request.args.get('admin_q', '')
    query = {}
    if admin_q:
        query["name"] = {"$regex": admin_q, "$options": "i"}

    if request.method == 'POST':
        apps_col.insert_one({
            "name": request.form.get('name'), "logo": request.form.get('logo'),
            "category": request.form.get('category'), "version": request.form.get('version'),
            "badge": request.form.get('badge'),
            "info": request.form.get('info'), "download_link": request.form.get('download_link'),
            "created_at": datetime.now()
        })
        flash("Application published successfully.")
        return redirect('/admin/apps')
    
    all_apps = list(apps_col.find(query).sort('_id', -1))
    content = """
    <h1 class="text-5xl font-black mb-12 uppercase italic tracking-tighter">Apps Manager</h1>
    <div class="grid lg:grid-cols-12 gap-12">
        <form method="POST" class="lg:col-span-4 bg-slate-50 p-10 rounded-[3rem] border-2 border-slate-200 h-fit space-y-4">
            <h2 class="font-black text-indigo-600 uppercase italic">Publish New App</h2>
            <input name="name" placeholder="Application Title" required>
            <input name="logo" placeholder="Logo Link" required>
            <select name="badge">
                <option value="">Select Poster Badge</option>
                {% for b in all_badges %}<option value="{{ b.name }}">{{ b.name }}</option>{% endfor %}
            </select>
            <select name="category" required>
                <option value="" disabled selected>Select Category</option>
                {% for c in cats %}<option value="{{c.name}}">{{c.name}}</option>{% endfor %}
            </select>
            <select name="version" required>
                <option value="" disabled selected>Select Version</option>
                {% for v in all_vers %}<option value="{{v.name}}">{{v.name}}</option>{% endfor %}
            </select>
            <textarea name="info" placeholder="Description" class="h-32" required></textarea>
            <input name="download_link" placeholder="Download URL" required>
            <button class="btn-main w-full py-5 text-lg">PUBLISH APP</button>
        </form>
        
        <div class="lg:col-span-8 space-y-6">
            <form action="/admin/apps" method="GET" class="flex bg-slate-100 rounded-3xl px-6 py-2 border border-slate-200 shadow-inner">
                <input type="text" name="admin_q" placeholder="Search Apps by Name..." class="bg-transparent border-none p-0 w-full text-sm font-semibold outline-none" value="{{ admin_q }}">
                <button type="submit"><i class="fas fa-search text-indigo-600 text-lg"></i></button>
            </form>
            <div class="bg-white border-2 rounded-[3rem] overflow-hidden shadow-xl overflow-x-auto">
                <table class="w-full text-left">
                    <thead class="bg-slate-950 text-white text-[11px] uppercase font-bold tracking-widest">
                        <tr><th class="p-6">Asset Details</th><th class="p-6">Category</th><th class="p-6 text-right">Actions</th></tr>
                    </thead>
                    <tbody class="text-sm">
                        {% for a in all_apps %}
                        <tr class="border-t hover:bg-slate-50 transition">
                            <td class="p-6 flex items-center gap-4">
                                <img src="{{a.logo}}" class="w-12 h-12 rounded-xl border-2 border-white shadow-md">
                                <span class="font-bold text-slate-800">{{a.name}}</span>
                            </td>
                            <td class="p-6 uppercase font-black text-slate-400 text-[10px]">{{a.category}}</td>
                            <td class="p-6 text-right space-x-4">
                                <a href="/admin/edit-app/{{a._id}}" class="text-indigo-600 font-bold">EDIT</a>
                                <a href="/del/app/{{a._id}}" class="text-red-500 font-bold" onclick="return confirm('Delete app?')">DEL</a>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block admin_content %}{% endblock %}', content), site=site, all_apps=all_apps, cats=cats, all_badges=all_badges, all_vers=all_vers, admin_q=admin_q, is_admin_route=True, ads={}, active="apps")

@app.route('/admin/edit-app/<id>', methods=['GET', 'POST'])
def edit_app(id):
    if not session.get('logged_in'): return redirect('/admin-gate')
    app_data = apps_col.find_one({"_id": ObjectId(id)})
    site = get_site_info()
    cats = list(categories_col.find().sort('name', 1))
    all_badges = list(badges_col.find().sort('name', 1))
    all_vers = list(versions_col.find().sort('name', -1))
    
    if request.method == 'POST':
        apps_col.update_one({"_id": ObjectId(id)}, {"$set": {
            "name": request.form.get('name'), "logo": request.form.get('logo'),
            "category": request.form.get('category'), "version": request.form.get('version'),
            "badge": request.form.get('badge'),
            "info": request.form.get('info'), "download_link": request.form.get('download_link')
        }})
        flash("Application data updated.")
        return redirect('/admin/apps')
        
    content = """
    <h1 class="text-4xl font-black mb-10 uppercase italic">Edit: {{app_data.name}}</h1>
    <form method="POST" class="max-w-3xl bg-white p-10 rounded-[3rem] border-2 shadow-2xl space-y-6">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <input name="name" value="{{app_data.name}}" required>
            <input name="logo" value="{{app_data.logo}}" required>
            <select name="badge">
                <option value="">Select Poster Badge</option>
                {% for b in all_badges %}<option value="{{ b.name }}" {% if b.name == app_data.badge %}selected{% endif %}>{{ b.name }}</option>{% endfor %}
            </select>
            <select name="category" required>
                {% for c in cats %}<option value="{{c.name}}" {% if c.name == app_data.category %}selected{% endif %}>{{c.name}}</option>{% endfor %}
            </select>
            <select name="version" required>
                {% for v in all_vers %}<option value="{{v.name}}" {% if v.name == app_data.version %}selected{% endif %}>{{v.name}}</option>{% endfor %}
            </select>
        </div>
        <textarea name="info" class="h-40" required>{{app_data.info}}</textarea>
        <input name="download_link" value="{{app_data.download_link}}" required>
        <div class="flex gap-4">
            <button class="btn-main flex-1 py-5">UPDATE DATA</button>
            <a href="/admin/apps" class="bg-slate-100 text-slate-500 px-10 py-5 rounded-[18px] font-bold">CANCEL</a>
        </div>
    </form>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block admin_content %}{% endblock %}', content), site=site, app_data=app_data, cats=cats, all_badges=all_badges, all_vers=all_vers, is_admin_route=True, ads={}, active="apps")

# --- ADMIN: MEDIA ---

@app.route('/admin/media', methods=['GET', 'POST'])
def admin_media():
    if not session.get('logged_in'): return redirect('/admin-gate')
    if request.method == 'POST':
        media_col.insert_one({
            "title": request.form.get('title'), "url": request.form.get('url'),
            "link": request.form.get('link'), "created_at": datetime.now()
        })
        flash("Media banner has been added.")
        return redirect('/admin/media')
    
    media_list = list(media_col.find().sort('_id', -1))
    site = get_site_info()
    content = """
    <h1 class="text-5xl font-black mb-12 uppercase italic tracking-tighter">Media Center</h1>
    <div class="grid lg:grid-cols-12 gap-12">
        <form method="POST" class="lg:col-span-4 bg-slate-50 p-10 rounded-[3rem] border-2 border-dashed border-slate-200 h-fit space-y-5">
            <h2 class="font-black text-emerald-600 uppercase italic">New Slider Banner</h2>
            <input name="title" placeholder="Banner Headline" required>
            <input name="url" placeholder="Banner Image URL" required>
            <input name="link" placeholder="Redirect Link" required>
            <button class="bg-emerald-600 text-white w-full py-5 rounded-2xl font-bold shadow-lg">PUBLISH BANNER</button>
        </form>
        <div class="lg:col-span-8 grid grid-cols-1 md:grid-cols-2 gap-8">
            {% for m in media_list %}
            <div class="bg-white border-2 rounded-[2.5rem] overflow-hidden shadow-xl flex flex-col group">
                <div class="relative overflow-hidden h-48">
                    <img src="{{ m.url }}" class="w-full h-full object-cover group-hover:scale-110 transition duration-700">
                </div>
                <div class="p-6">
                    <h3 class="font-black uppercase text-sm truncate mb-1 italic">{{ m.title }}</h3>
                    <a href="/admin/del-media/{{ m._id }}" class="text-red-500 font-black text-xs hover:underline" onclick="return confirm('Remove media?')">REMOVE FROM SLIDER</a>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block admin_content %}{% endblock %}', content), site=site, media_list=media_list, is_admin_route=True, ads={}, active="media")

# --- ADMIN: ADS & LAYOUT ---

@app.route('/admin/ads', methods=['GET', 'POST'])
def admin_ads():
    if not session.get('logged_in'): return redirect('/admin-gate')
    if request.method == 'POST':
        ads_col.update_one(
            {"name": request.form.get('name')},
            {"$set": {"name": request.form.get('name'), "code": request.form.get('code'), "created_at": datetime.now()}},
            upsert=True
        )
        flash("Advertisement integrated successfully.")
        return redirect('/admin/ads')
    ads_list = list(ads_col.find())
    site = get_site_info()
    content = """
    <h1 class="text-5xl font-black mb-12 uppercase italic tracking-tighter">Google Ads & Global Manager</h1>
    <div class="grid lg:grid-cols-2 gap-12">
        <form method="POST" class="bg-slate-50 p-10 rounded-[3rem] border-2 border-slate-200 space-y-5">
            <h2 class="font-black text-indigo-600 uppercase italic">Integrate New Ad Code</h2>
            <select name="name" required>
                <option value="" disabled selected>Select Ad Placement</option>
                <option value="GlobalHeader">Global Head Script (Auto Ads / Google Tag)</option>
                <option value="TopBanner_728x90">Top Banner (728x90 / 320x50)</option>
                <option value="BottomBanner_468x60">Bottom Banner (468x60 / 320x50)</option>
                <option value="Details_300x250">Details Page Rectangle (300x250)</option>
                <option value="InFeed_Native">Home Feed Native (In-between Rows)</option>
                <option value="Popunder">Popunder Script</option>
                <option value="SocialBar">Social Bar / Floater</option>
            </select>
            <textarea name="code" placeholder="Paste Ad HTML/JS Code Here" class="h-64 font-mono text-sm" required></textarea>
            <button class="btn-main w-full py-5">DEPLOY AD CODE</button>
        </form>
        <div class="space-y-6">
            {% for ad in ads_list %}
            <div class="bg-white border-2 p-8 rounded-[2.5rem] flex justify-between items-center shadow-lg">
                <span class="font-black uppercase text-sm italic tracking-widest text-slate-700">{{ ad.name }}</span>
                <a href="/del/ad/{{ ad._id }}" class="text-red-500 font-black text-xs">REMOVE CODE</a>
            </div>
            {% endfor %}
        </div>
    </div>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block admin_content %}{% endblock %}', content), site=site, ads_list=ads_list, is_admin_route=True, ads={}, active="ads")

@app.route('/admin/layout', methods=['GET', 'POST'])
def admin_layout():
    if not session.get('logged_in'): return redirect('/admin-gate')
    site = get_site_info()
    if request.method == 'POST':
        l_type = request.form.get('l_type')
        if l_type == 'branding':
            settings_col.update_one({"type": "site_info"}, {"$set": {
                "name": request.form.get('name'), "logo": request.form.get('logo'), 
                "title": request.form.get('title'), "desc": request.form.get('desc'), 
                "copyright": request.form.get('copyright'), "fb": request.form.get('fb'), "ig": request.form.get('ig')
            }}, upsert=True)
        elif l_type == 'legal':
            settings_col.update_one({"type": "legal_page", "page": request.form.get('page')}, {"$set": {"text": request.form.get('text')}}, upsert=True)
        flash("Layout and branding settings saved.")
        return redirect('/admin/layout')
    
    content = """
    <h1 class="text-5xl font-black mb-12 uppercase italic tracking-tighter">Site Customization</h1>
    <div class="grid lg:grid-cols-2 gap-12">
        <form method="POST" class="bg-white p-10 rounded-[3rem] border-2 shadow-xl space-y-5 h-fit">
            <input type="hidden" name="l_type" value="branding">
            <h2 class="font-black uppercase italic text-indigo-600 border-b pb-4">Branding & Socials</h2>
            <div class="grid grid-cols-2 gap-4">
                <input name="name" value="{{site.name}}" placeholder="Site Name">
                <input name="logo" value="{{site.logo}}" placeholder="Logo URL">
            </div>
            <input name="title" value="{{site.title}}" placeholder="Browser Tab Title">
            <textarea name="desc" class="h-24">{{site.desc}}</textarea>
            <input name="copyright" value="{{site.copyright}}" placeholder="Copyright Text">
            <div class="grid grid-cols-2 gap-4">
                <input name="fb" value="{{site.fb}}" placeholder="Facebook Link">
                <input name="ig" value="{{site.ig}}" placeholder="Instagram Link">
            </div>
            <button class="btn-main w-full py-5">SAVE ALL BRANDING</button>
        </form>
        <form method="POST" class="bg-slate-50 p-10 rounded-[3rem] border-2 border-dashed border-slate-200 space-y-5 h-fit">
            <input type="hidden" name="l_type" value="legal">
            <h2 class="font-black uppercase italic text-emerald-600 border-b pb-4">Legal Page Editor</h2>
            <select name="page" required>
                <option value="privacy">Privacy Policy</option>
                <option value="terms">Terms of Service</option>
                <option value="dmca">DMCA Takedown</option>
            </select>
            <textarea name="text" placeholder="Paste policy text here..." class="h-80 font-medium"></textarea>
            <button class="btn-main w-full py-5 bg-emerald-600">UPDATE LEGAL CONTENT</button>
        </form>
    </div>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block admin_content %}{% endblock %}', content), site=site, is_admin_route=True, ads={}, active="layout")

# --- ADMIN: SETTINGS ---

@app.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    if not session.get('logged_in'): return redirect('/admin-gate')
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        if form_type == 'api':
            settings_col.update_one({"type": "shortener"}, {"$set": {"url": request.form.get('url'), "api": request.form.get('api')}}, upsert=True)
            flash("API Configuration Saved.")
        elif form_type == 'password':
            new_pw = request.form.get('new_password')
            confirm_pw = request.form.get('confirm_password')
            if new_pw == confirm_pw:
                users_col.update_one({"username": "admin"}, {"$set": {"password": generate_password_hash(new_pw)}})
                flash("Admin password updated successfully.")
            else:
                flash("Passwords do not match!")
        return redirect('/admin/settings')
    
    cfg = get_shortener()
    site = get_site_info()
    content = """
    <h1 class="text-5xl font-black mb-12 uppercase italic tracking-tighter">System & Security</h1>
    <div class="grid lg:grid-cols-2 gap-12">
        <div class="bg-slate-950 p-12 rounded-[4rem] shadow-2xl border-4 border-slate-900">
            <h2 class="text-emerald-400 font-black uppercase mb-8 italic tracking-widest text-sm">Universal Link Shortener (API)</h2>
            <form method="POST" class="space-y-6">
                <input type="hidden" name="form_type" value="api">
                <input name="url" value="{{cfg.url}}" placeholder="Domain" class="bg-slate-900 border-none text-white font-bold py-5 text-xl">
                <input name="api" value="{{cfg.api}}" placeholder="API Token" class="bg-slate-900 border-none text-white font-bold py-5 text-xl">
                <button class="bg-emerald-500 text-black w-full py-5 rounded-[2rem] font-black text-xl">UPDATE GLOBAL API</button>
            </form>
        </div>
        
        <div class="bg-white p-12 rounded-[4rem] shadow-2xl border-4 border-slate-50">
            <h2 class="text-indigo-600 font-black uppercase mb-8 italic tracking-widest text-sm">Change Admin Password</h2>
            <form method="POST" class="space-y-6">
                <input type="hidden" name="form_type" value="password">
                <input type="password" name="new_password" placeholder="New Password" required class="bg-slate-50 border-slate-200">
                <input type="password" name="confirm_password" placeholder="Confirm New Password" required class="bg-slate-50 border-slate-200">
                <button class="btn-main w-full py-5 text-xl">UPDATE PASSWORD</button>
            </form>
        </div>
    </div>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block admin_content %}{% endblock %}', content), site=site, cfg=cfg, is_admin_route=True, ads={}, active="settings")

# --- LOGIN & AUTH ---

@app.route('/admin-gate', methods=['GET', 'POST'])
def login():
    site = get_site_info()
    if request.method == 'POST':
        pw = request.form.get('password')
        admin = users_col.find_one({"username": "admin"})
        if not admin:
            users_col.insert_one({"username": "admin", "password": generate_password_hash(pw)})
            session['logged_in'] = True; return redirect('/admin/dashboard')
        if check_password_hash(admin['password'], pw):
            session['logged_in'] = True; return redirect('/admin/dashboard')
        flash("Denied.")
    return render_template_string(f"<!DOCTYPE html><html><head>{BASE_CSS}</head><body class='bg-slate-100 flex items-center justify-center min-h-screen'><form method='POST' class='bg-white p-12 rounded-[4rem] shadow-2xl w-full max-w-md text-center border-4 border-white'><img src='{site['logo']}' class='w-24 h-24 rounded-[2rem] mx-auto mb-10 shadow-xl border-4 border-slate-50'><h2 class='text-4xl font-black mb-10 uppercase italic tracking-tighter'>System Lock</h2><input type='password' name='password' class='text-center font-black text-3xl mb-8 p-6' placeholder='••••' required><button class='bg-slate-950 text-white w-full py-6 rounded-3xl font-black text-xl shadow-2xl hover:bg-indigo-600 transition'>UNLOCK SYSTEM</button></form></body></html>")

@app.route('/forgot', methods=['GET', 'POST'])
def forgot():
    if request.method == 'POST':
        if request.form.get('key') == RECOVERY_KEY:
            users_col.update_one({"username": "admin"}, {"$set": {"password": generate_password_hash(request.form.get('pw'))}}, upsert=True)
            flash("System password reset.")
            return redirect('/admin-gate')
    return render_template_string(f"<!DOCTYPE html><html><head>{BASE_CSS}</head><body class='bg-slate-100 flex items-center justify-center min-h-screen'><form method='POST' class='bg-white p-12 rounded-[3.5rem] shadow-xl w-full max-w-md space-y-6'><h2 class='font-black uppercase italic text-center'>Reset Key</h2><input name='key' placeholder='Recovery Key' required><input type='password' name='pw' placeholder='New Password' required><button class='btn-main w-full py-5 text-xl'>RESET NOW</button></form></body></html>")

# --- SYSTEM CORE ---

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
        except: pass
    return redirect(target)

@app.route('/admin/del-cat/<id>')
def delete_cat(id):
    if not session.get('logged_in'): return redirect('/admin-gate')
    categories_col.delete_one({"_id": ObjectId(id)}); return redirect('/admin/categories')

@app.route('/admin/del-badge/<id>')
def delete_badge(id):
    if not session.get('logged_in'): return redirect('/admin-gate')
    badges_col.delete_one({"_id": ObjectId(id)}); return redirect('/admin/badges')

@app.route('/admin/del-version/<id>')
def delete_version(id):
    if not session.get('logged_in'): return redirect('/admin-gate')
    versions_col.delete_one({"_id": ObjectId(id)}); return redirect('/admin/versions')

@app.route('/admin/del-media/<id>')
def delete_media(id):
    if not session.get('logged_in'): return redirect('/admin-gate')
    media_col.delete_one({"_id": ObjectId(id)}); return redirect('/admin/media')

@app.route('/del/<type>/<id>')
def delete_entry(type, id):
    if not session.get('logged_in'): return redirect('/admin-gate')
    if type == 'app': apps_col.delete_one({"_id": ObjectId(id)})
    if type == 'ad': ads_col.delete_one({"_id": ObjectId(id)})
    return redirect(request.referrer)

@app.route('/logout')
def logout(): session.clear(); return redirect('/')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
