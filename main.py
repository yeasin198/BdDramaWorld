from flask import Flask, render_template_string, request, redirect, url_for, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
import requests

app = Flask(__name__)
app.secret_key = "movie_pro_final_v2"

# --- MongoDB কানেকশন ---
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client.movie_database
movies_col = db.movies
settings_col = db.settings

# --- Helper: URL Shortener ---
def shorten_link(url):
    config = settings_col.find_one({"type": "config"})
    if config and config.get('api') and url and url.strip():
        # অনেক API {url} প্লেসহোল্ডার ব্যবহার করে
        api_url = config.get('api').replace("{url}", url)
        try:
            r = requests.get(api_url, timeout=5)
            return r.text.strip() if r.status_code == 200 else url
        except:
            return url
    return url

# --- UI Styles ---
HEAD_CSS = """
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<script src="https://cdn.tailwindcss.com"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
<style>
    body { background-color: #0b0f19; color: white; font-family: 'Inter', sans-serif; }
    .glass { background: rgba(255, 255, 255, 0.03); backdrop-filter: blur(15px); border: 1px solid rgba(255,255,255,0.05); }
    .corner-tag { position: absolute; padding: 2px 8px; font-size: 10px; font-weight: bold; border-radius: 4px; z-index: 10; }
</style>
"""

def get_ads():
    ads = settings_col.find_one({"type": "ads"})
    return ads if ads else {"top": "", "bottom": "", "popup": ""}

# --- ROUTES ---

@app.route('/')
def index():
    query = request.args.get('q')
    ads = get_ads()
    movies = list(movies_col.find({"name": {"$regex": query, "$options": "i"}})) if query else list(movies_col.find())
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>{HEAD_CSS}<title>MoviePro</title></head>
    <body>
        <nav class="p-4 glass sticky top-0 z-50 flex justify-between items-center px-6">
            <a href="/" class="text-2xl font-black text-blue-500">MOVIE<span class="text-white">PRO</span></a>
            <form action="/" class="hidden md:flex bg-gray-900 border border-gray-700 rounded-lg overflow-hidden">
                <input name="q" placeholder="Search..." class="bg-transparent p-2 px-4 outline-none w-64 text-sm text-white">
                <button class="px-4 text-blue-500"><i class="fa fa-search"></i></button>
            </form>
            <a href="/admin" class="bg-blue-600 px-5 py-2 rounded-full text-xs font-bold uppercase tracking-wider">Admin</a>
        </nav>

        <div class="max-w-7xl mx-auto p-6">
            <div class="mb-6 text-center">{ads['top']}</div>
            <div class="grid grid-cols-2 md:grid-cols-5 gap-6">
                {{% for movie in movies %}}
                <a href="/movie/{{{{ movie._id }}}}" class="group block relative rounded-2xl overflow-hidden shadow-2xl aspect-[2/3] border border-white/5">
                    <span class="corner-tag top-2 left-2 bg-blue-600">{{{{ movie.tag1 }}}}</span>
                    <span class="corner-tag top-2 right-2 bg-red-600">{{{{ movie.tag2 }}}}</span>
                    <span class="corner-tag bottom-2 left-2 bg-yellow-500 text-black">{{{{ movie.tag3 }}}}</span>
                    <span class="corner-tag bottom-2 right-2 bg-green-600">{{{{ movie.tag4 }}}}</span>
                    <img src="{{{{ movie.poster }}}}" class="w-full h-full object-cover group-hover:scale-110 transition duration-500">
                    <div class="absolute inset-0 bg-gradient-to-t from-black via-transparent to-transparent"></div>
                    <div class="absolute bottom-3 left-3 right-3 text-xs font-bold truncate">{{{{ movie.name }}}}</div>
                </a>
                {{% endfor %}}
            </div>
            <div class="mt-10 text-center">{ads['bottom']}</div>
        </div>
        {ads['popup']}
    </body>
    </html>
    """
    return render_template_string(html, movies=movies)

@app.route('/movie/<id>')
def movie_details(id):
    movie = movies_col.find_one({"_id": ObjectId(id)})
    ads = get_ads()
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>{HEAD_CSS}<title>{{{{ movie.name }}}}</title></head>
    <body class="p-4 md:p-10">
        <div class="max-w-5xl mx-auto">
            <div class="md:flex gap-10 glass p-8 rounded-3xl border border-white/10">
                <img src="{{{{ movie.poster }}}}" class="w-full md:w-72 rounded-2xl shadow-2xl mb-6">
                <div>
                    <h1 class="text-4xl font-black mb-4">{{{{ movie.name }}}} ({{{{ movie.year }}}})</h1>
                    <p class="text-blue-400 font-bold mb-6 italic">{{{{ movie.lang }}}}</p>
                    <p class="text-gray-400 leading-relaxed">{{{{ movie.story }}}}</p>
                </div>
            </div>

            <div class="mt-12 text-center">{ads['top']}</div>

            <h2 class="text-2xl font-bold mt-16 mb-8 italic">Watch Episodes:</h2>
            <div class="space-y-6">
                {{% for ep in movie.episodes %}}
                <div class="glass p-6 rounded-3xl border-l-4 border-blue-600">
                    <h3 class="font-bold text-lg mb-4 text-blue-300">Episode: {{{{ ep.ep_no }}}}</h3>
                    <div class="grid md:grid-cols-2 gap-4">
                        {{% for link in ep.links %}}
                        <div class="bg-black/30 p-4 rounded-xl border border-gray-800">
                            <span class="text-[10px] uppercase text-gray-500 block mb-3 font-bold">Quality: {{{{ link.quality }}}}</span>
                            <div class="flex gap-2">
                                <a href="{{{{ link.stream }}}}" class="bg-blue-600 p-2 px-4 rounded-lg text-xs font-bold grow text-center">STREAM</a>
                                <a href="{{{{ link.download }}}}" class="bg-green-600 p-2 px-4 rounded-lg text-xs font-bold grow text-center">DOWN</a>
                                <a href="{{{{ link.telegram }}}}" class="bg-sky-500 p-2 px-4 rounded-lg text-xs font-bold grow text-center text-white"><i class="fab fa-telegram"></i></a>
                            </div>
                        </div>
                        {{% endfor %}}
                    </div>
                </div>
                {{% endfor %}}
            </div>
            <div class="mt-12 text-center">{ads['bottom']}</div>
        </div>
        {ads['popup']}
    </body>
    </html>
    """
    return render_template_string(html, movie=movie)

# --- ADMIN ROUTES ---

@app.route('/admin')
def admin():
    q = request.args.get('q')
    movies = list(movies_col.find({"name": {"$regex": q, "$options": "i"}})) if q else list(movies_col.find())
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>{HEAD_CSS}<title>Admin Dashboard</title></head>
    <body class="p-6">
        <div class="max-w-6xl mx-auto">
            <div class="flex flex-col md:flex-row justify-between items-center mb-10 gap-4">
                <h1 class="text-2xl font-black italic text-blue-500">ADMIN PANEL</h1>
                <div class="flex gap-4">
                    <form action="/admin" class="flex bg-gray-900 rounded-xl overflow-hidden border border-gray-800">
                        <input name="q" placeholder="Search..." class="bg-transparent p-2 px-4 outline-none text-sm">
                        <button class="px-4 text-blue-500"><i class="fa fa-search"></i></button>
                    </form>
                    <a href="/admin/add" class="bg-green-600 p-3 px-6 rounded-xl font-bold text-sm">+ MOVIE</a>
                    <a href="/admin/settings" class="bg-gray-800 p-3 px-6 rounded-xl font-bold text-sm">SETTINGS</a>
                </div>
            </div>
            <div class="grid gap-4">
                {{% for m in movies %}}
                <div class="glass p-4 rounded-2xl flex justify-between items-center">
                    <div class="flex items-center gap-4">
                        <img src="{{{{ m.poster }}}}" class="w-12 h-16 object-cover rounded">
                        <h3 class="font-bold">{{{{ m.name }}}}</h3>
                    </div>
                    <div class="flex gap-3">
                        <a href="/admin/edit/{{{{ m._id }}}}" class="text-yellow-500 p-2"><i class="fa fa-edit"></i></a>
                        <a href="/admin/delete/{{{{ m._id }}}}" class="text-red-500 p-2" onclick="return confirm('Delete?')"><i class="fa fa-trash"></i></a>
                    </div>
                </div>
                {{% endfor %}}
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html, movies=movies)

@app.route('/admin/add', methods=['GET', 'POST'])
@app.route('/admin/edit/<id>', methods=['GET', 'POST'])
def edit_movie(id=None):
    movie = movies_col.find_one({"_id": ObjectId(id)}) if id else None
    if request.method == 'POST':
        data = {
            "name": request.form['name'], "poster": request.form['poster'],
            "year": request.form['year'], "lang": request.form['lang'],
            "tag1": request.form['tag1'], "tag2": request.form['tag2'],
            "tag3": request.form['tag3'], "tag4": request.form['tag4'],
            "story": request.form['story']
        }
        if id:
            movies_col.update_one({"_id": ObjectId(id)}, {"$set": data})
        else:
            data['episodes'] = []
            movies_col.insert_one(data)
        return redirect('/admin')

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>{HEAD_CSS}</head>
    <body class="p-6">
        <form method="POST" class="max-w-3xl mx-auto glass p-8 md:p-12 rounded-[2.5rem] border border-white/10 space-y-6">
            <h2 class="text-2xl font-black italic">{'EDIT MOVIE' if id else 'ADD NEW MOVIE'}</h2>
            <input name="name" value="{{{{ movie.name if movie else '' }}}}" placeholder="Movie Name" class="w-full bg-black/40 p-4 rounded-2xl border border-gray-800 outline-none" required>
            <input name="poster" value="{{{{ movie.poster if movie else '' }}}}" placeholder="Poster Image URL" class="w-full bg-black/40 p-4 rounded-2xl border border-gray-800 outline-none">
            <div class="grid grid-cols-2 gap-4">
                <input name="year" value="{{{{ movie.year if movie else '' }}}}" placeholder="Year" class="bg-black/40 p-4 rounded-2xl border border-gray-800 outline-none">
                <input name="lang" value="{{{{ movie.lang if movie else '' }}}}" placeholder="Language" class="bg-black/40 p-4 rounded-2xl border border-gray-800 outline-none">
            </div>
            <div class="grid grid-cols-4 gap-2">
                <input name="tag1" value="{{{{ movie.tag1 if movie else '' }}}}" placeholder="Tag 1" class="bg-black/40 p-3 rounded-xl border border-gray-800 text-xs">
                <input name="tag2" value="{{{{ movie.tag2 if movie else '' }}}}" placeholder="Tag 2" class="bg-black/40 p-3 rounded-xl border border-gray-800 text-xs">
                <input name="tag3" value="{{{{ movie.tag3 if movie else '' }}}}" placeholder="Tag 3" class="bg-black/40 p-3 rounded-xl border border-gray-800 text-xs">
                <input name="tag4" value="{{{{ movie.tag4 if movie else '' }}}}" placeholder="Tag 4" class="bg-black/40 p-3 rounded-xl border border-gray-800 text-xs">
            </div>
            <textarea name="story" placeholder="Storyline..." class="w-full bg-black/40 p-4 rounded-2xl h-32 border border-gray-800 outline-none">{{{{ movie.story if movie else '' }}}}</textarea>
            <div class="flex gap-4">
                <button class="bg-blue-600 p-4 px-8 rounded-2xl font-black grow">SAVE MOVIE</button>
                {{% if id %}}
                <a href="/admin/episodes/{{{{ id }}}}" class="bg-gray-800 p-4 px-8 rounded-2xl font-bold text-blue-400">EPISODES</a>
                {{% endif %}}
            </div>
        </form>
    </body>
    </html>
    """
    return render_template_string(html, movie=movie, id=id)

# --- EPISODE SYSTEM (FIXED) ---

@app.route('/admin/episodes/<mid>')
def manage_episodes_list(mid):
    movie = movies_col.find_one({"_id": ObjectId(mid)})
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>{HEAD_CSS}</head>
    <body class="p-6">
        <div class="max-w-4xl mx-auto">
            <div class="flex justify-between items-center mb-8">
                <h2 class="text-2xl font-black italic text-blue-400">Episodes: {{{{ movie.name }}}}</h2>
                <a href="/admin/episode/add/{{{{ mid }}}}" class="bg-green-600 p-3 px-6 rounded-xl font-bold text-sm">+ NEW EPISODE</a>
            </div>
            <div class="grid gap-4">
                {{% for ep in movie.episodes %}}
                <div class="glass p-5 rounded-2xl flex justify-between items-center border border-white/5">
                    <span class="font-bold">Episode {{{{ ep.ep_no }}}}</span>
                    <div class="flex gap-4">
                        <a href="/admin/episode/edit/{{{{ mid }}}}/{{{{ loop.index0 }}}}" class="text-yellow-500"><i class="fa fa-edit"></i></a>
                        <a href="/admin/episode/delete/{{{{ mid }}}}/{{{{ loop.index0 }}}}" class="text-red-500" onclick="return confirm('Delete?')"><i class="fa fa-trash"></i></a>
                    </div>
                </div>
                {{% endfor %}}
            </div>
            <div class="mt-10"><a href="/admin" class="text-gray-500 font-bold underline">← Back to Admin</a></div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html, movie=movie, mid=mid)

@app.route('/admin/episode/save', methods=['POST'])
def save_episode():
    mid = request.form['mid']
    idx = request.form.get('idx') # এডিট করলে থাকবে, নতুন এডে থাকবে না
    
    # লিঙ্ক ডাটা তৈরি
    links = []
    for i in [1, 2]:
        links.append({
            "quality": request.form.get(f'q{i}_n'),
            "stream": shorten_link(request.form.get(f'q{i}_s')),
            "download": shorten_link(request.form.get(f'q{i}_d')),
            "telegram": shorten_link(request.form.get(f'q{i}_t'))
        })
    
    new_episode_data = {"ep_no": request.form['ep_no'], "links": links}
    
    if idx is not None and idx != "":
        # বিদ্যমান ইপিসোড এডিট (ইন্ডেক্স অনুযায়ী আপডেট)
        movie = movies_col.find_one({"_id": ObjectId(mid)})
        movie['episodes'][int(idx)] = new_episode_data
        movies_col.update_one({"_id": ObjectId(mid)}, {"$set": {"episodes": movie['episodes']}})
    else:
        # নতুন ইপিসোড যোগ (পুশ)
        movies_col.update_one({"_id": ObjectId(mid)}, {"$push": {"episodes": new_episode_data}})
    
    return redirect(f'/admin/episodes/{mid}')

@app.route('/admin/episode/add/<mid>')
@app.route('/admin/episode/edit/<mid>/<int:idx>')
def episode_form(mid, idx=None):
    movie = movies_col.find_one({"_id": ObjectId(mid)})
    ep = movie['episodes'][idx] if idx is not None else None
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>{HEAD_CSS}</head>
    <body class="p-6">
        <form method="POST" action="/admin/episode/save" class="max-w-2xl mx-auto glass p-8 md:p-12 rounded-[2.5rem] border border-white/10 space-y-8">
            <input type="hidden" name="mid" value="{{{{ mid }}}}">
            <input type="hidden" name="idx" value="{{{{ idx if idx is not None else '' }}}}">
            <h2 class="text-2xl font-black italic">EPISODE SETTINGS</h2>
            <input name="ep_no" value="{{{{ ep.ep_no if ep else '' }}}}" placeholder="Episode Number (01, 02...)" class="w-full bg-black/40 p-4 rounded-2xl border border-blue-500/30 outline-none" required>
            
            {{% for i in [1, 2] %}}
            <div class="bg-gray-950 p-6 rounded-2xl border border-gray-800 space-y-4">
                <h3 class="text-blue-500 font-bold text-xs uppercase italic tracking-widest">Quality {{{{ i }}}} Details</h3>
                <input name="q{{{{i}}}}_n" value="{{{{ ep.links[i-1].quality if ep else '' }}}}" placeholder="720p / 1080p" class="w-full bg-black/30 p-3 rounded-xl border border-gray-800 outline-none">
                <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <input name="q{{{{i}}}}_s" value="{{{{ ep.links[i-1].stream if ep else '' }}}}" placeholder="Stream URL" class="bg-black/30 p-3 rounded-lg text-xs border border-gray-800 outline-none">
                    <input name="q{{{{i}}}}_d" value="{{{{ ep.links[i-1].download if ep else '' }}}}" placeholder="Down URL" class="bg-black/30 p-3 rounded-lg text-xs border border-gray-800 outline-none">
                    <input name="q{{{{i}}}}_t" value="{{{{ ep.links[i-1].telegram if ep else '' }}}}" placeholder="Tele URL" class="bg-black/30 p-3 rounded-lg text-xs border border-gray-800 outline-none">
                </div>
            </div>
            {{% endfor %}}
            <button class="w-full bg-blue-600 p-5 rounded-2xl font-black">SAVE EPISODE LINKS</button>
        </form>
    </body>
    </html>
    """
    return render_template_string(html, mid=mid, ep=ep, idx=idx)

@app.route('/admin/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        settings_col.update_one({"type": "config"}, {"$set": {"api": request.form['api']}}, upsert=True)
        settings_col.update_one({"type": "ads"}, {"$set": {"top": request.form['top'], "bottom": request.form['bottom'], "popup": request.form['popup']}}, upsert=True)
        return redirect('/admin')
    cfg = settings_col.find_one({"type": "config"}) or {}
    ads = settings_col.find_one({"type": "ads"}) or {}
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>{HEAD_CSS}</head>
    <body class="p-6">
        <form method="POST" class="max-w-4xl mx-auto glass p-10 rounded-[2.5rem] space-y-8">
            <h2 class="text-3xl font-black italic text-blue-500">SITE CONFIGURATION</h2>
            <div>
                <label class="text-xs font-bold text-gray-500 uppercase ml-2">Shortener API (use {{url}})</label>
                <input name="api" value="{{{{ cfg.api if cfg else '' }}}}" placeholder="https://api.com/st?api=KEY&url={{url}}" class="w-full bg-black/40 p-4 rounded-2xl border border-gray-800 mt-2 outline-none">
            </div>
            <div class="grid md:grid-cols-2 gap-8">
                <div class="col-span-2 md:col-span-1">
                    <label class="text-xs font-bold text-yellow-500 uppercase ml-2">Top Ad Code</label>
                    <textarea name="top" class="w-full bg-black/40 p-4 rounded-2xl h-32 border border-gray-800 mt-2 text-xs">{{{{ ads.top if ads else '' }}}}</textarea>
                </div>
                <div class="col-span-2 md:col-span-1">
                    <label class="text-xs font-bold text-yellow-500 uppercase ml-2">Bottom Ad Code</label>
                    <textarea name="bottom" class="w-full bg-black/40 p-4 rounded-2xl h-32 border border-gray-800 mt-2 text-xs">{{{{ ads.bottom if ads else '' }}}}</textarea>
                </div>
                <div class="col-span-2">
                    <label class="text-xs font-bold text-red-500 uppercase ml-2">Popup / JS Code</label>
                    <textarea name="popup" class="w-full bg-black/40 p-4 rounded-2xl h-32 border border-gray-800 mt-2 text-xs">{{{{ ads.popup if ads else '' }}}}</textarea>
                </div>
            </div>
            <button class="w-full bg-green-600 p-5 rounded-2xl font-black">SAVE SETTINGS</button>
        </form>
    </body>
    </html>
    """
    return render_template_string(html, cfg=cfg, ads=ads)

@app.route('/admin/delete/<id>')
def delete_movie(id):
    movies_col.delete_one({"_id": ObjectId(id)})
    return redirect('/admin')

@app.route('/admin/episode/delete/<mid>/<int:idx>')
def delete_episode(mid, idx):
    movie = movies_col.find_one({"_id": ObjectId(mid)})
    movie['episodes'].pop(idx)
    movies_col.update_one({"_id": ObjectId(mid)}, {"$set": {"episodes": movie['episodes']}})
    return redirect(f'/admin/episodes/{mid}')

if __name__ == '__main__':
    app.run(debug=True)
