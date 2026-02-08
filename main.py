from flask import Flask, render_template_string, request, redirect, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId
import requests

app = Flask(__name__)
app.secret_key = "movie_pro_key_final"

# --- MongoDB কানেকশন ---
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client.movie_database
movies_col = db.movies
settings_col = db.settings # বিজ্ঞাপন ও API সেটিংসের জন্য

# --- Helper: URL Shortener ---
def shorten_link(url):
    config = settings_col.find_one({"type": "config"})
    if config and config.get('api') and url and url.strip():
        api_url = config.get('api').replace("{url}", url)
        try:
            r = requests.get(api_url, timeout=5)
            return r.text if r.status_code == 200 else url
        except:
            return url
    return url

# --- UI Components & Styles ---
HEAD_CSS = """
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<script src="https://cdn.tailwindcss.com"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
<style>
    body { background-color: #0b0f19; color: white; font-family: 'Inter', sans-serif; }
    .glass { background: rgba(255, 255, 255, 0.03); backdrop-filter: blur(15px); border: 1px solid rgba(255,255,255,0.05); }
    .corner-tag { position: absolute; padding: 2px 8px; font-size: 10px; font-weight: bold; border-radius: 4px; z-index: 10; }
    .movie-card:hover img { transform: scale(1.1); transition: 0.5s; }
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
    if query:
        movies = list(movies_col.find({"name": {"$regex": query, "$options": "i"}}))
    else:
        movies = list(movies_col.find())
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>{HEAD_CSS}<title>MoviePro - Home</title></head>
    <body>
        <nav class="p-4 glass sticky top-0 z-50 flex justify-between items-center px-6">
            <a href="/" class="text-2xl font-black text-blue-500">MOVIE<span class="text-white">PRO</span></a>
            <form action="/" class="hidden md:flex bg-gray-900 border border-gray-700 rounded-lg overflow-hidden">
                <input name="q" placeholder="Search movies..." class="bg-transparent p-2 px-4 outline-none w-64 text-sm">
                <button class="px-4 text-blue-500"><i class="fa fa-search"></i></button>
            </form>
            <a href="/admin" class="bg-blue-600 px-5 py-2 rounded-full text-xs font-bold uppercase tracking-wider">Admin Panel</a>
        </nav>

        <div class="max-w-7xl mx-auto p-4 md:p-6">
            <div class="mb-6 text-center">{ads['top']}</div>
            
            <form action="/" class="md:hidden flex bg-gray-900 border border-gray-700 rounded-xl mb-6">
                <input name="q" placeholder="Search..." class="bg-transparent p-3 flex-grow outline-none text-sm">
                <button class="px-6 bg-blue-600 rounded-r-xl"><i class="fa fa-search"></i></button>
            </form>

            <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4 md:gap-8">
                {{% for movie in movies %}}
                <a href="/movie/{{{{ movie._id }}}}" class="group block relative">
                    <div class="relative overflow-hidden rounded-2xl shadow-2xl aspect-[2/3] movie-card">
                        <span class="corner-tag top-2 left-2 bg-blue-600 shadow-lg">{{{{ movie.tag1 }}}}</span>
                        <span class="corner-tag top-2 right-2 bg-red-600 shadow-lg">{{{{ movie.tag2 }}}}</span>
                        <span class="corner-tag bottom-2 left-2 bg-yellow-500 text-black shadow-lg">{{{{ movie.tag3 }}}}</span>
                        <span class="corner-tag bottom-2 right-2 bg-green-600 shadow-lg">{{{{ movie.tag4 }}}}</span>
                        <img src="{{{{ movie.poster }}}}" class="w-full h-full object-cover">
                        <div class="absolute inset-0 bg-gradient-to-t from-black via-transparent to-transparent opacity-90"></div>
                        <div class="absolute bottom-3 left-3 right-3">
                             <h3 class="font-bold text-sm truncate">{{{{ movie.name }}}}</h3>
                             <p class="text-[10px] text-gray-400 mt-1 uppercase">{{{{ movie.year }}}} • {{{{ movie.lang }}}}</p>
                        </div>
                    </div>
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
    <body>
        <div class="max-w-5xl mx-auto p-4 py-10">
            <div class="md:flex gap-10 glass p-6 md:p-10 rounded-[2rem] border border-gray-800">
                <img src="{{{{ movie.poster }}}}" class="w-full md:w-80 rounded-2xl shadow-2xl mb-8 md:mb-0 border border-gray-700">
                <div class="flex-grow">
                    <h1 class="text-4xl md:text-6xl font-black leading-tight">{{{{ movie.name }}}}</h1>
                    <div class="flex flex-wrap gap-4 my-6">
                        <span class="bg-blue-600/20 text-blue-400 border border-blue-500/30 px-4 py-1 rounded-full text-sm font-bold">{{{{ movie.year }}}}</span>
                        <span class="bg-gray-800 px-4 py-1 rounded-full text-sm font-bold">{{{{ movie.lang }}}}</span>
                    </div>
                    <div class="bg-white/5 p-5 rounded-2xl border border-white/5">
                        <h2 class="text-blue-500 font-bold text-xs uppercase tracking-widest mb-2 italic">About Storyline</h2>
                        <p class="text-gray-400 text-sm md:text-base leading-relaxed">{{{{ movie.story }}}}</p>
                    </div>
                </div>
            </div>

            <div class="mt-12 text-center">{ads['top']}</div>

            <div class="mt-16">
                <h2 class="text-3xl font-bold mb-10 flex items-center gap-4 italic">
                    <span class="w-10 h-[2px] bg-blue-600"></span> Watch & Download
                </h2>
                <div class="space-y-8">
                    {{% for ep in movie.episodes %}}
                    <div class="glass p-6 md:p-8 rounded-3xl border-l-8 border-blue-600 relative overflow-hidden">
                        <div class="absolute top-0 right-0 p-10 bg-blue-600/5 rounded-full -mr-10 -mt-10"></div>
                        <h3 class="font-black text-xl mb-6 text-blue-400 italic">Episode: {{{{ ep.ep_no }}}}</h3>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {{% for link in ep.links %}}
                            <div class="bg-black/40 p-5 rounded-2xl border border-gray-800">
                                <span class="text-[10px] font-black text-gray-500 uppercase tracking-widest block mb-4">Quality: {{{{ link.quality }}}}</span>
                                <div class="flex flex-wrap gap-3">
                                    <a href="{{{{ link.stream }}}}" target="_blank" class="flex-grow bg-blue-600 hover:bg-blue-700 text-center py-3 rounded-xl text-xs font-bold transition"><i class="fa fa-play mr-2"></i> STREAM</a>
                                    <a href="{{{{ link.download }}}}" target="_blank" class="flex-grow bg-green-600 hover:bg-green-700 text-center py-3 rounded-xl text-xs font-bold transition"><i class="fa fa-download mr-2"></i> DOWNLOAD</a>
                                    <a href="{{{{ link.telegram }}}}" target="_blank" class="w-full md:w-auto bg-sky-500 hover:bg-sky-600 px-6 py-3 rounded-xl text-xs font-bold transition text-center"><i class="fab fa-telegram mr-2"></i> TELEGRAM</a>
                                </div>
                            </div>
                            {{% endfor %}}
                        </div>
                    </div>
                    {{% endfor %}}
                </div>
            </div>
            <div class="mt-16 text-center">{ads['bottom']}</div>
        </div>
        {ads['popup']}
    </body>
    </html>
    """
    return render_template_string(html, movie=movie)

# --- ADMIN PANEL ---

@app.route('/admin')
def admin_dashboard():
    q = request.args.get('q')
    movies = list(movies_col.find({"name": {"$regex": q, "$options": "i"}})) if q else list(movies_col.find())
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>{HEAD_CSS}<title>Admin Panel</title></head>
    <body class="bg-gray-950">
        <div class="flex min-h-screen">
            <aside class="w-64 glass hidden lg:block border-r border-gray-800 p-8">
                <h1 class="text-xl font-black text-blue-500 mb-10">ADMIN <span class="text-white">PRO</span></h1>
                <nav class="space-y-4">
                    <a href="/admin" class="block p-4 bg-blue-600 rounded-2xl font-bold shadow-lg shadow-blue-600/20 text-sm">Dashboard</a>
                    <a href="/admin/add" class="block p-4 hover:bg-gray-900 rounded-2xl font-bold text-gray-400 text-sm transition">Add Movie</a>
                    <a href="/admin/settings" class="block p-4 hover:bg-gray-900 rounded-2xl font-bold text-gray-400 text-sm transition">Settings & Ads</a>
                    <a href="/" class="block p-4 text-red-500 font-bold text-sm italic">Exit Admin</a>
                </nav>
            </aside>
            <main class="flex-grow p-4 md:p-10">
                <div class="flex flex-col md:flex-row justify-between items-center mb-10 gap-6">
                    <form action="/admin" class="flex bg-gray-900 border border-gray-800 rounded-xl w-full md:w-96 shadow-xl">
                        <input name="q" placeholder="Search by title..." class="bg-transparent p-3 px-5 flex-grow outline-none text-sm">
                        <button class="px-6 text-blue-500"><i class="fa fa-search"></i></button>
                    </form>
                    <a href="/admin/add" class="w-full md:w-auto bg-green-600 hover:bg-green-700 px-8 py-3 rounded-xl font-bold text-sm shadow-xl transition">+ New Movie</a>
                </div>
                <div class="grid gap-4">
                    {{% for movie in movies %}}
                    <div class="glass p-4 rounded-2xl flex items-center justify-between border border-white/5 hover:border-blue-500/30 transition">
                        <div class="flex items-center gap-5">
                            <img src="{{{{ movie.poster }}}}" class="w-14 h-20 rounded-lg object-cover shadow-lg">
                            <div>
                                <h3 class="font-bold text-base">{{{{ movie.name }}}}</h3>
                                <p class="text-[10px] text-gray-500 font-bold uppercase tracking-tighter">{{{{ movie.year }}}} • {{{{ movie.lang }}}}</p>
                            </div>
                        </div>
                        <div class="flex gap-2">
                            <a href="/admin/edit/{{{{ movie._id }}}}" class="p-3 bg-yellow-500/10 text-yellow-500 rounded-xl hover:bg-yellow-500 hover:text-white transition"><i class="fa fa-edit"></i></a>
                            <a href="/admin/delete/{{{{ movie._id }}}}" class="p-3 bg-red-500/10 text-red-500 rounded-xl hover:bg-red-500 hover:text-white transition" onclick="return confirm('Delete?')"><i class="fa fa-trash"></i></a>
                        </div>
                    </div>
                    {{% endfor %}}
                </div>
            </main>
        </div>
    </body>
    </html>
    """
    return render_template_string(html, movies=movies)

@app.route('/admin/add', methods=['GET', 'POST'])
@app.route('/admin/edit/<id>', methods=['GET', 'POST'])
def manage_movie(id=None):
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
    <body class="p-4 md:p-10">
        <div class="max-w-4xl mx-auto glass p-8 md:p-12 rounded-[2.5rem] border border-white/5">
            <h2 class="text-3xl font-black mb-10 italic">{'Edit Movie Details' if id else 'Upload New Movie'}</h2>
            <form method="POST" class="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div class="md:col-span-2">
                    <label class="text-[10px] font-black text-gray-500 uppercase ml-2">Movie Name</label>
                    <input name="name" value="{{{{ movie.name if movie else '' }}}}" class="w-full bg-black/40 p-4 rounded-2xl mt-2 border border-gray-800 outline-none focus:border-blue-500" required>
                </div>
                <div class="md:col-span-2">
                    <label class="text-[10px] font-black text-gray-500 uppercase ml-2">Poster URL</label>
                    <input name="poster" value="{{{{ movie.poster if movie else '' }}}}" class="w-full bg-black/40 p-4 rounded-2xl mt-2 border border-gray-800 outline-none focus:border-blue-500">
                </div>
                <div><input name="year" value="{{{{ movie.year if movie else '' }}}}" placeholder="Year" class="w-full bg-black/40 p-4 rounded-2xl border border-gray-800 outline-none"></div>
                <div><input name="lang" value="{{{{ movie.lang if movie else '' }}}}" placeholder="Language" class="w-full bg-black/40 p-4 rounded-2xl border border-gray-800 outline-none"></div>
                <div class="md:col-span-2 grid grid-cols-4 gap-4">
                    <input name="tag1" value="{{{{ movie.tag1 if movie else '' }}}}" placeholder="Tag 1" class="bg-black/40 p-3 rounded-xl border border-gray-800 text-xs">
                    <input name="tag2" value="{{{{ movie.tag2 if movie else '' }}}}" placeholder="Tag 2" class="bg-black/40 p-3 rounded-xl border border-gray-800 text-xs">
                    <input name="tag3" value="{{{{ movie.tag3 if movie else '' }}}}" placeholder="Tag 3" class="bg-black/40 p-3 rounded-xl border border-gray-800 text-xs">
                    <input name="tag4" value="{{{{ movie.tag4 if movie else '' }}}}" placeholder="Tag 4" class="bg-black/40 p-3 rounded-xl border border-gray-800 text-xs">
                </div>
                <div class="md:col-span-2">
                    <textarea name="story" placeholder="Write Storyline..." class="w-full bg-black/40 p-5 rounded-2xl h-40 border border-gray-800 outline-none">{{{{ movie.story if movie else '' }}}}</textarea>
                </div>
                <div class="md:col-span-2 flex flex-col md:flex-row gap-4">
                    <button class="flex-grow bg-blue-600 py-5 rounded-2xl font-black shadow-2xl hover:bg-blue-700 transition">SAVE MOVIE</button>
                    {{% if id %}}
                    <a href="/admin/episodes/{{{{ id }}}}" class="bg-gray-800 px-10 py-5 rounded-2xl font-bold text-blue-400 text-center">MANAGE EPISODES</a>
                    {{% endif %}}
                </div>
            </form>
        </div>
    </body>
    </html>
    """
    return render_template_string(html, movie=movie)

@app.route('/admin/episodes/<mid>')
def episode_list(mid):
    movie = movies_col.find_one({"_id": ObjectId(mid)})
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>{HEAD_CSS}</head>
    <body class="p-6">
        <div class="max-w-4xl mx-auto">
            <div class="flex justify-between items-center mb-10">
                <h2 class="text-2xl font-black italic">Episodes: {{{{ movie.name }}}}</h2>
                <a href="/admin/episode/add/{{{{ mid }}}}" class="bg-blue-600 px-6 py-2 rounded-xl font-bold">+ Add Episode</a>
            </div>
            <div class="grid gap-4">
                {{% for ep in movie.episodes %}}
                <div class="glass p-6 rounded-2xl flex justify-between items-center border border-white/5">
                    <span class="font-bold italic">Episode {{{{ ep.ep_no }}}}</span>
                    <div class="flex gap-3">
                        <a href="/admin/episode/edit/{{{{ mid }}}}/{{{{ loop.index0 }}}}" class="p-2 text-yellow-500"><i class="fa fa-edit"></i></a>
                        <a href="/admin/episode/delete/{{{{ mid }}}}/{{{{ loop.index0 }}}}" class="p-2 text-red-500" onclick="return confirm('Delete?')"><i class="fa fa-trash"></i></a>
                    </div>
                </div>
                {{% endfor %}}
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html, movie=movie, mid=mid)

@app.route('/admin/episode/save', methods=['POST'])
@app.route('/admin/episode/add/<mid>')
@app.route('/admin/episode/edit/<mid>/<int:idx>')
def manage_episode(mid, idx=None):
    movie = movies_col.find_one({"_id": ObjectId(mid)})
    ep = movie['episodes'][idx] if idx is not None else None
    if request.method == 'POST':
        mid = request.form['mid']
        index = request.form.get('idx')
        links = []
        for i in [1, 2]:
            links.append({
                "quality": request.form.get(f'q{i}_n'),
                "stream": shorten_link(request.form.get(f'q{i}_s')),
                "download": shorten_link(request.form.get(f'q{i}_d')),
                "telegram": shorten_link(request.form.get(f'q{i}_t'))
            })
        new_ep = {"ep_no": request.form['ep_no'], "links": links}
        if index:
            movie['episodes'][int(index)] = new_ep
            movies_col.update_one({"_id": ObjectId(mid)}, {"$set": {"episodes": movie['episodes']}})
        else:
            movies_col.update_one({"_id": ObjectId(mid)}, {"$push": {"episodes": new_ep}})
        return redirect(f'/admin/episodes/{mid}')

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>{HEAD_CSS}</head>
    <body class="p-6">
        <form method="POST" action="/admin/episode/save" class="max-w-2xl mx-auto glass p-8 md:p-12 rounded-[2.5rem]">
            <input type="hidden" name="mid" value="{{{{ mid }}}}">
            <input type="hidden" name="idx" value="{{{{ idx if idx is not None else '' }}}}">
            <h2 class="text-2xl font-black mb-10 italic">Episode Settings</h2>
            <input name="ep_no" value="{{{{ ep.ep_no if ep else '' }}}}" placeholder="Episode Number (e.g. 01)" class="w-full bg-black/40 p-5 rounded-2xl mb-8 border border-blue-600/30 outline-none" required>
            
            {{% for i in [1, 2] %}}
            <div class="bg-gray-900/50 p-6 rounded-2xl mb-6 border border-gray-800">
                <h3 class="text-blue-500 font-bold mb-4 uppercase text-[10px] tracking-widest italic">Quality {{{{ i }}}} Details</h3>
                <input name="q{{{{i}}}}_n" value="{{{{ ep.links[i-1].quality if ep else '' }}}}" placeholder="720p / 1080p" class="w-full bg-black/40 p-3 rounded-xl mb-4 border border-gray-800 outline-none">
                <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <input name="q{{{{i}}}}_s" value="{{{{ ep.links[i-1].stream if ep else '' }}}}" placeholder="Stream URL" class="bg-black/40 p-3 rounded-lg text-xs border border-gray-800">
                    <input name="q{{{{i}}}}_d" value="{{{{ ep.links[i-1].download if ep else '' }}}}" placeholder="Download URL" class="bg-black/40 p-3 rounded-lg text-xs border border-gray-800">
                    <input name="q{{{{i}}}}_t" value="{{{{ ep.links[i-1].telegram if ep else '' }}}}" placeholder="Telegram URL" class="bg-black/40 p-3 rounded-lg text-xs border border-gray-800">
                </div>
            </div>
            {{% endfor %}}
            <button class="w-full bg-blue-600 py-5 rounded-2xl font-black">SAVE EPISODE</button>
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
            <h2 class="text-3xl font-black italic">Advanced Settings</h2>
            <div>
                <label class="block text-xs font-black text-blue-500 mb-2 uppercase">Shortener API (Use {{url}})</label>
                <input name="api" value="{{{{ cfg.api if cfg else '' }}}}" placeholder="https://api.com/st?api=KEY&url={{url}}" class="w-full bg-black/40 p-4 rounded-xl border border-gray-800 outline-none">
            </div>
            <div class="grid md:grid-cols-2 gap-8">
                <div class="col-span-2 md:col-span-1">
                    <label class="block text-xs font-black text-yellow-500 mb-2 uppercase">Top Ad Code</label>
                    <textarea name="top" class="w-full bg-black/40 p-4 rounded-xl h-32 border border-gray-800 text-xs">{{{{ ads.top if ads else '' }}}}</textarea>
                </div>
                <div class="col-span-2 md:col-span-1">
                    <label class="block text-xs font-black text-yellow-500 mb-2 uppercase">Bottom Ad Code</label>
                    <textarea name="bottom" class="w-full bg-black/40 p-4 rounded-xl h-32 border border-gray-800 text-xs">{{{{ ads.bottom if ads else '' }}}}</textarea>
                </div>
                <div class="col-span-2">
                    <label class="block text-xs font-black text-red-500 mb-2 uppercase">Popup / JS Code</label>
                    <textarea name="popup" class="w-full bg-black/40 p-4 rounded-xl h-32 border border-gray-800 text-xs">{{{{ ads.popup if ads else '' }}}}</textarea>
                </div>
            </div>
            <button class="w-full bg-green-600 py-5 rounded-2xl font-black">SAVE SETTINGS</button>
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
