import os
import requests
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# --- কনফিগারেশন ---
app.secret_key = os.environ.get("SESSION_SECRET", "super_secret_99887766")
RECOVERY_KEY = os.environ.get("RECOVERY_KEY", "admin@secret")

# --- MongoDB কানেকশন ---
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster"
client = MongoClient(MONGO_URI)
db = client['app_hub_ultimate_v3']
apps_col = db['apps']
users_col = db['users']
ads_col = db['ads']
settings_col = db['settings']

# --- এইচটিএমএল ডিজাইন (Tailwind CSS) ---
BASE_LAYOUT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>App Hub Pro</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        .sidebar-active { background: #4f46e5; color: white; }
        .line-clamp-3 { display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
    </style>
</head>
<body class="bg-slate-50 font-sans antialiased text-slate-900">
    {% if not is_admin_route %}
    <!-- User Navbar -->
    <nav class="bg-white border-b sticky top-0 z-50">
        <div class="container mx-auto px-4 h-16 flex items-center justify-between">
            <a href="/" class="text-2xl font-black text-indigo-600">APP<span class="text-slate-800">HUB</span></a>
            <div class="flex items-center gap-4">
                <form action="/" method="GET" class="hidden md:flex bg-slate-100 rounded-full px-4 py-1.5 items-center">
                    <input type="text" name="q" placeholder="Search apps..." class="bg-transparent outline-none text-sm w-48">
                    <button type="submit"><i class="fas fa-search text-slate-400"></i></button>
                </form>
                <a href="/login" class="text-sm font-bold text-indigo-600 border border-indigo-600 px-4 py-1.5 rounded-full hover:bg-indigo-600 hover:text-white transition">Admin</a>
            </div>
        </div>
    </nav>
    {% endif %}

    <div class="{% if is_admin_route %}flex min-h-screen{% else %}container mx-auto px-4 py-8{% endif %}">
        {% if is_admin_route %}
        <!-- Admin Sidebar -->
        <div class="w-64 bg-slate-900 text-slate-300 flex flex-col">
            <div class="p-6 text-2xl font-black text-white border-b border-slate-800 italic">ADMIN PANEL</div>
            <div class="flex-1 p-4 space-y-2">
                <a href="/admin/dashboard" class="flex items-center gap-3 p-3 rounded-xl hover:bg-slate-800 transition {{ 'sidebar-active' if active_page == 'dashboard' }}">
                    <i class="fas fa-chart-line w-5"></i> Dashboard
                </a>
                <a href="/admin/apps" class="flex items-center gap-3 p-3 rounded-xl hover:bg-slate-800 transition {{ 'sidebar-active' if active_page == 'apps' }}">
                    <i class="fas fa-mobile-screen w-5"></i> Manage Apps
                </a>
                <a href="/admin/ads" class="flex items-center gap-3 p-3 rounded-xl hover:bg-slate-800 transition {{ 'sidebar-active' if active_page == 'ads' }}">
                    <i class="fas fa-ad w-5"></i> Ad Manager
                </a>
                <a href="/admin/settings" class="flex items-center gap-3 p-3 rounded-xl hover:bg-slate-800 transition {{ 'sidebar-active' if active_page == 'settings' }}">
                    <i class="fas fa-cog w-5"></i> API Settings
                </a>
                <div class="pt-10">
                    <a href="/" class="flex items-center gap-3 p-3 rounded-xl hover:bg-slate-800 text-emerald-400">
                        <i class="fas fa-eye"></i> View Site
                    </a>
                    <a href="/logout" class="flex items-center gap-3 p-3 rounded-xl hover:bg-red-900 text-red-400">
                        <i class="fas fa-sign-out-alt"></i> Logout
                    </a>
                </div>
            </div>
        </div>
        <div class="flex-1 p-8 overflow-y-auto">
            {% with messages = get_flashed_messages() %}{% for msg in messages %}
                <div class="bg-indigo-600 text-white p-4 rounded-xl mb-6 shadow-lg shadow-indigo-100 flex justify-between items-center">
                    <span>{{ msg }}</span>
                    <button onclick="this.parentElement.remove()"><i class="fas fa-times"></i></button>
                </div>
            {% endfor %}{% endwith %}
            {% block admin_content %}{% endblock %}
        </div>
        {% else %}
            {% with messages = get_flashed_messages() %}{% for msg in messages %}
                <div class="bg-indigo-100 text-indigo-700 p-4 rounded-xl mb-6 border-l-4 border-indigo-600">{{ msg }}</div>
            {% endfor %}{% endwith %}
            {% block content %}{% endblock %}
        {% endif %}
    </div>
</body>
</html>
"""

# --- USER ROUTES ---

@app.route('/')
def home():
    query = request.args.get('q', '')
    if query:
        apps = list(apps_col.find({"name": {"$regex": query, "$options": "i"}}).sort('_id', -1))
    else:
        apps = list(apps_col.find().sort('_id', -1))
    
    ads = list(ads_col.find())
    
    content = """
    <!-- Ads Top -->
    <div class="mb-10 space-y-4">
        {% for ad in ads %}
            <div class="bg-white p-2 rounded-xl shadow-sm border flex justify-center overflow-hidden">{{ ad.code | safe }}</div>
        {% endfor %}
    </div>

    <!-- User Search Mobile -->
    <form action="/" method="GET" class="md:hidden mb-6 flex bg-white border rounded-xl px-4 py-3 items-center">
        <input type="text" name="q" placeholder="Search apps..." class="flex-1 outline-none">
        <button type="submit"><i class="fas fa-search text-indigo-600"></i></button>
    </form>

    <div class="flex justify-between items-center mb-8">
        <h2 class="text-2xl font-black text-slate-800">{% if q %}Search Results for "{{q}}"{% else %}Featured Apps{% endif %}</h2>
        <span class="text-sm font-bold text-slate-400">{{ apps|length }} Apps Found</span>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {% for app in apps %}
        <a href="/app/{{app._id}}" class="bg-white p-6 rounded-[2.5rem] border border-slate-100 shadow-sm hover:shadow-xl hover:-translate-y-1 transition duration-300 group">
            <div class="flex flex-col items-center">
                <img src="{{app.logo}}" class="w-24 h-24 rounded-3xl mb-4 shadow-lg group-hover:scale-110 transition duration-500">
                <h3 class="font-bold text-lg text-slate-800 text-center">{{app.name}}</h3>
                <div class="flex gap-2 my-2">
                    <span class="text-[10px] bg-indigo-50 text-indigo-600 px-2 py-0.5 rounded-full font-bold uppercase">{{app.category}}</span>
                    <span class="text-[10px] bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full font-bold">V {{app.version}}</span>
                </div>
                <p class="text-xs text-slate-400 text-center line-clamp-2 h-8">{{app.info}}</p>
                <div class="mt-4 w-full bg-slate-50 text-indigo-600 text-center py-2.5 rounded-2xl font-bold group-hover:bg-indigo-600 group-hover:text-white transition">View Details</div>
            </div>
        </a>
        {% endfor %}
    </div>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block content %}{% endblock %}', content), apps=apps, ads=ads, q=query, is_admin_route=False)

@app.route('/app/<id>')
def details(id):
    app_data = apps_col.find_one({"_id": ObjectId(id)})
    if not app_data: return redirect('/')
    
    content = """
    <div class="max-w-4xl mx-auto">
        <div class="bg-white rounded-[3rem] shadow-sm border p-8 md:p-12">
            <div class="flex flex-col md:flex-row gap-8 items-center md:items-start text-center md:text-left">
                <img src="{{app.logo}}" class="w-48 h-48 rounded-[3rem] shadow-2xl">
                <div class="flex-1">
                    <h1 class="text-4xl font-black text-slate-800 mb-2">{{app.name}}</h1>
                    <div class="flex flex-wrap gap-3 mb-6 justify-center md:justify-start">
                        <span class="bg-indigo-600 text-white px-4 py-1 rounded-full font-bold text-sm">{{app.category}}</span>
                        <span class="bg-slate-100 text-slate-600 px-4 py-1 rounded-full font-bold text-sm">Version: {{app.version}}</span>
                        <span class="bg-slate-100 text-slate-600 px-4 py-1 rounded-full font-bold text-sm">Released: {{app.release_date}}</span>
                    </div>
                    <p class="text-slate-500 leading-relaxed text-lg mb-8">{{app.info}}</p>
                    <a href="/get/{{app._id}}" class="inline-flex items-center gap-3 bg-indigo-600 text-white px-10 py-5 rounded-[2rem] font-black text-xl hover:bg-indigo-700 hover:scale-105 transition transform shadow-2xl shadow-indigo-200">
                        <i class="fas fa-download"></i> DOWNLOAD NOW
                    </a>
                </div>
            </div>
        </div>
    </div>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block content %}{% endblock %}', content), app=app_data, is_admin_route=False)

@app.route('/get/<id>')
def download_logic(id):
    app_data = apps_col.find_one({"_id": ObjectId(id)})
    if not app_data: return redirect('/')
    
    short_cfg = settings_col.find_one({"type": "shortener"})
    target = app_data['download_link']
    
    if short_cfg and short_cfg.get('url') and short_cfg.get('api'):
        try:
            api_url = f"https://{short_cfg['url']}/api?api={short_cfg['api']}&url={target}"
            res = requests.get(api_url, timeout=10).json()
            short_url = res.get('shortenedUrl') or res.get('shortedUrl')
            if short_url: return redirect(short_url)
        except: pass
    return redirect(target)

# --- ADMIN ROUTES ---

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('logged_in'): return redirect('/login')
    
    stats = {
        "apps": apps_col.count_documents({}),
        "ads": ads_col.count_documents({}),
        "users": users_col.count_documents({})
    }
    
    content = """
    <h1 class="text-3xl font-black mb-8">Dashboard Overview</h1>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
        <div class="bg-white p-8 rounded-[2rem] shadow-sm border border-slate-100">
            <div class="w-12 h-12 bg-indigo-100 text-indigo-600 rounded-2xl flex items-center justify-center mb-4 text-xl">
                <i class="fas fa-mobile-alt"></i>
            </div>
            <div class="text-4xl font-black text-slate-800">{{ stats.apps }}</div>
            <div class="text-slate-400 font-bold uppercase text-xs tracking-wider">Total Applications</div>
        </div>
        <div class="bg-white p-8 rounded-[2rem] shadow-sm border border-slate-100">
            <div class="w-12 h-12 bg-emerald-100 text-emerald-600 rounded-2xl flex items-center justify-center mb-4 text-xl">
                <i class="fas fa-ad"></i>
            </div>
            <div class="text-4xl font-black text-slate-800">{{ stats.ads }}</div>
            <div class="text-slate-400 font-bold uppercase text-xs tracking-wider">Active Ad Units</div>
        </div>
        <div class="bg-white p-8 rounded-[2rem] shadow-sm border border-slate-100">
            <div class="w-12 h-12 bg-orange-100 text-orange-600 rounded-2xl flex items-center justify-center mb-4 text-xl">
                <i class="fas fa-link"></i>
            </div>
            <div class="text-4xl font-black text-slate-800">Shortener</div>
            <div class="text-slate-400 font-bold uppercase text-xs tracking-wider">API Integration</div>
        </div>
    </div>

    <div class="bg-indigo-900 rounded-[2rem] p-10 text-white flex items-center justify-between">
        <div>
            <h2 class="text-3xl font-black mb-2">Welcome Back, Admin!</h2>
            <p class="text-indigo-300">You can manage all your content from the sidebar menu.</p>
        </div>
        <img src="https://cdn-icons-png.flaticon.com/512/2021/2021646.png" class="h-32 hidden md:block">
    </div>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block admin_content %}{% endblock %}', content), stats=stats, is_admin_route=True, active_page='dashboard')

@app.route('/admin/apps', methods=['GET', 'POST'])
def admin_apps():
    if not session.get('logged_in'): return redirect('/login')
    
    if request.method == 'POST':
        apps_col.insert_one({
            "name": request.form.get('name'), "logo": request.form.get('logo'),
            "category": request.form.get('category'), "release_date": request.form.get('release_date'),
            "version": request.form.get('version'), "info": request.form.get('info'),
            "download_link": request.form.get('download_link'), "at": datetime.now()
        })
        flash("Application published successfully!")
        return redirect('/admin/apps')
    
    q = request.args.get('q', '')
    if q:
        apps = list(apps_col.find({"name": {"$regex": q, "$options": "i"}}).sort('_id', -1))
    else:
        apps = list(apps_col.find().sort('_id', -1))
        
    content = """
    <div class="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 mb-8">
        <h1 class="text-3xl font-black">Manage Applications</h1>
        <form class="bg-white rounded-full px-4 py-2 border flex items-center w-full lg:w-72">
            <input type="text" name="q" placeholder="Search apps..." class="bg-transparent outline-none text-sm flex-1" value="{{q}}">
            <button type="submit"><i class="fas fa-search text-indigo-600"></i></button>
        </form>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <!-- Add Form -->
        <div class="bg-white p-8 rounded-[2rem] shadow-sm border border-slate-100">
            <h2 class="text-xl font-bold mb-6 text-indigo-600 italic underline">Upload New App</h2>
            <form method="POST" class="space-y-4">
                <input type="text" name="name" placeholder="App Name" class="w-full bg-slate-50 border-none p-4 rounded-2xl outline-none focus:ring-2 ring-indigo-500" required>
                <input type="text" name="logo" placeholder="Logo Link (URL)" class="w-full bg-slate-50 border-none p-4 rounded-2xl outline-none focus:ring-2 ring-indigo-500" required>
                <select name="category" class="w-full bg-slate-50 border-none p-4 rounded-2xl outline-none">
                    <option>Mobile</option><option>PC / Desktop</option><option>iOS</option>
                </select>
                <div class="flex gap-2">
                    <input type="date" name="release_date" class="w-1/2 bg-slate-50 border-none p-4 rounded-2xl outline-none" required>
                    <input type="text" name="version" placeholder="Version" class="w-1/2 bg-slate-50 border-none p-4 rounded-2xl outline-none" required>
                </div>
                <textarea name="info" placeholder="Info..." class="w-full bg-slate-50 border-none p-4 rounded-2xl outline-none h-24" required></textarea>
                <input type="text" name="download_link" placeholder="Main Link" class="w-full bg-slate-50 border-none p-4 rounded-2xl outline-none" required>
                <button class="w-full bg-indigo-600 text-white py-4 rounded-2xl font-black shadow-lg shadow-indigo-100 hover:bg-indigo-700">PUBLISH APP</button>
            </form>
        </div>
        <!-- Table -->
        <div class="lg:col-span-2 bg-white rounded-[2rem] shadow-sm border border-slate-100 overflow-hidden">
            <table class="w-full text-left">
                <thead class="bg-slate-50 border-b">
                    <tr><th class="p-5 font-bold text-slate-500">App Name</th><th class="p-5 font-bold text-slate-500">Action</th></tr>
                </thead>
                <tbody>
                    {% for item in apps %}
                    <tr class="border-b last:border-0 hover:bg-slate-50">
                        <td class="p-5 flex items-center gap-4">
                            <img src="{{item.logo}}" class="w-10 h-10 rounded-xl shadow">
                            <div>
                                <p class="font-bold text-slate-800">{{item.name}}</p>
                                <span class="text-[10px] bg-indigo-50 text-indigo-600 px-2 py-0.5 rounded font-black">{{item.category}}</span>
                            </div>
                        </td>
                        <td class="p-5">
                            <a href="/del/app/{{item._id}}" class="text-red-500 font-black hover:bg-red-50 px-4 py-2 rounded-xl transition" onclick="return confirm('Delete permanently?')">DELETE</a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block admin_content %}{% endblock %}', content), apps=apps, q=q, is_admin_route=True, active_page='apps')

@app.route('/admin/ads', methods=['GET', 'POST'])
def admin_ads():
    if not session.get('logged_in'): return redirect('/login')
    if request.method == 'POST':
        ads_col.insert_one({"name": request.form.get('name'), "code": request.form.get('code')})
        flash("New Ad Unit Added!")
    all_ads = list(ads_col.find())
    content = """
    <h1 class="text-3xl font-black mb-8">Manage Advertisements</h1>
    <div class="max-w-4xl bg-white p-10 rounded-[3rem] shadow-sm border border-slate-100">
        <form method="POST" class="space-y-6 mb-12">
            <input type="text" name="name" placeholder="Ad Spot Label (e.g. Header Ads)" class="w-full bg-slate-50 p-4 rounded-2xl outline-none" required>
            <textarea name="code" placeholder="Paste Ad HTML/JS code here..." class="w-full bg-slate-50 p-4 rounded-2xl h-44 font-mono text-sm" required></textarea>
            <button class="bg-emerald-600 text-white px-10 py-4 rounded-2xl font-black shadow-lg">SAVE AD UNIT</button>
        </form>
        <div class="space-y-4">
            <h2 class="text-xl font-bold mb-4">Active Units</h2>
            {% for ad in ads %}
            <div class="flex justify-between items-center p-6 bg-slate-50 rounded-2xl">
                <div><span class="font-bold text-slate-800">{{ad.name}}</span> <br> <small class="text-emerald-500 font-bold">STATUS: LIVE</small></div>
                <a href="/del/ad/{{ad._id}}" class="text-red-500 font-black">REMOVE</a>
            </div>
            {% endfor %}
        </div>
    </div>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block admin_content %}{% endblock %}', content), ads=all_ads, is_admin_route=True, active_page='ads')

@app.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    if not session.get('logged_in'): return redirect('/login')
    if request.method == 'POST':
        settings_col.update_one({"type": "shortener"}, {"$set": {"url": request.form.get('url'), "api": request.form.get('api')}}, upsert=True)
        flash("Shortener configuration updated!")
    curr = settings_col.find_one({"type": "shortener"}) or {}
    content = """
    <h1 class="text-3xl font-black mb-8">System Settings</h1>
    <div class="max-w-md bg-white p-10 rounded-[3rem] shadow-sm border border-slate-100">
        <h2 class="text-xl font-bold mb-6 text-orange-600"><i class="fas fa-link mr-2"></i>URL Shortener API</h2>
        <form method="POST" class="space-y-4">
            <input type="text" name="url" value="{{cfg.url}}" placeholder="Domain (e.g. site.xyz)" class="w-full bg-slate-50 p-4 rounded-2xl outline-none" required>
            <input type="password" name="api" value="{{cfg.api}}" placeholder="Personal API Key" class="w-full bg-slate-50 p-4 rounded-2xl outline-none" required>
            <button class="w-full bg-orange-600 text-white py-4 rounded-2xl font-black shadow-lg">UPDATE API</button>
        </form>
        <p class="mt-4 text-[10px] text-slate-400">All download links will be automatically shortened using this API.</p>
    </div>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block admin_content %}{% endblock %}', content), cfg=curr, is_admin_route=True, active_page='settings')

# --- AUTH ---

@app.route('/login', methods=['GET', 'POST'])
def login():
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
        flash("Incorrect admin password!")
    content = """
    <div class="max-w-sm mx-auto mt-20 bg-white p-12 rounded-[3rem] shadow-2xl border text-center">
        <h2 class="text-3xl font-black mb-10 text-indigo-700">ADMIN LOGIN</h2>
        <form method="POST" class="space-y-6">
            <input type="password" name="password" placeholder="Passcode" class="w-full bg-slate-50 p-4 rounded-2xl text-center outline-none focus:ring-2 ring-indigo-500" required>
            <button class="w-full bg-indigo-600 text-white py-4 rounded-2xl font-black shadow-xl">LOG IN</button>
        </form>
        <a href="/forgot" class="text-xs text-slate-400 mt-8 block">Forgot password?</a>
    </div>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block content %}{% endblock %}', content), is_admin_route=False)

@app.route('/forgot', methods=['GET', 'POST'])
def forgot():
    if request.method == 'POST':
        if request.form.get('key') == RECOVERY_KEY:
            users_col.update_one({"username": "admin"}, {"$set": {"password": generate_password_hash(request.form.get('pw'))}}, upsert=True)
            flash("System override successful! Please login.")
            return redirect('/login')
        flash("Recovery key is incorrect!")
    content = """
    <div class="max-w-sm mx-auto mt-20 bg-white p-12 rounded-[3rem] shadow-2xl border text-center">
        <h2 class="text-2xl font-bold mb-8 text-red-600">RESET SYSTEM</h2>
        <form method="POST" class="space-y-4">
            <input type="text" name="key" placeholder="Secret Key" class="w-full bg-slate-50 p-4 rounded-2xl outline-none" required>
            <input type="password" name="pw" placeholder="New PW" class="w-full bg-slate-50 p-4 rounded-2xl outline-none" required>
            <button class="w-full bg-red-600 text-white py-4 rounded-2xl font-black shadow-lg">OVERRIDE</button>
        </form>
    </div>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block content %}{% endblock %}', content), is_admin_route=False)

@app.route('/del/<type>/<id>')
def delete(type, id):
    if not session.get('logged_in'): return redirect('/login')
    if type == 'app': apps_col.delete_one({"_id": ObjectId(id)})
    if type == 'ad': ads_col.delete_one({"_id": ObjectId(id)})
    flash("Entry removed successfully!")
    return redirect(request.referrer)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# Vercel Handler
handler = app

if __name__ == '__main__':
    app.run(debug=True)
