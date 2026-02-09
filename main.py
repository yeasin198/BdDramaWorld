import os
import requests
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash

# ফ্লাস্ক অ্যাপ ইনিশিয়ালাইজেশন
app = Flask(__name__)

# --- সিকিউরিটি কনফিগারেশন ---
# ভার্সেল ড্যাশবোর্ড থেকে এই মানগুলো পরিবর্তন করা যাবে (Environment Variables)
app.secret_key = os.environ.get("SESSION_SECRET", "super_secret_123456789")
RECOVERY_KEY = os.environ.get("RECOVERY_KEY", "admin@reset") # পাসওয়ার্ড রিসেট করার জন্য সিক্রেট কী

# --- MongoDB কানেকশন (আপনার দেওয়া লিঙ্ক) ---
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster"
client = MongoClient(MONGO_URI)
db = client['app_hub_pro_database']
apps_col = db['apps']
users_col = db['users']
ads_col = db['ads']
settings_col = db['settings']

# --- সম্পূর্ণ ডিজাইন (এক ফাইলে রাখার জন্য CSS ও HTML এখানে দেওয়া হয়েছে) ---
BASE_LAYOUT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>App Hub - Ultimate Store</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style> .line-clamp-2 { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; } </style>
</head>
<body class="bg-slate-50 font-sans">
    <nav class="bg-indigo-700 p-4 text-white shadow-xl sticky top-0 z-50">
        <div class="container mx-auto flex justify-between items-center">
            <a href="/" class="text-2xl font-black tracking-tighter italic">APP<span class="text-indigo-300">HUB</span></a>
            <div class="space-x-4 flex items-center text-xs font-bold">
                <a href="/" class="hover:text-indigo-200">HOME</a>
                {% if session.get('logged_in') %}
                    <a href="/admin" class="bg-indigo-800 px-3 py-1.5 rounded-lg">ADMIN</a>
                    <a href="/admin/ads" class="bg-indigo-800 px-3 py-1.5 rounded-lg">ADS</a>
                    <a href="/admin/settings" class="bg-indigo-800 px-3 py-1.5 rounded-lg">SHORTENER</a>
                    <a href="/logout" class="text-red-300">LOGOUT</a>
                {% else %}
                    <a href="/login" class="bg-white text-indigo-700 px-4 py-1.5 rounded-lg shadow-md">LOGIN</a>
                {% endif %}
            </div>
        </div>
    </nav>
    <div class="container mx-auto p-4 md:p-8">
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for msg in messages %}
                    <div class="bg-indigo-100 border-l-4 border-indigo-500 text-indigo-700 p-4 mb-6 shadow-sm rounded-r-lg">{{ msg }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        {% block content %}{% endblock %}
    </div>
    <footer class="text-center py-10 text-slate-400 text-xs">
        &copy; 2024 App Hub Pro - All Rights Reserved.
    </footer>
</body>
</html>
"""

# --- পেজ কন্ট্রোলার (Routes) ---

@app.route('/')
def home():
    apps = list(apps_col.find().sort('_id', -1))
    ads = list(ads_col.find())
    
    content = """
    <!-- Ads Display Section -->
    <div class="max-w-4xl mx-auto mb-10 space-y-6">
        {% for ad in ads %}
            <div class="flex justify-center bg-white p-2 rounded-xl shadow-sm border overflow-hidden">
                {{ ad.code | safe }}
            </div>
        {% endfor %}
    </div>

    <h2 class="text-2xl font-bold mb-8 text-slate-800 flex items-center gap-2">
        <i class="fas fa-layer-group text-indigo-600"></i> Applications Store
    </h2>
    
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
        {% for app in apps %}
        <div class="bg-white rounded-3xl p-6 shadow-sm border border-slate-100 hover:shadow-2xl transition duration-300 group">
            <div class="flex flex-col items-center">
                <img src="{{app.logo}}" class="w-20 h-20 rounded-2xl mb-4 shadow-md object-cover group-hover:scale-105 transition">
                <h3 class="text-lg font-bold text-slate-800 text-center mb-1">{{app.name}}</h3>
                <div class="flex gap-2 mb-3">
                    <span class="text-[10px] bg-indigo-50 text-indigo-600 px-2 py-0.5 rounded-full font-bold uppercase">{{app.category}}</span>
                    <span class="text-[10px] bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full font-bold">V {{app.version}}</span>
                </div>
                <p class="text-xs text-slate-400 text-center mb-6 line-clamp-2 h-8">{{app.info}}</p>
                <a href="/get/{{app._id}}" class="w-full bg-indigo-600 text-white text-center py-3 rounded-2xl font-bold hover:bg-indigo-800 transition shadow-lg shadow-indigo-100">
                    <i class="fas fa-download mr-1"></i> Download
                </a>
            </div>
        </div>
        {% endfor %}
    </div>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block content %}{% endblock %}', content), apps=apps, ads=ads)

@app.route('/get/<id>')
def download_process(id):
    app_data = apps_col.find_one({"_id": ObjectId(id)})
    if not app_data: return "Application not found!", 404
    
    original_link = app_data['download_link']
    short_cfg = settings_col.find_one({"type": "shortener"})
    
    # URL Shortener API integration
    if short_cfg and short_cfg.get('url') and short_cfg.get('api'):
        try:
            api_endpoint = f"https://{short_cfg['url']}/api?api={short_cfg['api']}&url={original_link}"
            res = requests.get(api_endpoint, timeout=10).json()
            short_url = res.get('shortenedUrl') or res.get('shortedUrl')
            if short_url: return redirect(short_url)
        except Exception:
            pass # সমস্যা হলে অরিজিনাল লিঙ্কে পাঠাবে
            
    return redirect(original_link)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    if request.method == 'POST':
        apps_col.insert_one({
            "name": request.form.get('name'),
            "logo": request.form.get('logo'),
            "category": request.form.get('category'),
            "release_date": request.form.get('release_date'),
            "version": request.form.get('version'),
            "info": request.form.get('info'),
            "download_link": request.form.get('download_link'),
            "timestamp": datetime.now()
        })
        flash("App added to database!")
        return redirect(url_for('admin'))
    
    all_apps = list(apps_col.find().sort('_id', -1))
    content = """
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-10">
        <!-- Add App Form -->
        <div class="bg-white p-8 rounded-3xl shadow-sm border">
            <h2 class="text-xl font-bold mb-6 text-indigo-700 flex items-center gap-2 underline decoration-indigo-100"><i class="fas fa-plus-circle"></i> New Upload</h2>
            <form method="POST" class="space-y-4">
                <input type="text" name="name" placeholder="App Name" class="w-full border p-3 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none" required>
                <input type="text" name="logo" placeholder="Logo Link (URL)" class="w-full border p-3 rounded-xl outline-none" required>
                <select name="category" class="w-full border p-3 rounded-xl">
                    <option value="Mobile">Mobile (Android)</option>
                    <option value="Desktop">Desktop (PC)</option>
                    <option value="iOS">iOS (Apple)</option>
                </select>
                <div class="flex gap-2">
                    <input type="date" name="release_date" class="w-1/2 border p-3 rounded-xl text-sm" required>
                    <input type="text" name="version" placeholder="Version" class="w-1/2 border p-3 rounded-xl" required>
                </div>
                <textarea name="info" placeholder="About App..." class="w-full border p-3 rounded-xl h-24 outline-none" required></textarea>
                <input type="text" name="download_link" placeholder="Download Link" class="w-full border p-3 rounded-xl outline-none" required>
                <button class="w-full bg-indigo-600 text-white py-4 rounded-2xl font-bold hover:bg-indigo-700 shadow-lg">Publish Now</button>
            </form>
        </div>
        <!-- Manage Table -->
        <div class="lg:col-span-2">
            <div class="bg-white rounded-3xl shadow-sm border overflow-hidden">
                <table class="w-full text-left">
                    <thead class="bg-slate-50 border-b">
                        <tr><th class="p-4 font-bold text-slate-600">App Details</th><th class="p-4 font-bold text-slate-600">Action</th></tr>
                    </thead>
                    <tbody>
                        {% for item in apps %}
                        <tr class="border-b hover:bg-slate-50">
                            <td class="p-4 flex items-center gap-3">
                                <img src="{{item.logo}}" class="w-10 h-10 rounded-lg shadow-sm">
                                <div><p class="font-bold text-slate-800 leading-none">{{item.name}}</p><small class="text-indigo-500 font-bold">v{{item.version}}</small></div>
                            </td>
                            <td class="p-4"><a href="/del/app/{{item._id}}" class="text-red-500 bg-red-50 px-4 py-2 rounded-xl hover:bg-red-500 hover:text-white transition font-bold" onclick="return confirm('Delete permanently?')">Delete</a></td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block content %}{% endblock %}', content), apps=all_apps)

@app.route('/admin/ads', methods=['GET', 'POST'])
def ads_manager():
    if not session.get('logged_in'): return redirect(url_for('login'))
    if request.method == 'POST':
        ads_col.insert_one({"name": request.form.get('name'), "code": request.form.get('code')})
        flash("Ad script saved!")
        return redirect(url_for('ads_manager'))
    
    all_ads = list(ads_col.find().sort('_id', -1))
    content = """
    <div class="max-w-4xl mx-auto">
        <div class="bg-white p-8 rounded-3xl shadow-sm border mb-10">
            <h2 class="text-xl font-bold mb-6 text-indigo-700"><i class="fas fa-ad mr-2"></i>Manage Ad Scripts</h2>
            <form method="POST" class="space-y-4">
                <input type="text" name="name" placeholder="Ad Spot Label (e.g. Top Banner)" class="w-full border p-3 rounded-xl outline-none" required>
                <textarea name="code" placeholder="Paste Ad HTML/JS code here..." class="w-full border p-3 rounded-xl h-44 font-mono text-xs focus:ring-2 focus:ring-indigo-500" required></textarea>
                <button class="bg-indigo-600 text-white px-8 py-3 rounded-2xl font-bold hover:bg-indigo-700 shadow-lg">Save Code</button>
            </form>
        </div>
        <div class="bg-white rounded-3xl shadow-sm border overflow-hidden">
            {% for ad in ads %}
            <div class="flex justify-between items-center p-6 border-b last:border-0 hover:bg-slate-50">
                <div><p class="font-bold text-slate-800">{{ad.name}}</p><small class="text-green-500 font-bold">STATUS: ACTIVE</small></div>
                <a href="/del/ad/{{ad._id}}" class="text-red-600 font-bold bg-red-50 px-5 py-2 rounded-2xl hover:bg-red-600 hover:text-white transition">Remove</a>
            </div>
            {% endfor %}
        </div>
    </div>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block content %}{% endblock %}', content), ads=all_ads)

@app.route('/admin/settings', methods=['GET', 'POST'])
def settings():
    if not session.get('logged_in'): return redirect(url_for('login'))
    if request.method == 'POST':
        settings_col.update_one({"type": "shortener"}, {"$set": {"url": request.form.get('url'), "api": request.form.get('api')}}, upsert=True)
        flash("Shortener API updated!")
    
    curr = settings_col.find_one({"type": "shortener"}) or {}
    content = """
    <div class="max-w-md mx-auto bg-white p-8 rounded-3xl shadow-sm border">
        <h2 class="text-xl font-bold mb-6 text-indigo-700"><i class="fas fa-link mr-2"></i>Shortener Settings</h2>
        <form method="POST" class="space-y-4">
            <div><label class="text-xs font-bold text-slate-400 ml-1">DOMAIN (e.g. sjjdjdjdjdj.xyz)</label>
            <input type="text" name="url" value="{{cfg.url}}" placeholder="site.xyz" class="w-full border p-3 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none" required></div>
            <div><label class="text-xs font-bold text-slate-400 ml-1">API TOKEN</label>
            <input type="password" name="api" value="{{cfg.api}}" placeholder="your_secret_api_key" class="w-full border p-3 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none" required></div>
            <button class="w-full bg-indigo-700 text-white py-4 rounded-2xl font-bold shadow-lg">Update API</button>
        </form>
    </div>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block content %}{% endblock %}', content), cfg=curr)

# --- অথেন্টিকেশন ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    admin_user = users_col.find_one({"username": "admin"})
    if request.method == 'POST':
        pw = request.form.get('password')
        if not admin_user:
            users_col.insert_one({"username": "admin", "password": generate_password_hash(pw)})
            session['logged_in'] = True
            flash("Admin password set! Welcome.")
            return redirect(url_for('admin'))
        if check_password_hash(admin_user['password'], pw):
            session['logged_in'] = True
            return redirect(url_for('admin'))
        flash("Incorrect admin password!")
    
    content = """
    <div class="max-w-sm mx-auto mt-20 bg-white p-10 rounded-3xl shadow-2xl border border-indigo-50">
        <h2 class="text-3xl font-black text-center mb-10 text-indigo-700">ADMIN</h2>
        <form method="POST" class="space-y-6">
            <input type="password" name="password" placeholder="Password" class="w-full border-2 border-slate-100 p-4 rounded-2xl outline-none focus:border-indigo-500 text-center" required>
            <button class="w-full bg-indigo-600 text-white py-4 rounded-2xl font-black tracking-widest shadow-xl">LOG IN</button>
        </form>
        <div class="text-center mt-6"><a href="/forgot" class="text-xs text-slate-400 hover:text-indigo-500">Forgot?</a></div>
    </div>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block content %}{% endblock %}', content))

@app.route('/forgot', methods=['GET', 'POST'])
def forgot():
    if request.method == 'POST':
        if request.form.get('key') == RECOVERY_KEY:
            users_col.update_one({"username": "admin"}, {"$set": {"password": generate_password_hash(request.form.get('pw'))}}, upsert=True)
            flash("Password reset! Please log in.")
            return redirect(url_for('login'))
        flash("Invalid Secret Recovery Key!")
        
    content = """
    <div class="max-w-sm mx-auto mt-20 bg-white p-10 rounded-3xl shadow-2xl border border-red-50 text-center">
        <h2 class="text-2xl font-bold mb-8 text-red-600">RESET SYSTEM</h2>
        <form method="POST" class="space-y-4">
            <input type="text" name="key" placeholder="Recovery Key" class="w-full border p-4 rounded-2xl outline-none focus:border-red-500" required>
            <input type="password" name="pw" placeholder="New Password" class="w-full border p-4 rounded-2xl outline-none focus:border-red-500" required>
            <button class="w-full bg-red-600 text-white py-4 rounded-2xl font-bold shadow-lg">OVERRIDE</button>
        </form>
    </div>
    """
    return render_template_string(BASE_LAYOUT.replace('{% block content %}{% endblock %}', content))

@app.route('/del/<type>/<id>')
def delete_item(type, id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    if type == 'app': apps_col.delete_one({"_id": ObjectId(id)})
    if type == 'ad': ads_col.delete_one({"_id": ObjectId(id)})
    flash("Deleted successfully!")
    return redirect(request.referrer)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# Vercel-এর জন্য এক্সপোর্ট
def handler(request):
    return app(request)

if __name__ == '__main__':
    app.run(debug=True)
