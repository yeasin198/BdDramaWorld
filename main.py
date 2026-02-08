import os
from flask import Flask, render_template_string, request, redirect, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = "final_movie_system_ultra_key"

# --- MongoDB কানেকশন ---
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
client = MongoClient(MONGO_URI)
db = client['webseries_db']
series_collection = db['series']
settings_collection = db['settings']

# --- ডিফল্ট সেটিংস (কালার রিসেট করার জন্য) ---
DEFAULT_CONFIG = {
    "site_name": "WebSeries BD",
    "primary_color": "#E50914",
    "bg_color": "#0b0b0b",
    "card_bg": "#1a1a1a",
    "text_color": "#ffffff",
    "badge_color": "#E50914",
    "lang_color": "#aaaaaa",
    "shortener_url": "",
    "shortener_api": "",
    "ads": []
}

def get_site_config():
    s = settings_collection.find_one({"type": "config"})
    if not s:
        settings_collection.insert_one({"type": "config", **DEFAULT_CONFIG})
        return DEFAULT_CONFIG
    return s

# --- ডাইনামিক এবং অটো রেসপন্সিভ CSS ---
def get_css(s):
    return f"""
<style>
    :root {{ 
        --primary: {s['primary_color']}; 
        --bg: {s['bg_color']}; 
        --card: {s['card_bg']}; 
        --text: {s['text_color']}; 
        --badge: {s['badge_color']};
        --lang: {s['lang_color']};
    }}
    body {{ background: var(--bg); color: var(--text); font-family: 'Segoe UI', sans-serif; margin: 0; padding: 0; overflow-x: hidden; }}
    
    /* Header (Mobile Responsive) */
    header {{ background: #000; padding: 15px 5%; display: flex; flex-direction: column; align-items: center; border-bottom: 2px solid var(--primary); position: sticky; top: 0; z-index: 1000; }}
    @media (min-width: 768px) {{ header {{ flex-direction: row; justify-content: space-between; }} }}
    .logo {{ color: var(--primary); font-size: 24px; font-weight: bold; text-decoration: none; text-transform: uppercase; }}
    
    .search-box {{ display: flex; background: #222; border-radius: 5px; overflow: hidden; margin: 10px 0; border: 1px solid #333; width: 100%; max-width: 450px; }}
    .search-box input {{ border: none; background: transparent; color: white; padding: 10px; width: 100%; outline: none; }}
    .search-box button {{ background: var(--primary); border: none; color: white; padding: 0 15px; cursor: pointer; }}

    .container {{ padding: 20px 5%; }}
    
    /* Grid (Auto Responsive) */
    .grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; }}
    @media (min-width: 768px) {{ .grid {{ grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 20px; }} }}

    /* Cards & 4 Corner Badge System */
    .card {{ background: var(--card); border-radius: 8px; overflow: hidden; position: relative; text-decoration: none; color: white; transition: 0.3s; border: 1px solid #333; display: block; }}
    .card:hover {{ transform: translateY(-5px); border-color: var(--primary); }}
    .card img {{ width: 100%; aspect-ratio: 2/3; object-fit: cover; }}
    
    .badge-tl, .badge-tr, .badge-bl, .badge-br {{ position: absolute; background: var(--badge); color: white; padding: 2px 6px; font-size: 10px; font-weight: bold; border-radius: 3px; }}
    .badge-tl {{ top: 5px; left: 5px; }}
    .badge-tr {{ top: 5px; right: 5px; background: #000000aa; }}
    .badge-bl {{ bottom: 40px; left: 5px; background: orange; }}
    .badge-br {{ bottom: 40px; right: 5px; background: #27ae60; }}

    .card-info {{ padding: 10px; text-align: center; font-size: 13px; font-weight: bold; }}

    /* Detail Page */
    .detail-flex {{ display: flex; flex-direction: column; gap: 20px; }}
    @media (min-width: 768px) {{ .detail-flex {{ flex-direction: row; }} }}
    .detail-img {{ width: 100%; max-width: 250px; border-radius: 10px; border: 1px solid #333; align-self: center; }}
    .story {{ background: #111; padding: 15px; border-radius: 8px; border-left: 4px solid var(--primary); margin: 15px 0; color: #ccc; line-height: 1.6; font-size: 14px; }}
    
    /* Episodes */
    .ep-box {{ background: #1a1a1a; padding: 15px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #333; }}
    .ep-meta {{ display: flex; justify-content: space-between; font-size: 12px; color: #aaa; margin-bottom: 8px; }}
    .btn-group {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 10px; }}
    .btn {{ padding: 8px; border-radius: 4px; text-decoration: none; color: white; font-size: 11px; font-weight: bold; text-align: center; flex: 1; min-width: 80px; }}
    .dl {{ background: #27ae60; }} .st {{ background: #2980b9; }} .tg {{ background: #0088cc; }}
    .ss-img {{ width: 100%; max-width: 200px; border-radius: 5px; margin-top: 10px; border: 1px solid #444; }}

    /* Admin Interface */
    .admin-nav {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 15px 0; }}
    .admin-nav a {{ color: white; text-decoration: none; font-size: 12px; background: #333; padding: 8px 12px; border-radius: 4px; border: 1px solid var(--primary); }}
    .admin-table {{ width: 100%; border-collapse: collapse; }}
    .admin-table th, .admin-table td {{ padding: 10px; border: 1px solid #333; text-align: left; font-size: 13px; }}
    .form-card {{ max-width: 800px; margin: auto; background: #1a1a1a; padding: 25px; border-radius: 10px; border: 1px solid #333; }}
    input, textarea {{ width: 100%; padding: 10px; margin: 5px 0; background: #222; color: white; border: 1px solid #444; border-radius: 5px; box-sizing: border-box; }}
    .submit-btn {{ background: var(--primary); color: white; border: none; padding: 12px; width: 100%; cursor: pointer; font-weight: bold; border-radius: 5px; margin-top: 15px; }}
    .reset-btn {{ background: #555; margin-top: 10px; }}
    .ep-input-group {{ background: #262626; padding: 10px; border-radius: 5px; margin-bottom: 10px; border: 1px dashed #555; position: relative; }}
</style>
"""

# --- লিঙ্ক শর্টনার লজিক ---
def shorten_link(config, original_url):
    if config['shortener_url'] and config['shortener_api'] and original_url.strip():
        # উদাহরণ: https://api.shorte.st/st?api=KEY&url=URL
        return f"{config['shortener_url']}{config['shortener_api']}&url={original_url.strip()}"
    return original_url.strip()

# --- ইউজার প্যানেল ---

@app.route('/')
def home():
    s = get_site_config()
    q = request.args.get('q', '')
    movies = list(series_collection.find({"title": {"$regex": q, "$options": "i"}}).sort("_id", -1))
    
    html = f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{get_css(s)}</head><body>"
    html += f"<header><a href='/' class='logo'>{s['site_name']}</a><form action='/' class='search-box'><input name='q' placeholder='মুভি খুঁজুন...' value='{q}'><button>Search</button></form></header>"
    html += "<div class='container'>"
    for ad in s['ads']: html += f"<div class='ad-slot'>{ad}</div>"
    html += "<div class='grid'>"
    for m in movies:
        html += f"<a href='/series/{m['_id']}' class='card'>"
        if m.get("btl"): html += f"<div class='badge-tl'>{m['btl']}</div>"
        if m.get("btr"): html += f"<div class='badge-tr'>{m['btr']}</div>"
        if m.get("bbl"): html += f"<div class='badge-bl'>{m['bbl']}</div>"
        if m.get("bbr"): html += f"<div class='badge-br'>{m['bbr']}</div>"
        html += f"<img src='{m['poster']}'><div class='card-info'>{m['title']} ({m['year']})</div></a>"
    html += "</div></div></body></html>"
    return render_template_string(html)

@app.route('/series/<id>')
def detail(id):
    s = get_site_config()
    m = series_collection.find_one({"_id": ObjectId(id)})
    html = f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{get_css(s)}</head><body><header><a href='/' class='logo'>{s['site_name']}</a></header><div class='container'>"
    html += f"<div class='detail-flex'><img src='{m['poster']}' class='detail-img'><div><h1>{m['title']} ({m['year']})</h1>"
    html += f"<p>ভাষা: <span style='color:var(--lang)'>{m['language']}</span> | সাল: {m['year']}</p>"
    html += f"<div class='story'><b>গল্প:</b><br>{m['description']}</div></div></div><hr style='border:0.1px solid #333; margin:20px 0'><h3>এপিসোড সমূহ:</h3>"
    
    for ep in m['episodes']:
        html += f"<div class='ep-box'><div class='ep-meta'><span>Episode: {ep['ep_no']}</span><span>Quality: {ep.get('quality', 'HD')}</span></div>"
        if ep.get('ss'): html += f"<img src='{ep['ss']}' class='ss-img'><br>"
        html += f"<div class='btn-group'>"
        if ep['dl_link']: html += f"<a href='{ep['dl_link']}' class='btn dl' target='_blank'>Download</a>"
        if ep['st_link']: html += f"<a href='{ep['st_link']}' class='btn st' target='_blank'>Stream</a>"
        if ep['tg_link']: html += f"<a href='{ep['tg_link']}' class='btn tg' target='_blank'>Telegram</a>"
        html += "</div></div>"
    html += "</div></body></html>"
    return render_template_string(html)

# --- অ্যাডমিন প্যানেল ---

@app.route('/admin')
def admin_dashboard():
    s = get_site_config()
    q = request.args.get('q', '')
    movies = list(series_collection.find({"title": {"$regex": q, "$options": "i"}}).sort("_id", -1))
    html = f"<html><head>{get_css(s)}</head><body><header><a href='/admin' class='logo'>Admin Panel</a></header><div class='container'>"
    html += "<div class='admin-nav'><a href='/admin/add'>+ Add Movie</a><a href='/admin/settings'>⚙ Settings & Ads</a><a href='/' style='background:red'>View Site</a></div>"
    html += "<table class='admin-table'><tr><th>Poster</th><th>Title</th><th>Action</th></tr>"
    for m in movies:
        html += f"<tr><td><img src='{m['poster']}' width='40'></td><td>{m['title']}</td><td><a href='/admin/edit/{m['_id']}' style='color:orange'>Edit</a> | <form action='/admin/delete/{m['_id']}' method='POST' style='display:inline'><button style='color:red; background:none; border:none; cursor:pointer'>Delete</button></form></td></tr>"
    return render_template_string(html + "</table></div></body></html>")

@app.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    s = get_site_config()
    if request.method == 'POST':
        if 'reset' in request.form:
            settings_collection.update_one({"type": "config"}, {"$set": DEFAULT_CONFIG})
        else:
            settings_collection.update_one({"type": "config"}, {"$set": {
                "site_name": request.form.get('site_name'),
                "primary_color": request.form.get('p_color'),
                "bg_color": request.form.get('b_color'),
                "card_bg": request.form.get('c_color'),
                "text_color": request.form.get('t_color'),
                "badge_color": request.form.get('badge_color'),
                "lang_color": request.form.get('lang_color'),
                "shortener_url": request.form.get('sh_url'),
                "shortener_api": request.form.get('sh_api'),
                "ads": [ad for ad in request.form.getlist('ads[]') if ad.strip()]
            }})
        return redirect('/admin/settings')

    html = f"<html><head>{get_css(s)}</head><body><header><a href='/admin' class='logo'>Settings</a></header><div class='container'><div class='form-card'>"
    html += "<form method='POST'><h3>সাইট এবং কালার সেটিংস</h3><label>সাইট নেম:</label><input name='site_name' value='"+s['site_name']+"'>"
    html += "<div style='display:grid; grid-template-columns: 1fr 1fr; gap:10px;'>"
    for k, v in [('p_color','primary_color'),('b_color','bg_color'),('c_color','card_bg'),('t_color','text_color'),('badge_color','badge_color'),('lang_color','lang_color')]:
        html += f"<div><label>{k}:</label><input type='color' name='{k}' value='{s[v]}'></div>"
    html += "</div><hr><h3>লিঙ্ক শর্টনার সেটিংস</h3><label>Base URL (API Link):</label><input name='sh_url' value='"+s['shortener_url']+"' placeholder='https://short.me/api?api='><label>API Key:</label><input name='sh_api' value='"+s['shortener_api']+"'><hr><h3>বিজ্ঞাপন ও রিসেট</h3>"
    html += "<div id='ad-list'>"
    for ad in s['ads']: html += f"<textarea name='ads[]' rows='2'>{ad}</textarea>"
    html += "</div><button type='button' onclick='addAd()'>+ Add Ad Slot</button><button class='submit-btn'>Save Settings</button><button name='reset' value='1' class='submit-btn reset-btn' onclick='return confirm(\"রিসেট করবেন?\")'>Reset to Default Colors</button></form></div></div>"
    return render_template_string(html + "<script>function addAd(){document.getElementById('ad-list').insertAdjacentHTML('beforeend', '<textarea name=\"ads[]\" rows=\"2\"></textarea>')}</script></body></html>")

@app.route('/admin/add', methods=['GET', 'POST'])
@app.route('/admin/edit/<id>', methods=['GET', 'POST'])
def manage_movie(id=None):
    s = get_site_config()
    m = series_collection.find_one({"_id": ObjectId(id)}) if id else None
    if request.method == 'POST':
        ep_nos = request.form.getlist('ep_no[]')
        qs = request.form.getlist('q[]')
        ss_links = request.form.getlist('ss[]')
        dls = request.form.getlist('dl[]')
        sts = request.form.getlist('st[]')
        tgs = request.form.getlist('tg[]')
        eps = []
        for i in range(len(ep_nos)):
            eps.append({"ep_no": ep_nos[i], "quality": qs[i], "ss": ss_links[i], 
                        "dl_link": shorten_link(s, dls[i]), "st_link": shorten_link(s, sts[i]), "tg_link": shorten_link(s, tgs[i])})
        data = {"title": request.form.get('t'), "year": request.form.get('y'), "language": request.form.get('l'), "poster": request.form.get('p'), 
                "btl": request.form.get('btl'), "btr": request.form.get('btr'), "bbl": request.form.get('bbl'), "bbr": request.form.get('bbr'),
                "description": request.form.get('d'), "episodes": eps}
        if id: series_collection.update_one({"_id": ObjectId(id)}, {"$set": data})
        else: series_collection.insert_one(data)
        return redirect('/admin')

    html = f"<html><head>{get_css(s)}</head><body><header><a href='/admin' class='logo'>Manage</a></header><div class='container'><div class='form-card'><form method='POST'>"
    html += f"<h3>মুভি তথ্য</h3><input name='t' placeholder='মুভির নাম' value='{m['title'] if m else ''}' required><div style='display:flex; gap:10px'><input name='y' placeholder='সাল' value='{m['year'] if m else ''}'><input name='l' placeholder='ভাষা' value='{m['language'] if m else ''}'></div>"
    html += f"<input name='p' placeholder='পোস্টার লিঙ্ক' value='{m['poster'] if m else ''}' required>"
    html += f"<div style='display:grid; grid-template-columns: 1fr 1fr; gap:5px'><input name='btl' placeholder='Badge TL' value='{m['btl'] if m else ''}'><input name='btr' placeholder='Badge TR' value='{m['btr'] if m else ''}'><input name='bbl' placeholder='Badge BL' value='{m['bbl'] if m else ''}'><input name='bbr' placeholder='Badge BR' value='{m['bbr'] if m else ''}'></div>"
    html += f"<textarea name='d' placeholder='গল্প'>{m['description'] if m else ''}</textarea><h3>এপিসোড সমূহ</h3><div id='ep-area'>"
    if m:
        for e in m['episodes']: html += f"<div class='ep-input-group'><input name='ep_no[]' value='{e['ep_no']}' placeholder='নং'><input name='q[]' value='{e.get('quality','')}' placeholder='Quality'><input name='ss[]' value='{e.get('ss','')}' placeholder='Screenshot'><input name='dl[]' value='{e['dl_link']}' placeholder='DL'><input name='st[]' value='{e['st_link']}' placeholder='ST'><input name='tg[]' value='{e['tg_link']}' placeholder='TG'></div>"
    else: html += "<div class='ep-input-group'><input name='ep_no[]' placeholder='নং'><input name='q[]' placeholder='Quality'><input name='ss[]' placeholder='Screenshot'><input name='dl[]' placeholder='DL'><input name='st[]' placeholder='ST'><input name='tg[]' placeholder='TG'></div>"
    html += "</div><button type='button' onclick='addEp()'>+ Add Episode</button><button class='submit-btn'>Save Movie</button></form></div></div>"
    return render_template_string(html + "<script>function addEp(){document.getElementById('ep-area').insertAdjacentHTML('beforeend', '<div class=\"ep-input-group\"><input name=\"ep_no[]\" placeholder=\"নং\"><input name=\"q[]\" placeholder=\"Quality\"><input name=\"ss[]\" placeholder=\"Screenshot\"><input name=\"dl[]\" placeholder=\"DL\"><input name=\"st[]\" placeholder=\"ST\"><input name=\"tg[]\" placeholder=\"TG\"></div>')}</script></body></html>")

@app.route('/admin/delete/<id>', methods=['POST'])
def delete_movie(id):
    series_collection.delete_one({"_id": ObjectId(id)})
    return redirect('/admin')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
