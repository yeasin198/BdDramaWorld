import os
import requests
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash

# ফ্লাস্ক অ্যাপ সেটআপ
app = Flask(__name__)

# --- সিকিউরিটি কনফিগারেশন ---
# ভেরিয়েবলগুলো না পেলে ডিফল্ট মান ব্যবহার হবে (Vercel-এ পরে চেঞ্জ করা যাবে)
app.secret_key = os.environ.get("SESSION_SECRET", "super_secret_key_998877")
RECOVERY_KEY = os.environ.get("RECOVERY_KEY", "admin@123")

# --- MongoDB কানেকশন ---
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster"
client = MongoClient(MONGO_URI)
db = client['app_hub_final_db']
apps_col = db['apps']
users_col = db['users']
ads_col = db['ads']
settings_col = db['settings']

# --- এইচটিএমএল ডিজাইন (Tailwind CSS) ---
LAYOUT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>App Hub Pro</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>.line-clamp-2{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;}</style>
</head>
<body class="bg-gray-100 font-sans">
    <nav class="bg-indigo-700 p-4 text-white shadow-lg sticky top-0 z-50">
        <div class="container mx-auto flex justify-between items-center">
            <a href="/" class="text-2xl font-black italic">APP<span class="text-indigo-300">HUB</span></a>
            <div class="space-x-4 flex items-center text-xs font-bold uppercase">
                <a href="/" class="hover:text-indigo-200">Home</a>
                {% if session.get('logged_in') %}
                    <a href="/admin" class="hover:text-indigo-200">Apps</a>
                    <a href="/admin/ads" class="hover:text-indigo-200">Ads</a>
                    <a href="/admin/settings" class="hover:text-indigo-200">Settings</a>
                    <a href="/logout" class="bg-red-500 px-3 py-1 rounded">Logout</a>
                {% else %}
                    <a href="/login" class="bg-white text-indigo-700 px-4 py-1 rounded">Login</a>
                {% endif %}
            </div>
        </div>
    </nav>
    <div class="container mx-auto p-4 md:p-8">
        {% with messages = get_flashed_messages() %}{% if messages %}
            {% for msg in messages %}<div class="bg-blue-100 border-l-4 border-blue-500 text-blue-700 p-4 mb-6 shadow-sm">{{ msg }}</div>{% endfor %}
        {% endif %}{% endwith %}
        {% block content %}{% endblock %}
    </div>
</body>
</html>
"""

# --- রুটস এবং লজিক (Routes) ---

@app.route('/')
def home():
    apps = list(apps_col.find().sort('_id', -1))
    ads = list(ads_col.find())
    content = """
    <!-- Ads Display -->
    <div class="max-w-4xl mx-auto mb-10 space-y-4">
        {% for ad in ads %}
            <div class="flex justify-center bg-white p-2 rounded-xl shadow-sm border overflow-hidden">{{ ad.code | safe }}</div>
        {% endfor %}
    </div>

    <h2 class="text-2xl font-bold mb-8 text-gray-800 border-b-2 border-indigo-600 inline-block pb-1">Available Apps</h2>
    
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
        {% for app in apps %}
        <div class="bg-white rounded-3xl p-6 shadow-sm border border-gray-100 hover:shadow-2xl transition duration-300">
            <div class="flex flex-col items-center">
                <img src="{{app.logo}}" class="w-20 h-20 rounded-2xl mb-4 shadow-md object-cover">
                <h3 class="text-lg font-bold text-gray-800 text-center">{{app.name}}</h3>
                <div class="flex gap-2 my-2">
                    <span class="text-[10px] bg-indigo-50 text-indigo-600 px-2 py-0.5 rounded font-bold uppercase">{{app.category}}</span>
                    <span class="text-[10px] bg-gray-100 text-gray-500 px-2 py-0.5 rounded font-bold uppercase">v{{app.version}}</span>
                </div>
                <p class="text-xs text-gray-400 text-center mb-6 line-clamp-2 h-8">{{app.info}}</p>
                <a href="/get/{{app._id}}" class="w-full bg-indigo-600 text-white text-center py-3 rounded-2xl font-bold hover:bg-indigo-700 transition shadow-lg">Download</a>
            </div>
        </div>
        {% endfor %}
    </div>
    """
    return render_template_string(LAYOUT.replace('{% block content %}{% endblock %}', content), apps=apps, ads=ads)

@app.route('/get/<id>')
def download_process(id):
    app_data = apps_col.find_one({"_id": ObjectId(id)})
    if not app_data: return "Error: App Not Found", 404
    
    original_link = app_data['download_link']
    short_cfg = settings_col.find_one({"type": "shortener"})
    
    if short_cfg and short_cfg.get('url') and short_cfg.get('api'):
        try:
            api_url = f"https://{short_cfg['url']}/api?api={short_cfg['api']}&url={original_link}"
            res = requests.get(api_url, timeout=10).json()
            short_url = res.get('shortenedUrl') or res.get('shortedUrl')
            if short_url: return redirect(short_url)
        except: pass
    return redirect(original_link)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('logged_in'): return redirect(url_for('login'))
    if request.method == 'POST':
        apps_col.insert_one({
            "name": request.form.get('name'), "logo": request.form.get('logo'),
            "category": request.form.get('category'), "release_date": request.form.get('release_date'),
            "version": request.form.get('version'), "info": request.form.get('info'),
            "download_link": request.form.get('download_link'), "at": datetime.now()
        })
        flash("App added successfully!")
        return redirect(url_for('admin'))
    
    all_apps = list(apps_col.find().sort('_id', -1))
    content = """
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div class="bg-white p-6 rounded-2xl shadow border">
            <h2 class="text-xl font-bold mb-6 text-indigo-700 border-b pb-2">New Upload</h2>
            <form method="POST" class="space-y-4">
                <input type="text" name="name" placeholder="App Name" class="w-full border p-3 rounded-xl focus:ring-1 ring-indigo-500 outline-none" required>
                <input type="text" name="logo" placeholder="Logo Link (URL)" class="w-full border p-3 rounded-xl outline-none" required>
                <select name="category" class="w-full border p-3 rounded-xl"><option>Mobile</option><option>Desktop</option><option>iOS</option></select>
                <div class="flex gap-2">
                    <input type="date" name="release_date" class="w-1/2 border p-3 rounded-xl text-sm" required>
                    <input type="text" name="version" placeholder="Version" class="w-1/2 border p-3 rounded-xl" required>
                </div>
                <textarea name="info" placeholder="Info..." class="w-full border p-3 rounded-xl h-24" required></textarea>
                <input type="text" name="download_link" placeholder="Main Download Link" class="w-full border p-3 rounded-xl outline-none" required>
                <button class="w-full bg-indigo-600 text-white py-3 rounded-xl font-bold hover:bg-indigo-700">Publish Now</button>
            </form>
        </div>
        <div class="lg:col-span-2 bg-white rounded-2xl shadow border overflow-hidden">
            <table class="w-full text-left text-sm">
                <thead class="bg-gray-50 border-b"><tr><th class="p-4 font-bold">App Name</th><th class="p-4 font-bold text-right">Action</th></tr></thead>
                <tbody>{% for app in apps %}<tr class="border-b">
                    <td class="p-4 flex items-center gap-3"><img src="{{app.logo}}" class="w-8 h-8 rounded">{{app.name}} <small class="text-gray-400">(v{{app.version}})</small></td>
                    <td class="p-4 text-right"><a href="/del/app/{{app._id}}" class="text-red-500 font-bold bg-red-50 px-3 py-1 rounded" onclick="return confirm('Delete?')">Delete</a></td>
                </tr>{% endfor %}</tbody>
            </table>
        </div>
    </div>
    """
    return render_template_string(LAYOUT.replace('{% block content %}{% endblock %}', content), apps=all_apps)

@app.route('/admin/ads', methods=['GET', 'POST'])
def ads_manager():
    if not session.get('logged_in'): return redirect(url_for('login'))
    if request.method == 'POST':
        ads_col.insert_one({"name": request.form.get('name'), "code": request.form.get('code')})
        flash("Ad Code Saved!")
    all_ads = list(ads_col.find())
    content = """
    <div class="max-w-3xl mx-auto bg-white p-8 rounded-2xl shadow border">
        <h2 class="text-xl font-bold mb-6 text-indigo-700">Manage Unlimited Ads</h2>
        <form method="POST" class="space-y-4 mb-10">
            <input type="text" name="name" placeholder="Ad Label (e.g. Header Ads)" class="w-full border p-3 rounded-xl" required>
            <textarea name="code" placeholder="Paste Ad HTML/JS Code here..." class="w-full border p-3 rounded-xl h-32 font-mono text-xs" required></textarea>
            <button class="bg-indigo-600 text-white px-8 py-3 rounded-xl font-bold">Add New Ad</button>
        </form>
        <div class="space-y-4">
            {% for ad in ads %}
            <div class="flex justify-between items-center p-3 border-b">
                <span>{{ad.name}}</span><a href="/del/ad/{{ad._id}}" class="text-red-500 font-bold">Delete</a>
            </div>
            {% endfor %}
        </div>
    </div>
    """
    return render_template_string(LAYOUT.replace('{% block content %}{% endblock %}', content), ads=all_ads)

@app.route('/admin/settings', methods=['GET', 'POST'])
def settings():
    if not session.get('logged_in'): return redirect(url_for('login'))
    if request.method == 'POST':
        settings_col.update_one({"type": "shortener"}, {"$set": {"url": request.form.get('url'), "api": request.form.get('api')}}, upsert=True)
        flash("API Settings Updated!")
    curr = settings_col.find_one({"type": "shortener"}) or {}
    content = """
    <div class="max-w-md mx-auto bg-white p-8 rounded-2xl shadow border">
        <h2 class="text-xl font-bold mb-6 italic">Shortener API</h2>
        <form method="POST" class="space-y-4">
            <input type="text" name="url" value="{{cfg.url}}" placeholder="Domain (e.g. site.xyz)" class="w-full border p-3 rounded-xl" required>
            <input type="password" name="api" value="{{cfg.api}}" placeholder="API Secret Key" class="w-full border p-3 rounded-xl" required>
            <button class="w-full bg-indigo-700 text-white py-3 rounded-xl font-bold">Update Settings</button>
        </form>
    </div>
    """
    return render_template_string(LAYOUT.replace('{% block content %}{% endblock %}', content), cfg=curr)

@app.route('/login', methods=['GET', 'POST'])
def login():
    admin = users_col.find_one({"username": "admin"})
    if request.method == 'POST':
        pw = request.form.get('password')
        if not admin:
            users_col.insert_one({"username": "admin", "password": generate_password_hash(pw)})
            session['logged_in'] = True
            return redirect(url_for('admin'))
        if check_password_hash(admin['password'], pw):
            session['logged_in'] = True
            return redirect(url_for('admin'))
        flash("Wrong Password!")
    content = """
    <div class="max-w-sm mx-auto mt-20 bg-white p-10 rounded-3xl shadow-2xl border text-center">
        <h2 class="text-2xl font-black mb-8 text-indigo-800">ADMIN ACCESS</h2>
        <form method="POST"><input type="password" name="password" placeholder="Passcode" class="w-full border p-4 rounded-2xl mb-4 text-center outline-none focus:ring-1 ring-indigo-500" required>
        <button class="w-full bg-indigo-600 text-white py-4 rounded-2xl font-bold shadow-lg">LOG IN</button></form>
        <a href="/forgot" class="text-xs text-gray-400 mt-6 block underline">Forgot Password?</a>
    </div>
    """
    return render_template_string(LAYOUT.replace('{% block content %}{% endblock %}', content))

@app.route('/forgot', methods=['GET', 'POST'])
def forgot():
    if request.method == 'POST':
        if request.form.get('key') == RECOVERY_KEY:
            users_col.update_one({"username": "admin"}, {"$set": {"password": generate_password_hash(request.form.get('pw'))}}, upsert=True)
            flash("Override Success! Please login.")
            return redirect(url_for('login'))
        flash("Invalid Recovery Key!")
    content = """
    <div class="max-w-sm mx-auto mt-20 bg-white p-8 rounded-2xl shadow border">
        <h2 class="font-bold text-red-600 mb-6">Reset System</h2>
        <form method="POST" class="space-y-4">
            <input type="text" name="key" placeholder="System Recovery Key" class="w-full border p-3 rounded-xl" required>
            <input type="password" name="pw" placeholder="New Admin PW" class="w-full border p-3 rounded-xl" required>
            <button class="w-full bg-red-600 text-white py-3 rounded-xl font-bold">RESET NOW</button>
        </form>
    </div>
    """
    return render_template_string(LAYOUT.replace('{% block content %}{% endblock %}', content))

@app.route('/del/<type>/<id>')
def delete(type, id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    if type == 'app': apps_col.delete_one({"_id": ObjectId(id)})
    if type == 'ad': ads_col.delete_one({"_id": ObjectId(id)})
    flash("Successfully Deleted!")
    return redirect(request.referrer)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
