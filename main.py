import os
import requests
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash

# --- ফ্ল্যাস্ক অ্যাপ এবং কনফিগারেশন ---
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "pro_app_hub_secure_key_2024_final")
RECOVERY_KEY = os.environ.get("RECOVERY_KEY", "admin@2024")

# --- MONGODB কানেকশন এবং ডেটাবেজ সেটআপ ---
try:
    # আপনার দেওয়া কানেকশন স্ট্রিং
    MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client['app_hub_ultimate_production']
    apps_col = db['apps']
    users_col = db['users']
    ads_col = db['ads']
    settings_col = db['settings']
except Exception as e:
    print(f"DATABASE CONNECTION ERROR: {e}")

# --- গ্লোবাল ফাংশন: সাইট ব্র্যান্ডিং এবং সেটিংস ---
def get_site_branding():
    branding = settings_col.find_one({"type": "branding"})
    if not branding:
        return {
            "name": "APPHUB PRO",
            "title": "Premium App Download Store",
            "logo": "https://cdn-icons-png.flaticon.com/512/2589/2589127.png"
        }
    return branding

def get_shortener_config():
    return settings_col.find_one({"type": "shortener"}) or {}

# --- প্রফেশনাল ইউআই স্টাইল (Detailed CSS) ---
UI_HEADER = """
<script src="https://cdn.tailwindcss.com"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.css" />
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;700;800&display=swap');
    body { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #f9fafb; color: #1e293b; }
    .glass-nav { background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(15px); border-bottom: 1px solid rgba(226, 232, 240, 0.8); }
    .hero-gradient { background: linear-gradient(135deg, #4f46e5 0%, #1e1b4b 100%); }
    .pro-card { background: white; border: 1px solid #f1f5f9; border-radius: 2rem; transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1); position: relative; overflow: hidden; }
    .pro-card:hover { transform: translateY(-12px); box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.1); border-color: #6366f1; }
    .sidebar-link { display: flex; align-items: center; gap: 12px; padding: 14px 20px; border-radius: 16px; font-weight: 600; color: #94a3b8; transition: 0.3s; }
    .sidebar-link:hover { background: rgba(99, 102, 241, 0.1); color: #6366f1; }
    .sidebar-active { background: #6366f1 !important; color: white !important; box-shadow: 0 10px 15px -3px rgba(99, 102, 241, 0.4); }
    .swiper { width: 100%; height: 420px; border-radius: 2.5rem; overflow: hidden; margin-bottom: 2rem; box-shadow: 0 20px 40px -10px rgba(0,0,0,0.2); }
    .line-clamp-2 { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
    .btn-indigo { background: #6366f1; color: white; padding: 12px 24px; border-radius: 16px; font-weight: 700; transition: 0.3s; box-shadow: 0 4px 14px 0 rgba(99, 102, 241, 0.39); }
    .btn-indigo:hover { background: #4f46e5; transform: scale(1.05); }
    input, textarea, select { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 14px; padding: 12px 16px; outline: none; transition: 0.3s; }
    input:focus, textarea:focus { border-color: #6366f1; background: white; box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.1); }
</style>
"""

# --- মেইন লেআউট জেনারেটর ---
def render_page(content, site, is_admin=False, active_page=""):
    nav = ""
    if not is_admin:
        nav = f'''
        <nav class="glass-nav h-20 sticky top-0 z-50">
            <div class="container mx-auto px-6 h-full flex items-center justify-between">
                <a href="/" class="flex items-center gap-3">
                    <img src="{site['logo']}" class="w-10 h-10 rounded-xl shadow-sm">
                    <span class="text-2xl font-extrabold text-slate-900 tracking-tighter uppercase">{site['name']}</span>
                </a>
                <div class="hidden md:flex flex-1 max-w-xl mx-12">
                    <form action="/" method="GET" class="w-full flex bg-slate-100 rounded-2xl px-5 py-2.5 items-center border border-slate-200">
                        <input type="text" name="q" placeholder="Search for your favorite apps..." class="bg-transparent outline-none text-sm w-full text-slate-600 font-medium">
                        <button type="submit"><i class="fas fa-search text-slate-400"></i></button>
                    </form>
                </div>
                <div class="text-[10px] font-black bg-slate-900 text-white px-3 py-1.5 rounded-full tracking-widest uppercase">Premium Store</div>
            </div>
        </nav>
        '''

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{site['name']} | {site['title']}</title>
        {UI_HEADER}
    </head>
    <body class="bg-slate-50">
        {nav}
        <div class="{'flex min-h-screen' if is_admin else 'container mx-auto px-6 py-12'}">
            {content}
        </div>
        <script src="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.js"></script>
        <script>
            const swiper = new Swiper('.swiper', {{
                loop: true, autoplay: {{ delay: 4000 }},
                pagination: {{ el: '.swiper-pagination', clickable: true }},
                navigation: {{ nextEl: '.swiper-button-next', prevEl: '.swiper-button-prev' }},
            }});
        </script>
    </body>
    </html>
    """

# --- ইউজার প্যানেল রাউটস (USER PANEL) ---

@app.route('/')
def home():
    site = get_site_branding()
    q = request.args.get('q', '')
    if q:
        apps = list(apps_col.find({"name": {"$regex": q, "$options": "i"}}).sort('_id', -1))
        featured = []
    else:
        apps = list(apps_col.find().sort('_id', -1))
        featured = list(apps_col.find({"featured": "on"}).limit(5))
    
    ads_html = "".join([f'<div class="bg-white p-4 rounded-3xl border border-slate-200 flex justify-center mb-8 shadow-sm">{ad["code"]}</div>' for ad in ads_col.find()])
    
    featured_html = ""
    if featured:
        slides = "".join([f'''
        <div class="swiper-slide hero-gradient flex items-center p-12 text-white relative">
            <div class="z-10 max-w-2xl">
                <span class="bg-indigo-500 text-[10px] font-bold px-4 py-1 rounded-full uppercase mb-6 inline-block tracking-widest">Editor's Choice</span>
                <h2 class="text-6xl font-black mb-6 leading-tight tracking-tighter">{f['name']}</h2>
                <p class="text-indigo-100 text-lg mb-10 line-clamp-2 opacity-90 leading-relaxed">{f['info']}</p>
                <div class="flex gap-4">
                    <a href="/app/{f['_id']}" class="bg-white text-indigo-900 px-10 py-4 rounded-2xl font-black text-xl shadow-2xl transition hover:scale-105">Details <i class="fas fa-arrow-right ml-2 text-sm"></i></a>
                </div>
            </div>
            <img src="{f['logo']}" class="absolute right-20 w-64 h-64 rounded-[4rem] shadow-2xl hidden lg:block rotate-6 opacity-80 border-8 border-indigo-400/30">
        </div>
        ''' for f in featured])
        featured_html = f'<div class="swiper"><div class="swiper-wrapper">{slides}</div><div class="swiper-pagination"></div></div>'

    apps_html = "".join([f'''
    <a href="/app/{a['_id']}" class="pro-card p-8 group">
        <div class="relative mb-6">
            <img src="{a['logo']}" class="w-24 h-24 rounded-[2.5rem] mx-auto shadow-xl group-hover:scale-110 transition duration-500">
            {f'<div class="absolute -top-2 -right-2 bg-indigo-600 text-white text-[9px] font-black px-3 py-1 rounded-full shadow-lg italic">FEATURED</div>' if a.get('featured') == 'on' else ''}
        </div>
        <h3 class="font-extrabold text-xl text-slate-800 mb-2 truncate px-2">{a['name']}</h3>
        <div class="flex justify-center gap-2 mb-4 font-bold uppercase text-[10px]">
            <span class="bg-indigo-50 text-indigo-600 px-3 py-1 rounded-full">{a['category']}</span>
            <span class="bg-slate-100 text-slate-500 px-3 py-1 rounded-full">v{a['version']}</span>
        </div>
        <p class="text-xs text-slate-400 line-clamp-2 h-8 mb-6 leading-relaxed px-2">{a['info']}</p>
        <div class="btn-indigo w-full flex justify-center py-3.5 group-hover:bg-indigo-800 transition">Download Now</div>
    </a>
    ''' for a in apps])

    content = f"""
    {featured_html}
    <div class="max-w-4xl mx-auto">{ads_html}</div>
    <div class="flex justify-between items-center mb-10 border-b pb-6 border-slate-200">
        <h2 class="text-3xl font-black text-slate-800">{"Results for " + q if q else "Discover Latest Apps"}</h2>
        <span class="text-xs font-extrabold text-slate-400 uppercase tracking-widest">{ len(apps) } Apps Found</span>
    </div>
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-10">{apps_html}</div>
    """
    return render_page(content, site)

@app.route('/app/<id>')
def details(id):
    site = get_site_branding()
    app_data = apps_col.find_one({"_id": ObjectId(id)})
    if not app_data: return redirect('/')
    
    content = f"""
    <div class="max-w-5xl mx-auto">
        <div class="bg-white rounded-[4rem] shadow-2xl p-12 md:p-20 flex flex-col md:flex-row gap-16 items-center border border-slate-100 relative overflow-hidden">
            <div class="absolute top-0 right-0 p-10 opacity-5 text-indigo-900 pointer-events-none">
                <i class="fas fa-download text-[200px]"></i>
            </div>
            <div class="relative">
                <img src="{app_data['logo']}" class="w-72 h-72 rounded-[4.5rem] shadow-2xl border-8 border-slate-50">
                <div class="absolute -bottom-6 -right-6 bg-indigo-600 text-white p-6 rounded-full shadow-2xl">
                    <i class="fas fa-shield-alt text-3xl"></i>
                </div>
            </div>
            <div class="flex-1 text-center md:text-left">
                <div class="flex flex-wrap gap-3 mb-8 justify-center md:justify-start">
                    <span class="bg-indigo-50 text-indigo-600 px-6 py-2 rounded-full font-extrabold text-xs uppercase tracking-widest">{app_data['category']}</span>
                    <span class="bg-emerald-50 text-emerald-600 px-6 py-2 rounded-full font-extrabold text-xs uppercase tracking-widest">Version {app_data['version']}</span>
                    <span class="bg-slate-100 text-slate-500 px-6 py-2 rounded-full font-extrabold text-xs uppercase tracking-widest">Official Release</span>
                </div>
                <h1 class="text-6xl font-black text-slate-900 mb-8 leading-none tracking-tighter italic uppercase">{app_data['name']}</h1>
                <p class="text-slate-500 text-xl leading-relaxed mb-12 opacity-80">{app_data['info']}</p>
                
                <div class="grid grid-cols-2 gap-6 mb-12">
                    <div class="bg-slate-50 p-6 rounded-3xl border">
                        <p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">Upload Date</p>
                        <p class="font-bold text-slate-700">{app_data.get('release_date', 'Recently')}</p>
                    </div>
                    <div class="bg-slate-50 p-6 rounded-3xl border">
                        <p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">App Status</p>
                        <p class="font-bold text-emerald-500 flex items-center gap-2"><i class="fas fa-check-circle"></i> Safe & Verified</p>
                    </div>
                </div>

                <a href="/get/{id}" class="inline-flex items-center gap-4 bg-indigo-600 text-white px-16 py-6 rounded-full font-black text-2xl shadow-2xl shadow-indigo-200 hover:bg-indigo-700 hover:scale-105 transition transform italic">
                    <i class="fas fa-cloud-download-alt"></i> START DOWNLOAD NOW
                </a>
            </div>
        </div>
    </div>
    """
    return render_page(content, site)

@app.route('/get/<id>')
def download_redirect(id):
    app_data = apps_col.find_one({"_id": ObjectId(id)})
    if not app_data: return redirect('/')
    cfg = get_shortener_config()
    target = app_data['download_link']
    
    if cfg.get('url') and cfg.get('api'):
        try:
            api_endpoint = f"https://{cfg['url']}/api?api={cfg['api']}&url={target}"
            res = requests.get(api_endpoint, timeout=10).json()
            short_url = res.get('shortenedUrl') or res.get('shortedUrl')
            if short_url: return redirect(short_url)
        except: pass
    return redirect(target)

# --- এডমিন অথেন্টিকেশন (HIDDEN LOGIN) ---

@app.route('/admin-gate', methods=['GET', 'POST'])
def login():
    site = get_site_branding()
    admin = users_col.find_one({"username": "admin"})
    if request.method == 'POST':
        pw = request.form.get('password')
        if not admin:
            users_col.insert_one({"username": "admin", "password": generate_password_hash(pw)})
            session['logged_in'] = True
            return redirect('/admin/dashboard')
        if check_password_hash(admin['password'], pw):
            session['logged_in'] = True
            return redirect('/admin/dashboard')
        flash("Invalid Administrative Passcode!")
    
    content = f"""
    <div class="max-w-md mx-auto mt-24 bg-white p-16 rounded-[4rem] shadow-2xl border text-center">
        <img src="{site['logo']}" class="w-20 h-20 mx-auto mb-8 rounded-2xl shadow-lg">
        <h2 class="text-3xl font-black mb-10 text-indigo-700 tracking-tighter uppercase italic underline decoration-indigo-200">System Access</h2>
        <form method="POST" class="space-y-6">
            <input type="password" name="password" placeholder="Passphrase" class="w-full bg-slate-50 p-5 rounded-2xl text-center mb-4 outline-none border focus:border-indigo-500 transition-all font-bold" required>
            <button class="btn-indigo w-full justify-center py-5 uppercase tracking-widest text-sm">Authorize Access</button>
        </form>
        <div class="mt-8 text-center"><a href="/forgot" class="text-[10px] font-bold text-slate-300 hover:text-indigo-600 uppercase tracking-widest transition">Forgot Key?</a></div>
    </div>
    """
    return render_template_string(f"<!DOCTYPE html><html><head>{UI_HEADER}</head><body class='bg-slate-50'>{content}</body></html>")

# --- এডমিন ড্যাশবোর্ড এবং ফাংশনালিটি ---

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('logged_in'): return redirect('/admin-gate')
    site = get_site_branding()
    stats = {
        "apps": apps_col.count_documents({}),
        "ads": ads_col.count_documents({}),
        "featured": apps_col.count_documents({"featured": "on"})
    }
    
    content = f"""
    <div class="mb-12">
        <h1 class="text-5xl font-black text-slate-900 tracking-tighter mb-4">Dashboard</h1>
        <p class="text-slate-400 font-bold uppercase tracking-widest text-xs">System Overview & Analysis</p>
    </div>
    
    <div class="grid grid-cols-1 md:grid-cols-3 gap-10 mb-16">
        <div class="bg-indigo-600 p-10 rounded-[3rem] text-white shadow-2xl shadow-indigo-100">
            <div class="text-6xl font-black mb-4 tracking-tighter">{stats['apps']}</div>
            <div class="font-bold uppercase text-[10px] tracking-widest opacity-80">Total Apps Live</div>
        </div>
        <div class="bg-slate-900 p-10 rounded-[3rem] text-white shadow-2xl shadow-slate-300">
            <div class="text-6xl font-black mb-4 tracking-tighter">{stats['ads']}</div>
            <div class="font-bold uppercase text-[10px] tracking-widest opacity-80">Ad Units Active</div>
        </div>
        <div class="bg-orange-500 p-10 rounded-[3rem] text-white shadow-2xl shadow-orange-100">
            <div class="text-6xl font-black mb-4 tracking-tighter">{stats['featured']}</div>
            <div class="font-bold uppercase text-[10px] tracking-widest opacity-80">Featured Slider</div>
        </div>
    </div>
    
    <div class="bg-indigo-50 p-12 rounded-[4rem] border-2 border-dashed border-indigo-200 flex items-center justify-between">
        <div class="max-w-xl">
            <h2 class="text-3xl font-black text-indigo-900 mb-4 tracking-tighter">Welcome Back, System Admin!</h2>
            <p class="text-indigo-700 text-lg font-medium">Your platform is performing efficiently. Use the left navigation to manage your applications, advertisement assets, and site-wide branding configurations.</p>
        </div>
        <i class="fas fa-rocket text-9xl text-indigo-200 hidden lg:block"></i>
    </div>
    """
    return render_page(content, site, is_admin=True, active_page="dashboard")

@app.route('/admin/apps', methods=['GET', 'POST'])
def admin_apps():
    if not session.get('logged_in'): return redirect('/admin-gate')
    site = get_site_branding()
    if request.method == 'POST':
        apps_col.insert_one({
            "name": request.form.get('name'), "logo": request.form.get('logo'),
            "category": request.form.get('category'), "release_date": request.form.get('release_date'),
            "version": request.form.get('version'), "info": request.form.get('info'),
            "download_link": request.form.get('download_link'), "featured": request.form.get('featured')
        })
        flash("Application Data Successfully Synchronized!")
        return redirect('/admin/apps')
    
    q = request.args.get('q', '')
    query = {"name": {"$regex": q, "$options": "i"}} if q else {}
    apps = list(apps_col.find(query).sort('_id', -1))
    
    apps_list_html = "".join([f'''
    <tr class="border-b last:border-0 hover:bg-slate-50 transition duration-300">
        <td class="p-6 flex items-center gap-4">
            <img src="{a['logo']}" class="w-12 h-12 rounded-xl shadow-md object-cover">
            <div>
                <p class="font-extrabold text-slate-800 leading-none mb-1">{a['name']}</p>
                <div class="flex gap-2">
                    <span class="text-[9px] font-black bg-indigo-50 text-indigo-600 px-2 py-0.5 rounded uppercase">{a['category']}</span>
                    {f'<span class="text-[9px] font-black bg-orange-400 text-white px-2 py-0.5 rounded uppercase">Featured</span>' if a.get('featured') else ''}
                </div>
            </div>
        </td>
        <td class="p-6 text-right">
            <a href="/del/app/{a['_id']}" class="text-red-500 font-bold bg-red-50 px-6 py-2.5 rounded-2xl hover:bg-red-500 hover:text-white transition" onclick="return confirm('WARNING: Permanent deletion cannot be undone. Continue?')">REMOVE</a>
        </td>
    </tr>
    ''' for a in apps])

    content = f"""
    <div class="flex flex-col md:flex-row justify-between items-center mb-10 gap-6">
        <h1 class="text-4xl font-black tracking-tighter">Manage Content</h1>
        <form class="bg-white px-8 py-3 rounded-full border flex items-center w-full md:w-96 shadow-sm">
            <input type="text" name="q" placeholder="Search and edit apps..." class="bg-transparent outline-none text-sm w-full font-medium" value="{q}">
            <button type="submit"><i class="fas fa-search text-indigo-600"></i></button>
        </form>
    </div>

    <div class="grid lg:grid-cols-3 gap-12">
        <div class="bg-white p-10 rounded-[3.5rem] shadow-sm border border-slate-100 h-fit sticky top-28">
            <h2 class="text-2xl font-black mb-8 text-indigo-700 italic border-b pb-4">New Upload</h2>
            <form method="POST" class="space-y-4">
                <input name="name" placeholder="App Title" class="w-full" required>
                <input name="logo" placeholder="Icon URL (Direct Link)" class="w-full" required>
                <select name="category" class="w-full"><option>Mobile</option><option>Desktop</option><option>iOS</option></select>
                <div class="flex gap-2"><input type="date" name="release_date" class="w-1/2" required><input name="version" placeholder="v1.0" class="w-1/2 font-bold" required></div>
                <textarea name="info" placeholder="Short Meta Info..." class="w-full h-28" required></textarea>
                <input name="download_link" placeholder="Main Destination URL" class="w-full" required>
                <label class="flex items-center gap-3 font-extrabold text-indigo-600 p-2 cursor-pointer">
                    <input type="checkbox" name="featured" class="w-6 h-6 rounded-lg accent-indigo-600"> Highlight in Hero Slider
                </label>
                <button class="btn-indigo w-full justify-center py-4 uppercase text-sm tracking-widest mt-4">PUBLISH CONTENT</button>
            </form>
        </div>
        <div class="lg:col-span-2 bg-white rounded-[3.5rem] border border-slate-100 overflow-hidden shadow-sm">
            <table class="w-full text-left">
                <thead class="bg-slate-50 border-b"><tr><th class="p-6 font-bold text-slate-400 uppercase text-xs tracking-widest">Entry Details</th><th class="p-6 text-right font-bold text-slate-400 uppercase text-xs tracking-widest">Operations</th></tr></thead>
                <tbody>{apps_list_html if apps_list_html else '<tr><td colspan="2" class="p-20 text-center font-bold text-slate-300">No Apps Found In Database.</td></tr>'}</tbody>
            </table>
        </div>
    </div>
    """
    return render_page(content, site, is_admin=True, active_page="apps")

@app.route('/admin/ads', methods=['GET', 'POST'])
def admin_ads():
    if not session.get('logged_in'): return redirect('/admin-gate')
    site = get_site_branding()
    if request.method == 'POST':
        ads_col.insert_one({"name": request.form.get('name'), "code": request.form.get('code')})
        flash("Advertisement Snippet Deployed Successfully!")
        return redirect('/admin/ads')
    
    ads_list_html = "".join([f'''
    <div class="flex justify-between items-center p-8 bg-white border border-slate-100 rounded-[2.5rem] shadow-sm hover:shadow-xl transition group">
        <div class="flex items-center gap-6">
            <div class="w-14 h-14 bg-emerald-100 text-emerald-600 rounded-2xl flex items-center justify-center text-xl shadow-inner group-hover:bg-emerald-600 group-hover:text-white transition duration-500"><i class="fas fa-ad"></i></div>
            <div>
                <p class="font-black text-slate-800 text-xl tracking-tighter mb-1 leading-none uppercase">{ad['name']}</p>
                <p class="text-[10px] font-black text-emerald-500 uppercase tracking-widest italic">Live & Monetized</p>
            </div>
        </div>
        <a href="/del/ad/{ad['_id']}" class="text-red-500 font-black text-xs bg-red-50 px-8 py-3 rounded-2xl hover:bg-red-500 hover:text-white transition">DISABLE UNIT</a>
    </div>
    ''' for ad in ads_col.find()])

    content = f"""
    <h1 class="text-5xl font-black mb-12 tracking-tighter">Monetization Center</h1>
    <div class="grid lg:grid-cols-3 gap-12">
        <form method="POST" class="bg-white p-10 rounded-[3.5rem] space-y-5 border border-slate-100 shadow-sm h-fit">
            <h2 class="text-2xl font-black mb-6 text-emerald-600 underline decoration-emerald-200 italic">Inject Ad Code</h2>
            <input name="name" placeholder="Ad Unit Name (e.g. Header)" class="w-full font-bold" required>
            <textarea name="code" placeholder="Paste full HTML/JS Script here..." class="w-full h-64 font-mono text-xs focus:ring-4 ring-emerald-500/10 border-emerald-100" required></textarea>
            <button class="btn-indigo bg-emerald-600 hover:bg-emerald-700 w-full justify-center py-4 uppercase text-sm tracking-widest shadow-emerald-100">DEPLOY SCRIPT</button>
        </form>
        <div class="lg:col-span-2 space-y-6">
            {ads_list_html if ads_list_html else '<div class="p-20 text-center text-slate-300 font-bold bg-white rounded-[3rem] border">No Active Ad Units Configured.</div>'}
        </div>
    </div>
    """
    return render_page(content, site, is_admin=True, active_page="ads")

@app.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    if not session.get('logged_in'): return redirect('/admin-gate')
    site = get_site_branding()
    if request.method == 'POST':
        ftype = request.form.get('type')
        if ftype == 'site':
            settings_col.update_one({"type": "branding"}, {"$set": {"name": request.form.get('name'), "title": request.form.get('title'), "logo": request.form.get('logo')}}, upsert=True)
            flash("System Branding Updated & Assets Synchronized!")
        else:
            settings_col.update_one({"type": "shortener"}, {"$set": {"url": request.form.get('url'), "api": request.form.get('api')}}, upsert=True)
            flash("External API Configuration Active!")
        return redirect('/admin/settings')

    cfg = get_shortener_config()
    content = f"""
    <h1 class="text-5xl font-black mb-12 tracking-tighter uppercase italic">System Configuration</h1>
    <div class="grid md:grid-cols-2 gap-12">
        <div class="bg-white p-12 rounded-[4rem] border border-slate-100 shadow-sm space-y-10">
            <h2 class="text-3xl font-black text-indigo-700 underline decoration-indigo-200">Site Branding</h2>
            <form method="POST" class="space-y-6">
                <input type="hidden" name="type" value="site">
                <div>
                    <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-2 mb-2 block">Brand Identity Name</label>
                    <input name="name" value="{site['name']}" class="w-full font-black text-2xl uppercase tracking-tighter" required>
                </div>
                <div>
                    <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-2 mb-2 block">Meta Title Header</label>
                    <input name="title" value="{site['title']}" class="w-full" required>
                </div>
                <div>
                    <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-2 mb-2 block">Brand Logo Asset URL</label>
                    <input name="logo" value="{site['logo']}" class="w-full" required>
                </div>
                <button class="btn-indigo w-full justify-center py-5 uppercase text-sm tracking-widest shadow-indigo-100">Update Platform Assets</button>
            </form>
        </div>
        <div class="bg-slate-900 p-12 rounded-[4rem] shadow-2xl space-y-10 text-white">
            <h2 class="text-3xl font-black text-emerald-400 underline decoration-emerald-900">Link Shortener</h2>
            <form method="POST" class="space-y-6">
                <input type="hidden" name="type" value="short">
                <div>
                    <label class="text-[10px] font-black text-slate-600 uppercase tracking-widest ml-2 mb-2 block">API Gateway Domain</label>
                    <input name="url" value="{cfg.get('url','')}" placeholder="e.g. sjjdjdjdjdj.xyz" class="w-full bg-slate-800 border-slate-700 text-white outline-none focus:ring-1 ring-emerald-400" required>
                </div>
                <div>
                    <label class="text-[10px] font-black text-slate-600 uppercase tracking-widest ml-2 mb-2 block">Personal API Access Token</label>
                    <input type="password" name="api" value="{cfg.get('api','')}" class="w-full bg-slate-800 border-slate-700 text-white outline-none focus:ring-1 ring-emerald-400" required>
                </div>
                <button class="w-full bg-emerald-500 text-slate-900 py-5 rounded-[2rem] font-black text-sm uppercase tracking-widest hover:bg-emerald-400 transition shadow-2xl shadow-emerald-900/40">Apply Configuration</button>
            </form>
            <p class="text-center text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em]">Automated Redirect System powered by API</p>
        </div>
    </div>
    """
    return render_page(content, site, is_admin=True, active_page="settings")

# --- অথেন্টিকেশন এবং হেল্পার রাউটস ---

@app.route('/forgot', methods=['GET', 'POST'])
def forgot():
    if request.method == 'POST':
        if request.form.get('key') == RECOVERY_KEY:
            users_col.update_one({"username": "admin"}, {"$set": {"password": generate_password_hash(request.form.get('pw'))}}, upsert=True)
            flash("System Credential Override Successful!")
            return redirect('/admin-gate')
        flash("Authorization Denied: Recovery Token Invalid!")
    
    content = f"""
    <div class="max-w-md mx-auto mt-32 bg-white p-16 rounded-[4rem] shadow-2xl border border-red-50 text-center">
        <h2 class="text-2xl font-black mb-10 text-red-600 tracking-widest uppercase italic underline">Master Reset</h2>
        <form method="POST" class="space-y-6">
            <input name="key" placeholder="System Security Token" class="w-full border-none bg-slate-50 p-5 rounded-2xl text-center outline-none focus:ring-4 ring-red-500/10" required>
            <input type="password" name="pw" placeholder="New Master Passcode" class="w-full border-none bg-slate-50 p-5 rounded-2xl text-center outline-none focus:ring-4 ring-red-500/10" required>
            <button class="bg-red-600 text-white py-5 w-full rounded-2xl font-black text-sm uppercase tracking-widest shadow-2xl shadow-red-200 hover:bg-red-700 transition">Update System Access</button>
        </form>
    </div>
    """
    return render_template_string(f"<!DOCTYPE html><html><head>{UI_HEADER}</head><body class='bg-slate-50'>{content}</body></html>")

@app.route('/del/<type>/<id>')
def delete_entry(type, id):
    if not session.get('logged_in'): return redirect('/admin-gate')
    if type == 'app': apps_col.delete_one({"_id": ObjectId(id)})
    if type == 'ad': ads_col.delete_one({"_id": ObjectId(id)})
    flash("Entry Purged Permanently.")
    return redirect(request.referrer)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# --- Vercel ডেপলয়মেন্ট হ্যান্ডলার ---
handler = app

if __name__ == '__main__':
    app.run(debug=True)
