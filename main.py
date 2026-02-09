import os
import requests
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# --- কনফিগারেশন ও ডাটাবেজ ---
# Vercel Environment Variables থেকে এই মানগুলো সেট করে নেবেন
app.secret_key = os.environ.get("SESSION_SECRET", "super_secret_key_v100_pro")
RECOVERY_KEY = os.environ.get("RECOVERY_KEY", "admin@2024")

# MongoDB কানেকশন স্ট্রিং
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster"
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client['app_hub_final_v10']
apps_col = db['apps']
users_col = db['users']
ads_col = db['ads']
settings_col = db['settings']

# --- সাইটের ডাইনামিক তথ্য নিয়ে আসার ফাংশন ---
def get_site_info():
    info = settings_col.find_one({"type": "site_info"})
    if not info:
        return {"name": "APPHUB", "title": "Ultimate App Store", "logo": "https://cdn-icons-png.flaticon.com/512/2589/2589127.png"}
    return info

# --- সিএসএস এবং মেইন ডিজাইন লেআউট ---
UI_STYLE = """
<script src="https://cdn.tailwindcss.com"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swiper@10/swiper-bundle.min.css" />
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;700;800&display=swap');
    body { font-family: 'Plus Jakarta Sans', sans-serif; background: #f8fafc; }
    .swiper { width: 100%; height: 380px; border-radius: 2.5rem; overflow: hidden; margin-bottom: 3rem; }
    .sidebar-active { background: #4f46e5; color: white !important; border-radius: 1rem; box-shadow: 0 10px 15px -3px rgba(79, 70, 229, 0.4); }
    .line-clamp-2 { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
</style>
"""

def base_layout(content, site, is_admin=False, active_page=""):
    header = ""
    if not is_admin:
        header = f'''<nav class="bg-white border-b sticky top-0 z-50 h-20 flex items-center shadow-sm">
            <div class="container mx-auto px-6 flex items-center justify-between">
                <a href="/" class="text-3xl font-extrabold text-indigo-600 tracking-tighter uppercase">{site['name']}</a>
                <form action="/" method="GET" class="hidden md:flex bg-gray-100 rounded-2xl px-5 py-2 items-center border border-gray-200">
                    <input type="text" name="q" placeholder="Search apps..." class="bg-transparent outline-none text-sm w-72">
                    <button type="submit"><i class="fas fa-search text-gray-400"></i></button>
                </form>
                <div class="text-[10px] font-black bg-gray-900 text-white px-3 py-1 rounded-full uppercase">PRO VERSION</div>
            </div></nav>'''
    
    return f"""
    <!DOCTYPE html><html lang="en">
    <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{site['name']} - {site['title']}</title>{UI_STYLE}</head>
    <body class="bg-slate-50">
        {header}
        <div class="{'flex min-h-screen' if is_admin else 'container mx-auto px-6 py-10'}">
            {content}
        </div>
        <script src="https://cdn.jsdelivr.net/npm/swiper@10/swiper-bundle.min.js"></script>
        <script>const swiper = new Swiper('.swiper', {{ loop: true, autoplay: {{ delay: 3500 }}, pagination: {{ el: '.swiper-pagination', clickable: true }} }});</script>
    </body></html>
    """

# --- ইউজার প্যানেল রাউটস ---

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
    
    ads_html = "".join([f'<div class="bg-white p-3 rounded-2xl shadow-sm border flex justify-center mb-6 overflow-hidden">{ad["code"]}</div>' for ad in ads_col.find()])
    
    featured_html = ""
    if featured:
        slides = "".join([f'''<div class="swiper-slide bg-indigo-900 flex items-center p-12 text-white relative overflow-hidden">
            <div class="z-10 max-w-xl">
                <span class="bg-indigo-500 text-[10px] font-bold px-3 py-1 rounded-full uppercase mb-4 inline-block tracking-widest">Featured App</span>
                <h2 class="text-5xl font-black mb-6 leading-tight">{f['name']}</h2>
                <a href="/app/{f['_id']}" class="bg-white text-indigo-900 px-10 py-4 rounded-full font-black text-xl shadow-2xl transition hover:bg-indigo-50">Details</a>
            </div>
            <img src="{f['logo']}" class="absolute right-20 w-56 h-56 rounded-[3.5rem] opacity-60 shadow-2xl hidden md:block rotate-12">
        </div>''' for f in featured])
        featured_html = f'<div class="swiper"><div class="swiper-wrapper">{slides}</div><div class="swiper-pagination"></div></div>'

    apps_html = "".join([f'''<a href="/app/{a['_id']}" class="bg-white p-8 rounded-[3rem] border border-gray-100 shadow-sm hover:shadow-2xl transition duration-500 text-center group">
        <img src="{a['logo']}" class="w-24 h-24 rounded-[2rem] mx-auto mb-5 shadow-lg group-hover:scale-110 transition duration-500">
        <h3 class="font-extrabold text-xl text-gray-800 mb-2 truncate px-2">{a['name']}</h3>
        <p class="text-xs font-bold text-indigo-500 uppercase mb-5 tracking-tighter">{a['category']} • V{a['version']}</p>
        <div class="bg-gray-50 text-indigo-600 py-3 rounded-2xl font-black group-hover:bg-indigo-600 group-hover:text-white transition uppercase">Download</div>
    </a>''' for a in apps])

    content = f"""
    {featured_html}
    <div class="mb-10">{ads_html}</div>
    <div class="flex justify-between items-center mb-10"><h2 class="text-3xl font-black text-gray-800 uppercase italic">{'Results' if q else 'Latest Uploads'}</h2></div>
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-10">{apps_html}</div>
    """
    return base_layout(content, site)

@app.route('/app/<id>')
def details(id):
    site = get_site_info()
    app_data = apps_col.find_one({"_id": ObjectId(id)})
    if not app_data: return redirect('/')
    content = f"""
    <div class="max-w-5xl mx-auto bg-white rounded-[4rem] shadow-2xl p-12 flex flex-col md:flex-row gap-12 items-center border border-gray-100">
        <img src="{app_data['logo']}" class="w-64 h-64 rounded-[4rem] shadow-2xl">
        <div class="flex-1 text-center md:text-left">
            <h1 class="text-5xl font-black text-gray-800 mb-6 tracking-tighter">{app_data['name']}</h1>
            <div class="flex flex-wrap gap-2 mb-8 justify-center md:justify-start uppercase font-bold text-xs tracking-widest">
                <span class="bg-indigo-600 text-white px-5 py-2 rounded-full">{app_data['category']}</span>
                <span class="bg-gray-100 text-gray-500 px-5 py-2 rounded-full">Version {app_data['version']}</span>
            </div>
            <p class="text-gray-500 text-lg leading-relaxed mb-10">{app_data['info']}</p>
            <a href="/get/{id}" class="inline-block bg-indigo-600 text-white px-16 py-6 rounded-full font-black text-2xl shadow-2xl shadow-indigo-200 hover:scale-105 transition italic uppercase">Get APK Now</a>
        </div>
    </div>
    """
    return base_layout(content, site)

@app.route('/get/<id>')
def download(id):
    app_data = apps_col.find_one({"_id": ObjectId(id)})
    cfg = settings_col.find_one({"type": "shortener"})
    url = app_data['download_link']
    if cfg and cfg.get('url') and cfg.get('api'):
        try:
            res = requests.get(f"https://{cfg['url']}/api?api={cfg['api']}&url={url}", timeout=10).json()
            short = res.get('shortenedUrl') or res.get('shortedUrl')
            if short: return redirect(short)
        except: pass
    return redirect(url)

# --- এডমিন প্যানেল (লগইন ও ড্যাশবোর্ড) ---

@app.route('/admin-gate', methods=['GET', 'POST'])
def login():
    site = get_site_info()
    admin_u = users_col.find_one({"username": "admin"})
    if request.method == 'POST':
        pw = request.form.get('password')
        if not admin_u:
            users_col.insert_one({"username": "admin", "password": generate_password_hash(pw)})
            session['logged_in'] = True
            return redirect('/admin/dashboard')
        if check_password_hash(admin_u['password'], pw):
            session['logged_in'] = True
            return redirect('/admin/dashboard')
        flash("Wrong Password!")
    content = f"""<div class="max-w-sm mx-auto mt-32 bg-white p-16 rounded-[4rem] shadow-2xl border text-center">
        <h2 class="text-3xl font-black mb-10 text-indigo-700 italic tracking-tighter">AUTHENTICATION</h2>
        <form method="POST">
            <input type="password" name="password" class="w-full bg-gray-50 p-4 rounded-2xl text-center mb-8 border outline-none focus:ring-2 ring-indigo-500" placeholder="Secret Key" required>
            <button class="w-full bg-indigo-600 text-white py-4 rounded-2xl font-black shadow-lg">LOG IN</button>
        </form>
        <a href="/forgot" class="text-[10px] text-gray-300 block mt-8 hover:text-indigo-600 uppercase font-bold tracking-widest">Forgot Password?</a>
    </div>"""
    return base_layout(content, site)

@app.route('/admin/dashboard')
def dashboard():
    if not session.get('logged_in'): return redirect('/admin-gate')
    site = get_site_info()
    stats = {"apps": apps_col.count_documents({}), "ads": ads_col.count_documents({}), "featured": apps_col.count_documents({"featured": "on"})}
    content = f"""{get_admin_sidebar(site, 'dashboard')}
    <div class="flex-1 p-12 overflow-y-auto">
        <h1 class="text-5xl font-black mb-12 tracking-tighter uppercase italic">System Stats</h1>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-10 mb-12">
            <div class="bg-indigo-600 p-12 rounded-[3.5rem] text-white shadow-2xl shadow-indigo-100">
                <div class="text-7xl font-black mb-2 tracking-tighter">{stats['apps']}</div><div class="font-bold text-xs uppercase opacity-70">Total Apps</div>
            </div>
            <div class="bg-slate-900 p-12 rounded-[3.5rem] text-white shadow-2xl shadow-slate-300">
                <div class="text-7xl font-black mb-2">{stats['ads']}</div><div class="font-bold text-xs uppercase opacity-70">Ad Units</div>
            </div>
            <div class="bg-orange-500 p-12 rounded-[3.5rem] text-white shadow-2xl shadow-orange-100">
                <div class="text-7xl font-black mb-2">{stats['featured']}</div><div class="font-bold text-xs uppercase opacity-70">Slider Apps</div>
            </div>
        </div>
        <div class="bg-indigo-50 p-10 rounded-[3rem] border-2 border-dashed border-indigo-200">
            <h2 class="text-2xl font-black text-indigo-900 mb-3">Welcome Back, Admin!</h2>
            <p class="text-indigo-700">Everything is running optimally. Total system assets are safe in MongoDB Atlas.</p>
        </div>
    </div>"""
    return base_layout(content, site, True)

@app.route('/admin/apps', methods=['GET', 'POST'])
def admin_apps():
    if not session.get('logged_in'): return redirect('/admin-gate')
    site = get_site_info()
    if request.method == 'POST':
        apps_col.insert_one({"name": request.form.get('name'), "logo": request.form.get('logo'), "category": request.form.get('category'), "version": request.form.get('version'), "info": request.form.get('info'), "download_link": request.form.get('download_link'), "featured": request.form.get('featured')})
        flash("App Published!")
    
    q = request.args.get('q', '')
    query = {"name": {"$regex": q, "$options": "i"}} if q else {}
    apps = list(apps_col.find(query).sort('_id', -1))
    
    apps_list = "".join([f'''<tr class="border-b"><td class="p-4 flex items-center gap-3"><img src="{a['logo']}" class="w-10 h-10 rounded-lg shadow-sm"><div><b class="text-slate-800">{a['name']}</b> <br> <small class="text-gray-400 font-bold uppercase text-[9px]">{a['category']}</small></div></td><td class="p-4 text-right"><a href="/del/app/{a['_id']}" class="text-red-500 font-bold bg-red-50 px-5 py-2 rounded-xl transition hover:bg-red-500 hover:text-white">Delete</a></td></tr>''' for a in apps])
    
    content = f"""{get_admin_sidebar(site, 'apps')}
    <div class="flex-1 p-12 overflow-y-auto">
        <div class="flex justify-between items-center mb-10">
            <h1 class="text-3xl font-black">Manage Applications</h1>
            <form class="bg-gray-100 rounded-full px-5 py-2 flex items-center border shadow-inner"><input name="q" placeholder="Search..." class="bg-transparent outline-none w-56 text-sm font-bold" value="{q}"><button><i class="fas fa-search text-indigo-600"></i></button></form>
        </div>
        <div class="grid lg:grid-cols-3 gap-10">
            <form method="POST" class="bg-white p-10 rounded-[3rem] shadow-sm border space-y-4">
                <h2 class="font-black text-indigo-600 uppercase text-xs mb-6 underline">New Upload</h2>
                <input name="name" placeholder="Name" class="w-full p-4 rounded-2xl border outline-none focus:ring-2 ring-indigo-500" required>
                <input name="logo" placeholder="Logo URL" class="w-full p-4 rounded-2xl border outline-none focus:ring-2 ring-indigo-500" required>
                <select name="category" class="w-full p-4 rounded-2xl border outline-none"><option>Mobile</option><option>PC</option><option>iOS</option></select>
                <input name="version" placeholder="Version (v1.0)" class="w-full p-4 rounded-2xl border outline-none" required>
                <textarea name="info" placeholder="Short description..." class="w-full p-4 rounded-2xl border h-28 outline-none" required></textarea>
                <input name="download_link" placeholder="Main Download Redirect URL" class="w-full p-4 rounded-2xl border outline-none" required>
                <label class="flex items-center gap-2 font-bold text-indigo-600 cursor-pointer"><input type="checkbox" name="featured" class="w-5 h-5 accent-indigo-600"> Highlight in Slider</label>
                <button class="w-full bg-indigo-600 text-white py-4 rounded-2xl font-black shadow-lg shadow-indigo-100 hover:bg-indigo-700">PUBLISH APP</button>
            </form>
            <div class="lg:col-span-2 bg-white rounded-[3rem] border shadow-sm overflow-hidden"><table class="w-full text-left"><tbody>{apps_list}</tbody></table></div>
        </div>
    </div>"""
    return base_layout(content, site, True)

@app.route('/admin/ads', methods=['GET', 'POST'])
def admin_ads():
    if not session.get('logged_in'): return redirect('/admin-gate')
    site = get_site_info()
    if request.method == 'POST':
        ads_col.insert_one({"name": request.form.get('name'), "code": request.form.get('code')})
        flash("Ad Injected!")
    
    ads_list = "".join([f'<div class="flex justify-between items-center p-6 border-b last:border-0"><div><b class="text-slate-800">{ad["name"]}</b> <br> <span class="text-[9px] text-green-500 font-black">STATUS: LIVE</span></div><a href="/del/ad/{ad["_id"]}" class="text-red-500 font-bold bg-red-50 px-6 py-2 rounded-2xl transition hover:bg-red-500 hover:text-white">Remove</a></div>' for ad in ads_col.find()])
    
    content = f"""{get_admin_sidebar(site, 'ads')}
    <div class="flex-1 p-12">
        <h1 class="text-3xl font-black mb-10">Advertisement Manager</h1>
        <form method="POST" class="max-w-3xl bg-white p-10 rounded-[3rem] border mb-10 space-y-5 shadow-sm">
            <input name="name" placeholder="Ad Spot Label (e.g. Header)" class="w-full p-4 rounded-2xl border focus:ring-2 ring-indigo-500 outline-none" required>
            <textarea name="code" placeholder="Paste HTML/JS Script Code" class="w-full p-4 rounded-2xl border h-44 font-mono text-xs outline-none" required></textarea>
            <button class="bg-indigo-600 text-white px-10 py-4 rounded-2xl font-black shadow-lg">SAVE AD UNIT</button>
        </form>
        <div class="bg-white rounded-[3rem] border shadow-sm overflow-hidden">{ads_list}</div>
    </div>"""
    return base_layout(content, site, True)

@app.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    if not session.get('logged_in'): return redirect('/admin-gate')
    site = get_site_info()
    if request.method == 'POST':
        ftype = request.form.get('type')
        if ftype == 'site':
            settings_col.update_one({"type": "site_info"}, {"$set": {"name": request.form.get('name'), "title": request.form.get('title')}}, upsert=True)
            flash("Branding Updated!")
        else:
            settings_col.update_one({"type": "shortener"}, {"$set": {"url": request.form.get('url'), "api": request.form.get('api')}}, upsert=True)
            flash("API Configured!")
        return redirect('/admin/settings')

    curr = settings_col.find_one({"type": "shortener"}) or {}
    content = f"""{get_admin_sidebar(site, 'settings')}
    <div class="flex-1 p-12 space-y-12">
        <h1 class="text-3xl font-black mb-10 tracking-tighter uppercase italic">Site Settings</h1>
        <div class="grid md:grid-cols-2 gap-12">
            <form method="POST" class="bg-white p-12 rounded-[4rem] border shadow-sm space-y-5">
                <h2 class="text-2xl font-black mb-4">Site Branding</h2>
                <input type="hidden" name="type" value="site">
                <div><label class="text-[9px] font-bold text-gray-400 uppercase ml-2">App Name</label>
                <input name="name" value="{site['name']}" class="w-full p-5 rounded-2xl border font-black text-2xl uppercase tracking-tighter" placeholder="Site Name"></div>
                <div><label class="text-[9px] font-bold text-gray-400 uppercase ml-2">Browser Title</label>
                <input name="title" value="{site['title']}" class="w-full p-5 rounded-2xl border" placeholder="Meta Title"></div>
                <button class="w-full bg-indigo-600 text-white py-5 rounded-[2rem] font-black shadow-xl">UPDATE BRANDING</button>
            </form>
            <form method="POST" class="bg-gray-900 p-12 rounded-[4rem] shadow-2xl space-y-5 text-white">
                <h2 class="text-2xl font-black mb-4 text-emerald-400">URL Shortener API</h2>
                <input type="hidden" name="type" value="short">
                <div><label class="text-[9px] font-bold text-gray-500 uppercase ml-2">Domain (site.xyz)</label>
                <input name="url" value="{curr.get('url','')}" class="w-full p-5 rounded-2xl border border-gray-800 bg-gray-800 text-white outline-none focus:ring-1 ring-emerald-400" placeholder="Domain"></div>
                <div><label class="text-[9px] font-bold text-gray-500 uppercase ml-2">API Secret Token</label>
                <input name="api" value="{curr.get('api','')}" class="w-full p-5 rounded-2xl border border-gray-800 bg-gray-800 text-white outline-none focus:ring-1 ring-emerald-400" placeholder="API Key"></div>
                <button class="w-full bg-emerald-500 text-gray-900 py-5 rounded-[2rem] font-black">SAVE API CONFIG</button>
            </form>
        </div>
    </div>"""
    return base_layout(content, site, True)

def get_admin_sidebar(site, active):
    return f"""
    <div class="w-72 bg-gray-950 text-gray-400 p-10 space-y-3 flex flex-col h-screen sticky top-0 shadow-2xl">
        <div class="text-3xl font-black text-white mb-10 italic uppercase tracking-tighter border-b border-gray-900 pb-5">{site['name']}</div>
        <a href="/admin/dashboard" class="p-4 rounded-2xl flex items-center gap-4 transition-all {'sidebar-active' if active=='dashboard' else 'hover:bg-gray-900 hover:text-white'}"><i class="fas fa-chart-line"></i> Dashboard</a>
        <a href="/admin/apps" class="p-4 rounded-2xl flex items-center gap-4 transition-all {'sidebar-active' if active=='apps' else 'hover:bg-gray-900 hover:text-white'}"><i class="fas fa-mobile-alt"></i> Apps</a>
        <a href="/admin/ads" class="p-4 rounded-2xl flex items-center gap-4 transition-all {'sidebar-active' if active=='ads' else 'hover:bg-gray-900 hover:text-white'}"><i class="fas fa-ad"></i> Ad Manager</a>
        <a href="/admin/settings" class="p-4 rounded-2xl flex items-center gap-4 transition-all {'sidebar-active' if active=='settings' else 'hover:bg-gray-900 hover:text-white'}"><i class="fas fa-tools"></i> Settings</a>
        <div class="flex-1"></div>
        <a href="/logout" class="text-red-400 font-black p-4 bg-red-900/10 rounded-2xl hover:bg-red-900/30 transition text-center uppercase tracking-widest text-xs">Logout</a>
    </div>"""

@app.route('/forgot', methods=['GET', 'POST'])
def forgot():
    if request.method == 'POST':
        if request.form.get('key') == RECOVERY_KEY:
            users_col.update_one({"username": "admin"}, {"$set": {"password": generate_password_hash(request.form.get('pw'))}}, upsert=True)
            flash("Override Success! Log in.")
            return redirect('/admin-gate')
        flash("Incorrect Recovery Key!")
    content = f"""<div class="max-w-sm mx-auto mt-32 bg-white p-16 rounded-[4rem] shadow-2xl border text-center">
    <h2 class="text-2xl font-bold text-red-600 mb-8 uppercase tracking-widest italic underline">Critical Reset</h2>
    <form method="POST" class="space-y-4">
        <input name="key" placeholder="System Secret Key" class="w-full p-4 border rounded-2xl outline-none focus:ring-1 ring-red-500" required>
        <input name="pw" placeholder="New Master PW" class="w-full p-4 border rounded-2xl outline-none focus:ring-1 ring-red-500" required>
        <button class="bg-red-600 text-white py-4 w-full rounded-2xl font-black shadow-xl">OVERRIDE SYSTEM</button>
    </form></div>"""
    return base_layout(content, get_site_info())

@app.route('/del/<type>/<id>')
def delete(type, id):
    if not session.get('logged_in'): return redirect('/admin-gate')
    if type == 'app': apps_col.delete_one({"_id": ObjectId(id)})
    if type == 'ad': ads_col.delete_one({"_id": ObjectId(id)})
    flash("Permanent Removal Done.")
    return redirect(request.referrer)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# Vercel Deployment Export
handler = app
if __name__ == '__main__':
    app.run(debug=True)
