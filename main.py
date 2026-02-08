import os
from flask import Flask, render_template_string, request, redirect, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = "final_ultra_movie_site_system"

# --- MongoDB Connection ---
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
client = MongoClient(MONGO_URI)
db = client['webseries_db']
movies_col = db['movies']
config_col = db['settings']

# --- ডিফল্ট সেটিংস (রিসেট লজিক) ---
DEFAULT_CONFIG = {
    "site_name": "WebSeries BD",
    "primary_color": "#E50914",
    "bg_color": "#0b0b0b",
    "text_color": "#ffffff",
    "lang_color": "#aaaaaa",
    "slider_count": 5,
    "sh_url": "",
    "sh_api": "",
    "ads": []
}

def get_config():
    conf = config_col.find_one({"type": "site_config"})
    if not conf:
        config_col.insert_one({"type": "site_config", **DEFAULT_CONFIG})
        return DEFAULT_CONFIG
    return conf

# --- ডাইনামিক এবং রেসপন্সিভ CSS (Auto Mobile & Desktop Mode) ---
def get_css(s):
    return f"""
<style>
    :root {{ 
        --primary: {s['primary_color']}; --bg: {s['bg_color']}; --text: {s['text_color']}; --lang: {s['lang_color']};
    }}
    body {{ background: var(--bg); color: var(--text); font-family: 'Segoe UI', sans-serif; margin: 0; padding: 0; overflow-x: hidden; }}
    
    header {{ background: #000; padding: 10px 5%; display: flex; flex-direction: column; align-items: center; border-bottom: 2px solid var(--primary); position: sticky; top: 0; z-index: 1000; }}
    @media (min-width: 768px) {{ header {{ flex-direction: row; justify-content: space-between; }} }}
    .logo {{ color: var(--primary); font-size: 24px; font-weight: bold; text-decoration: none; text-transform: uppercase; }}
    
    .search-box {{ display: flex; background: #222; border-radius: 5px; overflow: hidden; margin: 10px 0; border: 1px solid #333; width: 100%; max-width: 400px; }}
    .search-box input {{ border: none; background: transparent; color: white; padding: 8px 12px; width: 100%; outline: none; }}
    .search-box button {{ background: var(--primary); border: none; color: white; padding: 0 15px; cursor: pointer; }}
    
    .container {{ padding: 20px 5%; }}
    
    /* Slider */
    .slider {{ width: 100%; height: 220px; overflow: hidden; position: relative; border-radius: 10px; margin-bottom: 20px; border: 1px solid #333; }}
    @media (min-width: 768px) {{ .slider {{ height: 400px; }} }}
    .slide {{ width: 100%; height: 100%; position: absolute; display: none; }}
    .slide.active {{ display: block; }}
    .slide img {{ width: 100%; height: 100%; object-fit: cover; filter: brightness(0.6); }}
    .slide-info {{ position: absolute; bottom: 20px; left: 20px; z-index: 10; }}
    .slide-info h2 {{ font-size: 20px; margin: 0; }}

    /* Grid System */
    .grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }}
    @media (min-width: 768px) {{ .grid {{ grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 20px; }} }}

    .card {{ background: #151515; border-radius: 8px; overflow: hidden; position: relative; text-decoration: none; color: white; border: 1px solid #333; display: block; transition: 0.3s; }}
    .card:hover {{ transform: translateY(-5px); border-color: var(--primary); }}
    .card img {{ width: 100%; aspect-ratio: 2/3; object-fit: cover; }}
    
    /* 4 Corner Badge System */
    .btl, .btr, .bbl, .bbr {{ position: absolute; padding: 2px 7px; font-size: 10px; font-weight: bold; border-radius: 3px; color: white; z-index: 10; }}
    .btl {{ top: 5px; left: 5px; }} .btr {{ top: 5px; right: 5px; }} 
    .bbl {{ bottom: 45px; left: 5px; }} .bbr {{ bottom: 45px; right: 5px; }}

    .card-info {{ padding: 8px; text-align: center; font-size: 13px; font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}

    /* Detail View */
    .detail-container {{ max-width: 900px; margin: auto; }}
    .detail-img {{ width: 100%; max-width: 250px; border-radius: 10px; border: 1px solid #333; display: block; margin: 0 auto 20px; }}
    .story {{ background: #111; padding: 15px; border-radius: 8px; border-left: 4px solid var(--primary); margin: 15px 0; color: #ccc; line-height: 1.6; }}
    
    .ep-box {{ background: #1a1a1a; padding: 15px; border-radius: 8px; margin-bottom: 10px; border: 1px solid #333; }}
    .btn {{ padding: 10px; border-radius: 4px; text-decoration: none; color: white; font-size: 12px; font-weight: bold; text-align: center; display: inline-block; margin-right: 5px; margin-top: 5px; }}
    .dl {{ background: #27ae60; }} .st {{ background: #2980b9; }} .tg {{ background: #0088cc; }}
    
    .ad-slot {{ margin: 20px 0; text-align: center; }}

    /* Admin UI */
    .admin-nav {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px; }}
    .admin-nav a {{ color: white; text-decoration: none; background: #333; padding: 10px 15px; border-radius: 4px; border: 1px solid var(--primary); font-size: 13px; }}
    .form-card {{ max-width: 800px; margin: auto; background: #1a1a1a; padding: 25px; border-radius: 10px; border: 1px solid #333; }}
    input, textarea, select {{ width: 100%; padding: 12px; margin: 8px 0; background: #222; color: white; border: 1px solid #444; border-radius: 5px; box-sizing: border-box; }}
    .submit-btn {{ background: var(--primary); color: white; border: none; padding: 15px; width: 100%; cursor: pointer; font-weight: bold; border-radius: 5px; margin-top: 10px; }}
</style>
"""

# --- লিঙ্ক শর্টনার লজিক ---
def shorten_link(conf, url):
    if conf['sh_url'] and conf['sh_api'] and url.strip():
        return f"{conf['sh_url']}{conf['sh_api']}&url={url.strip()}"
    return url.strip()

# --- ইউজার প্যানেল রাউটস ---

@app.route('/')
def home():
    s = get_config()
    q = request.args.get('q', '')
    filt = {"title": {"$regex": q, "$options": "i"}} if q else {}
    movies = list(movies_col.find(filt).sort("_id", -1))
    slider_movies = movies[:int(s['slider_count'])]
    
    html = f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{get_css(s)}</head><body>"
    html += f"<header><a href='/' class='logo'>{s['site_name']}</a><form action='/' class='search-box'><input name='q' placeholder='খুঁজুন...' value='{q}'><button>Search</button></form></header>"
    
    html += "<div class='container'>"
    # Ads (Top)
    for ad in s['ads']: html += f"<div class='ad-slot'>{ad}</div>"
    
    # স্লাইডার
    if not q and slider_movies:
        html += "<div class='slider'>"
        for i, m in enumerate(slider_movies):
            html += f"<div class='slide {'active' if i==0 else ''}'><a href='/movie/{m['_id']}'><img src='{m['poster']}'><div class='slide-info'><h2>{m['title']}</h2></div></a></div>"
        html += "</div>"

    html += "<div class='grid'>"
    for m in movies:
        html += f"<a href='/movie/{m['_id']}' class='card'>"
        if m.get('btl'): html += f"<div class='btl' style='background:{m.get('btl_c', '#E50914')}'>{m['btl']}</div>"
        if m.get('btr'): html += f"<div class='btr' style='background:{m.get('btr_c', '#000000aa')}'>{m['btr']}</div>"
        if m.get('bbl'): html += f"<div class='bbl' style='background:{m.get('bbl_c', 'orange')}'>{m['bbl']}</div>"
        if m.get('bbr'): html += f"<div class='bbr' style='background:{m.get('bbr_c', '#27ae60')}'>{m['bbr']}</div>"
        html += f"<img src='{m['poster']}'><div class='card-info'>{m['title']} ({m['year']})</div></a>"
    html += "</div></div>"
    
    return render_template_string(html + """<script>
        let slides = document.querySelectorAll('.slide'); let current = 0;
        if(slides.length > 1) { setInterval(() => { slides[current].classList.remove('active'); current = (current + 1) % slides.length; slides[current].classList.add('active'); }, 4000); }
    </script></body></html>""")

@app.route('/movie/<id>')
def detail(id):
    s = get_config()
    m = movies_col.find_one({"_id": ObjectId(id)})
    html = f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{get_css(s)}</head><body><header><a href='/' class='logo'>{s['site_name']}</a></header><div class='container detail-container'>"
    html += f"<img src='{m['poster']}' class='detail-img'><h1>{m['title']} ({m['year']})</h1>"
    html += f"<p>ভাষা: <span style='color:var(--lang)'>{m['language']}</span></p><div class='story'>{m['description']}</div><hr><h3>ইপিসোড সমূহ:</h3>"
    for ep in m['episodes']:
        html += f"<div class='ep-box'><strong>Ep: {ep['ep_no']} - {ep['q']}</strong><br>"
        if ep['dl']: html += f"<a href='{ep['dl']}' class='btn dl' target='_blank'>Download</a>"
        if ep['st']: html += f"<a href='{ep['st']}' class='btn st' target='_blank'>Stream</a>"
        if ep['tg']: html += f"<a href='{ep['tg']}' class='btn tg' target='_blank'>Telegram</a>"
        html += "</div>"
    return render_template_string(html + "</div></body></html>")

# --- এডমিন সেকশন রাউটস ---

@app.route('/admin')
def admin():
    s = get_config()
    q = request.args.get('q', '')
    filt = {"title": {"$regex": q, "$options": "i"}} if q else {}
    movies = list(movies_col.find(filt).sort("_id", -1))
    html = f"<html><head>{get_css(s)}</head><body><header><a href='/admin' class='logo'>Admin Panel</a><form action='/admin' class='search-box'><input name='q' placeholder='মুভি খুঁজুন...' value='{q}'><button>Search</button></form></header><div class='container'>"
    html += "<div class='admin-nav'><a href='/admin/add'>+ Add Movie</a><a href='/admin/settings'>⚙ Site Settings</a><a href='/' style='background:red'>View Site</a></div>"
    html += "<table border='1' width='100%' style='border-collapse:collapse; color:white'><tr><th>Title</th><th>Action</th></tr>"
    for m in movies:
        html += f"<tr><td>{m['title']}</td><td><a href='/admin/edit/{m['_id']}' style='color:orange'>Edit</a> | <form action='/admin/delete/{m['_id']}' method='POST' style='display:inline'><button style='color:red; background:none; border:none; cursor:pointer'>Delete</button></form></td></tr>"
    return render_template_string(html + "</table></div></body></html>")

@app.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    s = get_config()
    if request.method == 'POST':
        if 'reset' in request.form:
            config_col.update_one({"type": "site_config"}, {"$set": DEFAULT_CONFIG})
        else:
            config_col.update_one({"type": "site_config"}, {"$set": {
                "site_name": request.form.get('site_name'), "primary_color": request.form.get('p_c'), "bg_color": request.form.get('b_c'),
                "text_color": request.form.get('t_c'), "lang_color": request.form.get('l_c'), "slider_count": request.form.get('sc'),
                "sh_url": request.form.get('sh_u'), "sh_api": request.form.get('sh_a'), "ads": request.form.getlist('ads[]')
            }})
        return redirect('/admin/settings')
    
    html = f"<html><head>{get_css(s)}</head><body><header><a href='/admin' class='logo'>Settings</a></header><div class='container'><div class='form-card'><form method='POST'>"
    html += f"সাইট নাম: <input name='site_name' value='{s['site_name']}'>"
    html += f"থিম কালার: <input type='color' name='p_c' value='{s['primary_color']}'> ব্যাকগ্রাউন্ড: <input type='color' name='b_c' value='{s['bg_color']}'>"
    html += f"টেক্সট কালার: <input type='color' name='t_c' value='{s['text_color']}'> ভাষা কালার: <input type='color' name='l_c' value='{s['lang_color']}'>"
    html += f"স্লাইডার মুভি সংখ্যা: <input type='number' name='sc' value='{s['slider_count']}'>"
    html += f"Link Shortener API URL: <input name='sh_u' value='{s['sh_url']}' placeholder='https://short.com/api?api='> Key: <input name='sh_a' value='{s['sh_api']}'>"
    html += "<h4>আনলিমিটেড বিজ্ঞাপন</h4><div id='ad-area'>"
    for ad in s.get('ads', []): html += f"<textarea name='ads[]' rows='3'>{ad}</textarea>"
    html += "</div><button type='button' onclick='addAd()'>+ Add Ad Slot</button>"
    html += "<button class='submit-btn'>Save All Settings</button><button name='reset' class='submit-btn' style='background:#555; margin-top:10px'>Reset Colors & Settings</button></form></div></div>"
    return render_template_string(html + "<script>function addAd(){document.getElementById('ad-area').insertAdjacentHTML('beforeend', '<textarea name=\"ads[]\" rows=\"3\"></textarea>')}</script></body></html>")

@app.route('/admin/add', methods=['GET', 'POST'])
@app.route('/admin/edit/<id>', methods=['GET', 'POST'])
def save_movie(id=None):
    s = get_config()
    m = movies_col.find_one({"_id": ObjectId(id)}) if id else None
    if request.method == 'POST':
        en, qu, dl, st, tg = request.form.getlist('en[]'), request.form.getlist('q[]'), request.form.getlist('dl[]'), request.form.getlist('st[]'), request.form.getlist('tg[]')
        eps = []
        for i in range(len(en)):
            eps.append({"ep_no": en[i], "q": qu[i], "dl": shorten_link(s, dl[i]), "st": shorten_link(s, st[i]), "tg": shorten_link(s, tg[i])})
        data = {
            "title": request.form.get('t'), "year": request.form.get('y'), "language": request.form.get('l'), "poster": request.form.get('p'), "description": request.form.get('d'),
            "btl": request.form.get('btl'), "btl_c": request.form.get('btl_c'), "btr": request.form.get('btr'), "btr_c": request.form.get('btr_c'),
            "bbl": request.form.get('bbl'), "bbl_c": request.form.get('bbl_c'), "bbr": request.form.get('bbr'), "bbr_c": request.form.get('bbr_c'),
            "episodes": eps
        }
        if id: movies_col.update_one({"_id": ObjectId(id)}, {"$set": data})
        else: movies_col.insert_one(data)
        return redirect('/admin')
    
    html = f"<html><head>{get_css(s)}</head><body><header><a href='/admin' class='logo'>Save Movie</a></header><div class='container'><div class='form-card'><form method='POST'>"
    html += f"<input name='t' placeholder='মুভির নাম' value='{m['title'] if m else ''}' required><div style='display:flex; gap:5px'><input name='y' placeholder='সাল' value='{m['year'] if m else ''}'><input name='l' placeholder='ভাষা' value='{m['language'] if m else ''}'></div>"
    html += f"<input name='p' placeholder='পোস্টার লিঙ্ক' value='{m['poster'] if m else ''}' required><textarea name='d' placeholder='গল্প'>{m['description'] if m else ''}</textarea>"
    html += "<h4>৪ কোণায় ৪ ব্যাজ এবং কালার</h4>"
    for b in [('btl', 'Top Left'), ('btr', 'Top Right'), ('bbl', 'Bottom Left'), ('bbr', 'Bottom Right')]:
        html += f"{b[1]}: <input name='{b[0]}' value='{m.get(b[0], '')}' style='width:30%'> <input type='color' name='{b[0]}_c' value='{m.get(b[0]+'_c', '#e50914')}' style='width:15%'> "
    html += "<h4>ইপিসোড সমূহ</h4><div id='e-area'>"
    if m:
        for e in m['episodes']: html += f"<div style='border:1px dashed #555;padding:10px;margin-bottom:5px'><input name='en[]' value='{e['ep_no']}' placeholder='নং'><input name='q[]' value='{e['q']}' placeholder='Quality'><input name='dl[]' value='{e['dl']}' placeholder='DL'><input name='st[]' value='{e['st']}' placeholder='ST'><input name='tg[]' value='{e['tg']}' placeholder='TG'></div>"
    else: html += "<div style='border:1px dashed #555;padding:10px;margin-bottom:5px'><input name='en[]' placeholder='Ep নং'><input name='q[]' placeholder='Quality'><input name='dl[]' placeholder='Download Link'><input name='st[]' placeholder='Stream Link'><input name='tg[]' placeholder='Telegram Link'></div>"
    html += "</div><button type='button' onclick='addE()' style='width:100%'>+ Add More Episode</button><button class='submit-btn'>Publish Movie</button></form></div></div>"
    return render_template_string(html + "<script>function addE(){document.getElementById('e-area').insertAdjacentHTML('beforeend', '<div style=\"border:1px dashed #555;padding:10px;margin-bottom:5px\"><input name=\"en[]\" placeholder=\"Ep নং\"><input name=\"q[]\" placeholder=\"Quality\"><input name=\"dl[]\" placeholder=\"DL\"><input name=\"st[]\" placeholder=\"ST\"><input name=\"tg[]\" placeholder=\"TG\"></div>')}</script></body></html>")

@app.route('/admin/delete/<id>', methods=['POST'])
def delete(id):
    movies_col.delete_one({"_id": ObjectId(id)})
    return redirect('/admin')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
