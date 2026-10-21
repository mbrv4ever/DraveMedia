#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DraveMedia - alles-in-een mediaspeler (Dravenlock).
- Speelt media (systeem-/Qt-backend, met optionele VLC-backend voor alle formaten)
- Opent afbeeldingen (alle door Qt/Pillow ondersteunde formaten)
- Ingebouwde mediaserver (streamt over het lokale netwerk, met Range-ondersteuning)
- Genereert een HTML5-mediaspeler voor op websites
Nederlands met OS-taaldetectie. Donker + zilver, toegankelijk.
"""
import sys
import os
import json
import socket
import threading
import urllib.parse
import html as _html
import time
import shutil
import hashlib
import base64
import tempfile
import subprocess
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

APP_NAME = "DraveMedia"
APP_VERSION = "0.27"
CONTACT = "service@dravenlock.nl"
DONATE_URL = "https://paypal.me/roger076"
VERSION_URL = "https://dravenlock.nl/downloads/DraveMedia/version.txt"

# ----------------------------------------------------------------------------- paden (script + frozen .exe)
def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


APP_DIR = app_dir()
CONFIG_PATH = os.path.join(APP_DIR, "dravemedia_config.json")


def resource_path(rel):
    base = getattr(sys, "_MEIPASS", APP_DIR)
    return os.path.join(base, rel)


# ----------------------------------------------------------------------------- config
DEFAULT_CONFIG = {
    "lang": "",                 # "" = automatisch (OS), anders "nl"/"en"
    "backend": "qt",            # "qt" of "vlc"
    "volume": 80,
    "server_dir": "",
    "server_port": 8000,
    "last_dir": "",
    "pwa_media_base": "",       # waar de media staat voor de PWA-export (leeg = naast de speler)
    "pwa_live_php": False,      # live medialijst via media.php i.p.v. vaste media.json
}


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            cfg.update(json.load(fh))
    except Exception:
        pass
    return cfg


def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, indent=2)
    except Exception:
        pass


# ----------------------------------------------------------------------------- taal
def system_lang():
    """Detecteer de OS-taal robuust (Windows + overig). Geeft 'nl' of 'en'."""
    val = ""
    try:
        if sys.platform.startswith("win"):
            import ctypes
            buf = ctypes.create_unicode_buffer(85)
            ctypes.windll.kernel32.GetUserDefaultLocaleName(buf, 85)
            val = buf.value or ""
        if not val:
            import locale
            val = (locale.getlocale()[0] or "") + " " + (os.environ.get("LANG", ""))
    except Exception:
        pass
    v = val.lower()
    if any(k in v for k in ("nl", "dutch", "nederland", "netherlands", "flemish", "vlaams", "belg")):
        return "nl"
    return "en"


# Nederlands is de basistaal; Engelse vertalingen via deze map (sleutel = NL-tekst).
TRANSLATIONS = {
    "en": {
        "Speler": "Player", "Afbeeldingen": "Images", "Server": "Server", "HTML5": "HTML5",
        "Openen…": "Open…", "Map openen…": "Open folder…", "Afspelen": "Play", "Pauze": "Pause",
        "Stop": "Stop", "Vorige": "Previous", "Volgende": "Next", "Volledig scherm": "Fullscreen",
        "Geluid": "Volume", "Dempen": "Mute", "Afspeellijst": "Playlist", "Wissen": "Clear",
        "Backend": "Backend", "Systeem (Qt)": "System (Qt)", "VLC (alle formaten)": "VLC (all formats)",
        "Instellingen": "Settings", "Taal": "Language", "Automatisch (systeem)": "Automatic (system)",
        "Nederlands": "Dutch", "Engels": "English", "Opslaan": "Save", "Annuleren": "Cancel", "OK": "OK",
        "Map kiezen…": "Choose folder…", "Starten": "Start", "Stoppen": "Stop",
        "Server-map:": "Server folder:", "Poort:": "Port:", "Open in browser": "Open in browser",
        "Kopieer link": "Copy link", "De server draait op:": "The server is running at:",
        "Server gestopt.": "Server stopped.", "Geen map gekozen.": "No folder chosen.",
        "Mediabestand of URL:": "Media file or URL:", "Bladeren…": "Browse…",
        "Titel:": "Title:", "Poster (optioneel):": "Poster (optional):",
        "Automatisch afspelen": "Autoplay", "Herhalen": "Loop", "Bediening tonen": "Show controls",
        "Genereer": "Generate", "HTML opslaan…": "Save HTML…",
        "Ook het mediabestand ernaast kopiëren": "Also copy the media file next to it",
        "Voorbeeld (broncode):": "Preview (source):", "Opgeslagen.": "Saved.",
        "Server-URL (optioneel):": "Server URL (optional):", "van server": "from server",
        "Start eerst de server op het Server-tabblad.": "Start the server on the Server tab first.",
        "Vul eerst een mediabestand of URL in.": "Enter a media file or URL first.",
        "Er ging iets mis bij het genereren:": "Something went wrong while generating:",
        "Start eerst de server.": "Start the server first.",
        "Bestand op server:": "File on server:",
        "— kies een bestand op de server —": "— choose a file on the server —",
        "Hele server als doorlopende speler (alleen server-URL nodig)": "Whole server as continuous player (only server URL needed)",
        "Vul de server-URL in (of start de server en klik 'van server').":
        "Enter the server URL (or start the server and click 'from server').",
        "Server-URL:": "Server URL:",
        "Bekijk in browser": "View in browser", "Kon de browser niet openen.": "Could not open the browser.",
        "Live voorbeeld:": "Live preview:",
        "Code kopiëren": "Copy code",
        "Snelgids": "Quick guide", "Sluiten": "Close",
        "♥ Donatie": "♥ Donate", "Steun Dravenlock": "Support Dravenlock", "Donatie": "Donation",
        "Steun Dravenlock — bedankt!": "Support Dravenlock — thank you!",
        "Media-URL (waar de media staat):": "Media URL (where the media lives):",
        "leeg = media staat naast de speler   ·   anders bijv. https://dravenlock.nl/media/": "empty = media sits next to the player   ·   otherwise e.g. https://dravenlock.nl/media/",
        "Maakt alleen de PWA-bestanden (speler + manifest + service worker + icoon). De media blijft op de server staan en wordt gestreamd. Upload de map naar je beveiligde site, bijv. onder /mediaspeler/.": "Creates only the PWA files (player + manifest + service worker + icon). The media stays on the server and is streamed. Upload the folder to your secure site, e.g. under /mediaspeler/.",
        "Klaar! De PWA-bestanden staan hier:": "Done! The PWA files are here:",
        "Upload alleen deze map naar je beveiligde site (bijv. /mediaspeler/). De media zelf blijft op de server staan.": "Upload only this folder to your secure site (e.g. /mediaspeler/). The media itself stays on the server.",
        "De media wordt gestreamd vanaf: ": "Media is streamed from: ",
        "dezelfde map als de speler": "the same folder as the player",
        "Live lijst via PHP (server met PHP, bijv. XAMPP) — werkt altijd bij, geen her-export nodig": "Live list via PHP (server with PHP, e.g. XAMPP) — always up to date, no re-export",
        "Live lijst: media.php scant je map automatisch — bij nieuwe media gewoon vernieuwen, geen her-export nodig.": "Live list: media.php scans your folder automatically — just refresh for new media, no re-export.",
        "Website (PWA) exporteren…": "Export website (PWA)…",
        "Maakt een complete map (speler + icoon + snelgids + jouw media) die je op je beveiligde website kunt zetten, bijv. onder /mediaspeler/.": "Creates a complete folder (player + icon + quick guide + your media) you can put on your secure website, e.g. under /mediaspeler/.",
        "Kies eerst een Server-map (de map met je media).": "Choose a Server folder first (the folder with your media).",
        "Kies waar de website-map komt te staan": "Choose where the website folder goes",
        "In deze map staan geen media-bestanden.": "There are no media files in this folder.",
        "Media kopiëren…": "Copying media…", "Annuleren": "Cancel",
        "Klaar! De website-map staat hier:": "Done! The website folder is here:",
        "Upload deze hele map naar je beveiligde site (bijv. /mediaspeler/) en open de snelgids.html voor uitleg.": "Upload this whole folder to your secure site (e.g. /mediaspeler/) and open snelgids.html for help.",
        "Map openen": "Open folder", "Exporteren": "Export",
        "De code is gekopieerd naar het klembord.": "The code has been copied to the clipboard.",
        "Ingebouwde browser niet beschikbaar.\nDraai herstel.bat om hem te installeren,\nof gebruik 'Bekijk in browser'.": "Built-in browser not available.\nRun herstel.bat to install it,\nor use 'View in browser'.",
        "Hele server (doorlopende speler)": "Whole server (continuous player)",
        "Eén bestand of URL": "Single file or URL",
        "De speler speelt alle media van de server automatisch achter elkaar af (Muziek/Video/Afbeeldingen). Alleen de server-URL hierboven is nodig.": "The player plays all media from the server automatically, one after another (Music/Video/Images). Only the server URL above is needed.",
        "Kon de browser niet openen. De link is gekopieerd; plak 'm zelf in de browser:": "Could not open the browser. The link was copied; paste it into your browser:",
        "Zoom +": "Zoom +", "Zoom -": "Zoom -", "Passend": "Fit", "Draaien": "Rotate",
        "Niets geladen": "Nothing loaded", "Over": "About", "Doneren": "Donate", "Contact": "Contact",
        "Sleep media hierheen of klik op Openen.": "Drop media here or click Open.",
        "Kon dit bestand niet laden.": "Could not load this file.",
        "VLC niet gevonden": "VLC not found",
        "De VLC-backend vereist dat VLC is geïnstalleerd (of python-vlc). "
        "Ik val nu terug op de systeemspeler (Qt).":
            "The VLC backend requires VLC to be installed (or python-vlc). "
            "Falling back to the system player (Qt).",
    }
}


def t(s, lang):
    if lang == "nl":
        return s
    return TRANSLATIONS.get(lang, {}).get(s, s)


# ----------------------------------------------------------------------------- netwerk
def local_ips():
    out = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        out.add(s.getsockname()[0]); s.close()
    except Exception:
        pass
    try:
        out.add(socket.gethostbyname(socket.gethostname()))
    except Exception:
        pass
    return sorted(i for i in out if i and not i.startswith("127."))


# ----------------------------------------------------------------------------- mediatypes
VIDEO_EXT = {".mp4", ".m4v", ".mkv", ".avi", ".mov", ".wmv", ".webm", ".flv", ".mpg", ".mpeg", ".ts", ".ogv", ".3gp"}
AUDIO_EXT = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".oga", ".m4a", ".wma", ".opus", ".aiff", ".alac"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tif", ".tiff", ".ico", ".svg", ".heic", ".jfif"}
MEDIA_EXT = VIDEO_EXT | AUDIO_EXT


def kind_of(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in VIDEO_EXT:
        return "video"
    if ext in AUDIO_EXT:
        return "audio"
    if ext in IMAGE_EXT:
        return "image"
    return "other"


MIME = {
    ".mp4": "video/mp4", ".m4v": "video/mp4", ".webm": "video/webm", ".ogv": "video/ogg",
    ".mkv": "video/x-matroska", ".mov": "video/quicktime", ".avi": "video/x-msvideo",
    ".mp3": "audio/mpeg", ".wav": "audio/wav", ".flac": "audio/flac", ".aac": "audio/aac",
    ".ogg": "audio/ogg", ".oga": "audio/ogg", ".opus": "audio/ogg", ".m4a": "audio/mp4",
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif",
    ".webp": "image/webp", ".svg": "image/svg+xml", ".bmp": "image/bmp", ".tif": "image/tiff",
    ".tiff": "image/tiff", ".ico": "image/x-icon", ".html": "text/html; charset=utf-8",
}


def guess_mime(path):
    return MIME.get(os.path.splitext(path)[1].lower(), "application/octet-stream")


# ----------------------------------------------------------------------------- FFmpeg-motor (direct play / remux / transcode naar HLS)
# Codecs die browsers rechtstreeks aankunnen -> dan hoeft er niets te gebeuren.
WEB_VCODECS = {"h264", "vp8", "vp9", "av1"}
WEB_ACODECS = {"aac", "mp3", "opus", "vorbis", ""}
WEB_CONTAINER_EXT = {".mp4", ".m4v", ".webm"}   # .mkv/.mov/.avi enz. spelen browsers NIET af
# Bron voor automatische download op de eerste start (Windows). Eén stabiele build:
FFMPEG_WIN_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
_FF_CACHE = {}
_DECIDE_CACHE = {}


def _find_tool(name):
    """Zoek ffmpeg/ffprobe: eerst naast de exe (Roger levert ze mee), dan in PATH."""
    if name in _FF_CACHE:
        return _FF_CACHE[name]
    exe = name + (".exe" if os.name == "nt" else "")
    cands = []
    base = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) \
        else os.path.dirname(os.path.abspath(__file__))
    cands += [os.path.join(base, exe), os.path.join(base, "ffmpeg", exe),
              os.path.join(base, "bin", exe)]
    found = None
    for c in cands:
        if os.path.isfile(c):
            found = c; break
    if not found:
        found = shutil.which(name)
    _FF_CACHE[name] = found
    return found


def ffmpeg_path():
    return _find_tool("ffmpeg")


def ffprobe_path():
    return _find_tool("ffprobe")


def probe_codecs(full):
    """Geef (container, vcodec, acodec) terug via ffprobe, of None als het niet lukt."""
    fp = ffprobe_path()
    if not fp:
        return None
    try:
        out = subprocess.run(
            [fp, "-v", "error", "-show_entries",
             "format=format_name:stream=codec_type,codec_name",
             "-of", "json", full],
            capture_output=True, text=True, timeout=20)
        info = json.loads(out.stdout or "{}")
        container = (info.get("format", {}) or {}).get("format_name", "")
        vcodec = acodec = ""
        for s in info.get("streams", []):
            if s.get("codec_type") == "video" and not vcodec:
                vcodec = s.get("codec_name", "")
            elif s.get("codec_type") == "audio" and not acodec:
                acodec = s.get("codec_name", "")
        return (container, vcodec, acodec)
    except Exception:
        return None


def decide_mode(full):
    """direct (rechtstreeks serveren) / remux (alleen herverpakken) / transcode (omzetten).
    Cachet op pad+wijzigingstijd. Zonder ffmpeg -> altijd 'direct' (best effort)."""
    try:
        key = (full, os.path.getmtime(full))
    except OSError:
        key = (full, 0)
    if key in _DECIDE_CACHE:
        return _DECIDE_CACHE[key]
    mode = "direct"
    if ffmpeg_path():
        info = probe_codecs(full)
        if info:
            container, v, a = info
            web_container = os.path.splitext(full)[1].lower() in WEB_CONTAINER_EXT
            if v in WEB_VCODECS and a in WEB_ACODECS:
                mode = "direct" if web_container else "remux"
            else:
                mode = "transcode"
    _DECIDE_CACHE[key] = mode
    return mode


def ffmpeg_target_dir():
    """Map waar we FFmpeg neerzetten als we 'm downloaden (naast de app)."""
    return os.path.join(app_dir(), "ffmpeg")


def _extract_ffmpeg(zip_path, dest_dir):
    """Pak ffmpeg.exe en ffprobe.exe (of zonder .exe) uit een gedownloade build."""
    import zipfile
    os.makedirs(dest_dir, exist_ok=True)
    wanted = ("ffmpeg.exe", "ffprobe.exe", "ffmpeg", "ffprobe")
    got = 0
    with zipfile.ZipFile(zip_path) as z:
        for n in z.namelist():
            if n.endswith("/"):
                continue
            base = os.path.basename(n).lower()
            if base in wanted:
                out = os.path.join(dest_dir, os.path.basename(n))
                with z.open(n) as src, open(out, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                try:
                    os.chmod(out, 0o755)
                except OSError:
                    pass
                got += 1
    _FF_CACHE.clear()
    return got >= 1


def download_ffmpeg(dest_dir=None, progress=None, url=FFMPEG_WIN_URL, cancel=None):
    """Download een FFmpeg-build en pak ffmpeg/ffprobe uit in dest_dir.
    progress(done_bytes, total_bytes) en cancel() optioneel. Geeft True bij succes."""
    import urllib.request
    dest_dir = dest_dir or ffmpeg_target_dir()
    os.makedirs(dest_dir, exist_ok=True)
    tmpzip = os.path.join(tempfile.gettempdir(), "dravemedia_ffmpeg.zip")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "DraveMedia"})
        with urllib.request.urlopen(req, timeout=60) as r, open(tmpzip, "wb") as f:
            total = int(r.headers.get("Content-Length", 0) or 0)
            done = 0
            while True:
                if cancel and cancel():
                    raise RuntimeError("geannuleerd")
                chunk = r.read(262144)
                if not chunk:
                    break
                f.write(chunk); done += len(chunk)
                if progress:
                    progress(done, total)
        ok = _extract_ffmpeg(tmpzip, dest_dir)
    except Exception:
        ok = False
    finally:
        try:
            os.remove(tmpzip)
        except OSError:
            pass
    return ok


class HlsManager:
    """Start FFmpeg per gevraagd bestand en serveert de HLS-segmenten. Ruimt op."""
    def __init__(self):
        self.sessions = {}          # token -> {dir, proc, full, mode, last}
        self.lock = threading.Lock()
        self.root = tempfile.mkdtemp(prefix="dravemedia_hls_")

    def register(self, full, mode):
        token = hashlib.md5(("%s|%s" % (full, mode)).encode("utf-8")).hexdigest()[:16]
        with self.lock:
            s = self.sessions.get(token)
            if not s:
                self.sessions[token] = {"dir": os.path.join(self.root, token),
                                        "proc": None, "full": full, "mode": mode,
                                        "last": time.time()}
        return token

    def _start(self, token):
        s = self.sessions[token]
        d = s["dir"]; os.makedirs(d, exist_ok=True)
        m3u8 = os.path.join(d, "index.m3u8")
        segpat = os.path.join(d, "seg_%03d.ts")
        if s["mode"] == "remux":
            codec_args = ["-c", "copy"]
        else:
            codec_args = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                          "-c:a", "aac", "-ac", "2"]
        cmd = ([ffmpeg_path(), "-nostdin", "-loglevel", "error", "-y", "-i", s["full"],
                "-map", "0:v:0?", "-map", "0:a:0?"] + codec_args +
               ["-f", "hls", "-hls_time", "6", "-hls_playlist_type", "event",
                "-hls_flags", "independent_segments",
                "-hls_segment_filename", segpat, m3u8])
        try:
            s["proc"] = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                                         stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
        except Exception:
            s["proc"] = None

    def ensure(self, token):
        with self.lock:
            s = self.sessions.get(token)
            if not s:
                return None
            s["last"] = time.time()
            if s["proc"] is None or s["proc"].poll() is not None and not os.path.exists(
                    os.path.join(s["dir"], "index.m3u8")):
                if s["proc"] is None:
                    self._start(token)
            return s

    def path_for(self, token, fname):
        with self.lock:
            s = self.sessions.get(token)
            if not s:
                return None
            s["last"] = time.time()
            d = s["dir"]
        cand = os.path.normpath(os.path.join(d, os.path.basename(fname)))
        if cand.startswith(d) and os.path.isfile(cand):
            return cand
        return None

    def reap(self, idle=120):
        now = time.time()
        with self.lock:
            for token in list(self.sessions):
                s = self.sessions[token]
                if now - s["last"] > idle:
                    self._kill(s); self.sessions.pop(token, None)

    def _kill(self, s):
        try:
            if s.get("proc"):
                s["proc"].terminate()
        except Exception:
            pass
        try:
            shutil.rmtree(s["dir"], ignore_errors=True)
        except Exception:
            pass

    def shutdown(self):
        with self.lock:
            for s in self.sessions.values():
                self._kill(s)
            self.sessions.clear()
        shutil.rmtree(self.root, ignore_errors=True)


# ----------------------------------------------------------------------------- mediaserver (Range-ondersteuning)
class _Handler(BaseHTTPRequestHandler):
    server_version = "DraveMedia/" + APP_VERSION

    def log_message(self, *a):
        pass  # stil

    def _safe_path(self):
        root = self.server.base_dir
        p = urllib.parse.unquote(self.path.split("?", 1)[0])
        p = p.lstrip("/")
        full = os.path.normpath(os.path.join(root, p))
        if not (full == root or full.startswith(root + os.sep)):
            return None
        return full

    def _auth_ok(self):
        code = getattr(self.server, "access_code", "") or ""
        if not code:
            return True
        hdr = self.headers.get("Authorization", "")
        if hdr.startswith("Basic "):
            try:
                raw = base64.b64decode(hdr[6:]).decode("utf-8", "replace")
                _, _, pw = raw.partition(":")
                if pw == code:
                    return True
            except Exception:
                pass
        return False

    def _ask_auth(self):
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="DraveMedia"')
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        path_only = self.path.split("?", 1)[0]
        public = ("/manifest.webmanifest", "/dm-sw.js", "/dm-icon.svg",
                  "/dm-icon-192.png", "/dm-icon-512.png")
        if path_only not in public and not self._auth_ok():
            self._ask_auth(); return
        if path_only == "/_list.json":
            self._send_list(); return
        if path_only == "/manifest.webmanifest":
            self._send_text(MANIFEST_JSON, "application/manifest+json"); return
        if path_only == "/dm-sw.js":
            self._send_text(SERVICE_WORKER_JS, "application/javascript"); return
        if path_only == "/dm-icon.svg":
            self._send_text(PWA_ICON_SVG, "image/svg+xml"); return
        if path_only == "/dm-icon-192.png":
            self._send_bytes(make_icon_png(192), "image/png"); return
        if path_only == "/dm-icon-512.png":
            self._send_bytes(make_icon_png(512), "image/png"); return
        if path_only == "/play.json":
            self._send_play(); return
        if path_only.startswith("/hls/"):
            self._send_hls(path_only); return
        full = self._safe_path()
        if full is None:
            self.send_error(403); return
        if os.path.isdir(full):
            self._send_index(full); return
        if not os.path.isfile(full):
            self.send_error(404); return
        self._send_file(full)

    def _send_play(self):
        """Beslis hoe een (video)bestand het best afspeelt: direct, of via HLS (remux/transcode)."""
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        rel = (q.get("file", [""])[0]).lstrip("/")
        root = self.server.base_dir
        full = os.path.normpath(os.path.join(root, urllib.parse.unquote(rel)))
        if not (full == root or full.startswith(root + os.sep)) or not os.path.isfile(full):
            self._send_text(json.dumps({"mode": "direct", "url": "/" + rel}), "application/json"); return
        mode = decide_mode(full)
        if mode == "direct" or not ffmpeg_path():
            out = {"mode": "direct", "url": "/" + rel}
        else:
            token = self.server.hls.register(full, mode)
            out = {"mode": "hls", "url": "/hls/%s/index.m3u8" % token, "via": mode}
        self._send_text(json.dumps(out), "application/json")

    def _send_hls(self, path_only):
        parts = path_only.split("/", 3)   # ['', 'hls', token, 'index.m3u8' of 'seg_x.ts']
        if len(parts) < 4:
            self.send_error(404); return
        token, fname = parts[2], parts[3]
        mgr = self.server.hls
        if fname == "index.m3u8":
            s = mgr.ensure(token)
            if not s:
                self.send_error(404); return
            m3u8 = os.path.join(s["dir"], "index.m3u8")
            for _ in range(150):   # wacht tot de eerste playlist er is (max ~15s)
                if os.path.exists(m3u8):
                    break
                time.sleep(0.1)
            if not os.path.exists(m3u8):
                self.send_error(504); return
            try:
                with open(m3u8, "rb") as fh:
                    data = fh.read()
            except OSError:
                self.send_error(404); return
            self.send_response(200)
            self.send_header("Content-Type", "application/vnd.apple.mpegurl")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)
            return
        # een segment
        seg = mgr.path_for(token, fname)
        for _ in range(100):       # segment kan nog geschreven worden
            if seg:
                break
            time.sleep(0.1); seg = mgr.path_for(token, fname)
        if not seg:
            self.send_error(404); return
        self._send_file(seg)

    def _send_text(self, text, ctype):
        data = text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def _send_bytes(self, data, ctype):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "max-age=86400")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def _send_list(self):
        """Geef alle media op de server, gecategoriseerd op type (zoals Plex-bibliotheken)."""
        root = self.server.base_dir
        cats = {"music": [], "video": [], "image": []}
        for dirpath, _dirs, files in os.walk(root):
            for fn in sorted(files, key=str.lower):
                full = os.path.join(dirpath, fn)
                k = kind_of(full)
                cat = {"audio": "music", "video": "video", "image": "image"}.get(k)
                if not cat:
                    continue
                rel = os.path.relpath(full, root).replace(os.sep, "/")
                cats[cat].append({"name": fn, "url": "/" + urllib.parse.quote(rel)})
        data = json.dumps(cats).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def _send_index(self, folder):
        data = build_stream_app("").encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def _send_file(self, full):
        size = os.path.getsize(full)
        ctype = guess_mime(full)
        rng = self.headers.get("Range")
        start, end = 0, size - 1
        partial = False
        if rng and rng.startswith("bytes="):
            try:
                s, _, e = rng[6:].partition("-")
                if s.strip():
                    start = int(s)
                if e.strip():
                    end = int(e)
                if start > end or start >= size:
                    raise ValueError
                end = min(end, size - 1)
                partial = True
            except ValueError:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.end_headers(); return
        length = end - start + 1
        self.send_response(206 if partial else 200)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(length))
        if partial:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        if self.command == "HEAD":
            return
        try:
            with open(full, "rb") as fh:
                fh.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = fh.read(min(65536, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

    do_HEAD = do_GET


class MediaServer:
    """Lichtgewicht HTTP-server voor het lokale netwerk, in een eigen thread."""
    def __init__(self):
        self.httpd = None
        self.thread = None
        self.port = 0
        self.base_dir = ""
        self.secure = False

    def start(self, base_dir, port, access_code="", certfile="", keyfile=""):
        self.stop()
        self.base_dir = os.path.normpath(base_dir)
        httpd = ThreadingHTTPServer(("0.0.0.0", int(port)), _Handler)
        httpd.base_dir = self.base_dir
        httpd.hls = HlsManager()
        httpd.access_code = access_code or ""
        httpd.daemon_threads = True
        self.secure = False
        if certfile and keyfile and os.path.isfile(certfile) and os.path.isfile(keyfile):
            import ssl
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(certfile, keyfile)
            httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
            self.secure = True
        self.httpd = httpd
        self.port = httpd.server_address[1]
        self.thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        self.thread.start()
        self._reaper = threading.Thread(target=self._reap_loop, args=(httpd,), daemon=True)
        self._reaper.start()
        return self.port

    def _reap_loop(self, httpd):
        while self.httpd is httpd:
            time.sleep(20)
            try:
                httpd.hls.reap()
            except Exception:
                pass

    def stop(self):
        if self.httpd is not None:
            try:
                self.httpd.hls.shutdown()
            except Exception:
                pass
            try:
                self.httpd.shutdown(); self.httpd.server_close()
            except Exception:
                pass
            self.httpd = None
            self.thread = None

    @property
    def running(self):
        return self.httpd is not None


def build_stream_app(base=""):
    """Bouw de doorlopende, gecategoriseerde speler (zoals Plex/online radio).
    base="" -> de serverpagina zelf (zelfde origin).
    base="http://ip:8000" -> standalone pagina die alleen die URL nodig heeft."""
    if base:
        h = _STREAM_APP_HTML.replace('var BASE="{{BASE}}";', 'var BASE="%s";' % base)
    else:
        # Live server: leid het basispad af uit de URL van de pagina zelf, zodat de speler
        # ook werkt achter een reverse proxy onder een submap (bv. https://site/dm/).
        h = _STREAM_APP_HTML.replace(
            'var BASE="{{BASE}}";',
            'var BASE=(function(){var p=location.pathname;'
            'if(!/\\/$/.test(p))p=p.replace(/[^\\/]*$/,"");'
            'return p.replace(/\\/+$/,"");})();')
    return h.replace("{{BASE}}", base)


# ------------------------------------------------------- statische PWA-website (voor op dravenlock.nl)
def scan_media(folder):
    """Doorzoek een map recursief. Geeft (cats, files) terug:
    cats = {"music":[{name,url}], "video":[...], "image":[...]} met RELATIEVE urls,
    files = [(absoluut_pad, relatief_pad), ...] om mee te kopiëren."""
    cats = {"music": [], "video": [], "image": []}
    files = []
    for dirpath, _dirs, names in os.walk(folder):
        for fn in sorted(names, key=str.lower):
            full = os.path.join(dirpath, fn)
            cat = {"audio": "music", "video": "video", "image": "image"}.get(kind_of(full))
            if not cat:
                continue
            rel = os.path.relpath(full, folder).replace(os.sep, "/")
            cats[cat].append({"name": fn, "url": urllib.parse.quote(rel)})
            files.append((full, rel))
    return cats, files


def build_static_index(media_base="", list_url="media.json"):
    """De doorlopende speler, maar met RELATIEVE paden voor een statische site
    (leest list_url, registreert ./sw.js). De media wordt GESTREAMD vanaf
    media_base (leeg = naast de speler; anders bv. https://site/media/ of /media/).
    list_url = "media.json" (vaste lijst) of "media.php" (live lijst via PHP)."""
    h = _STREAM_APP_HTML
    h = h.replace('href="{{BASE}}/manifest.webmanifest"', 'href="manifest.webmanifest"')
    h = h.replace('href="{{BASE}}/dm-icon.svg"', 'href="dm-icon.svg"')
    h = h.replace('var BASE="{{BASE}}";', 'var BASE="%s";' % media_base)
    h = h.replace('fetch(BASE+"/_list.json")', 'fetch("%s")' % list_url)
    h = h.replace('navigator.serviceWorker.register(BASE + "/dm-sw.js")',
                  'navigator.serviceWorker.register("sw.js")')
    h = h.replace("{{BASE}}", "")  # veiligheidsnet
    return h


def build_media_php(media_dir):
    """PHP-script dat de mediamap LIVE scant en dezelfde JSON teruggeeft als media.json
    (relatieve, ge-encodeerde paden). Werkt op elke server met PHP (bijv. XAMPP)."""
    safe_dir = media_dir.replace("\\", "/").replace("'", "")
    audio = sorted(e.lstrip(".") for e in AUDIO_EXT)
    video = sorted(e.lstrip(".") for e in VIDEO_EXT)
    image = sorted(e.lstrip(".") for e in IMAGE_EXT)
    def php_list(exts, cat):
        return ", ".join("'%s'=>'%s'" % (e, cat) for e in exts)
    extmap = ",\n  ".join([php_list(audio, "music"), php_list(video, "video"), php_list(image, "image")])
    return """<?php
// DraveMedia - live medialijst. Scant de map en geeft dezelfde JSON als media.json.
// Pas hieronder alleen $MEDIA_DIR aan als je map verandert.
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('Access-Control-Allow-Origin: *');

$MEDIA_DIR = '%s';

$extCat = [
  %s
];

$out = ['music'=>[], 'video'=>[], 'image'=>[]];
if (is_dir($MEDIA_DIR)) {
  $it = new RecursiveIteratorIterator(
        new RecursiveDirectoryIterator($MEDIA_DIR, FilesystemIterator::SKIP_DOTS));
  foreach ($it as $f) {
    if (!$f->isFile()) continue;
    $ext = strtolower($f->getExtension());
    if (!isset($extCat[$ext])) continue;
    $rel = str_replace('\\\\', '/', substr($f->getPathname(), strlen($MEDIA_DIR)));
    $rel = ltrim($rel, '/');
    $parts = array_map('rawurlencode', explode('/', $rel));
    $out[$extCat[$ext]][] = ['name'=>$f->getFilename(), 'url'=>implode('/', $parts)];
  }
  foreach ($out as $k=>&$arr) {
    usort($arr, function($a,$b){ return strcasecmp($a['name'],$b['name']); });
  }
  unset($arr);
}
echo json_encode($out, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
""" % (safe_dir, extmap)


STATIC_MANIFEST_JSON = """{
  "name": "DraveMedia",
  "short_name": "DraveMedia",
  "description": "Doorlopende mediaspeler",
  "start_url": "./",
  "scope": "./",
  "display": "standalone",
  "orientation": "any",
  "background_color": "#0e0e11",
  "theme_color": "#0e0e11",
  "icons": [
    {"src": "dm-icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
    {"src": "dm-icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
    {"src": "dm-icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
    {"src": "dm-icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any"}
  ]
}"""

STATIC_SERVICE_WORKER_JS = """// DraveMedia (statische site) - cachet de schil, laat media streamen.
var CACHE = "dravemedia-site-v1";

self.addEventListener("install", function(e){
  self.skipWaiting();
  e.waitUntil(caches.open(CACHE).then(function(c){ return c.addAll(["./"]).catch(function(){}); }));
});

self.addEventListener("activate", function(e){
  e.waitUntil(
    caches.keys().then(function(keys){
      return Promise.all(keys.filter(function(k){ return k !== CACHE; })
                             .map(function(k){ return caches.delete(k); }));
    }).then(function(){ return self.clients.claim(); })
  );
});

function isMedia(p){
  return /\\.(mp3|m4a|aac|flac|wav|ogg|opus|wma|mp4|webm|mkv|mov|avi|m4v|jpe?g|png|gif|webp|bmp|svg|heic|jfif)$/i.test(p);
}

self.addEventListener("fetch", function(e){
  var req = e.request;
  if (req.method !== "GET") return;
  var url = new URL(req.url);
  if (url.pathname.endsWith("/media.json") || isMedia(url.pathname) || req.headers.has("range")) {
    return;  // media + lijst: altijd vers / streamen
  }
  if (req.mode === "navigate") {
    e.respondWith(
      fetch(req).then(function(resp){
        var copy = resp.clone();
        caches.open(CACHE).then(function(c){ c.put("./", copy); }).catch(function(){});
        return resp;
      }).catch(function(){ return caches.match("./"); })
    );
    return;
  }
  e.respondWith(
    caches.match(req).then(function(cached){
      var net = fetch(req).then(function(resp){
        var copy = resp.clone();
        caches.open(CACHE).then(function(c){ c.put(req, copy); }).catch(function(){});
        return resp;
      }).catch(function(){ return cached; });
      return cached || net;
    })
  );
});
"""


def guide_html(lang="nl"):
    """Snelgids-inhoud (rich text) voor de IN-APP dialoog. Donker/zilver, groot, toegankelijk."""
    _pre = ('<pre style="background:#15151b;border:1px solid #20202a;border-radius:8px;'
            'padding:10px;white-space:pre-wrap;">')
    if lang == "en":
        return ("""
<h1>DraveMedia — Quick guide</h1>
<p>DraveMedia is an all-in-one <b>media player</b>, <b>streaming server</b> and
<b>HTML5/PWA generator</b>. Play media locally, share your whole media folder as a continuous
web player, or build an installable web app (PWA) for your own site.</p>

<h2>The four tabs</h2>
<ul>
<li><b>🎬 Player</b> — open files or a folder (or drag &amp; drop) and play video/audio.
Space = play/pause, double-click = fullscreen, Esc = back.</li>
<li><b>🖼 Images</b> — view photos with zoom, fit and rotate; step through with previous/next.</li>
<li><b>📡 Server</b> — share a media folder as a continuous web player on your network, and export a PWA website.</li>
<li><b>&lt;/&gt; HTML5</b> — generate ready-made player code (whole server or a single file) with a live preview.</li>
</ul>

<h2>Which way suits you?</h2>
<p>There are three ways to share your media — from very easy to advanced:</p>
<ol>
<li><b>Just play at home</b> (no install) — ideal on your own Wi-Fi.</li>
<li><b>Install to your home screen</b> (as an app) — needs a secure connection (HTTPS).</li>
<li><b>HTML5 code on your own website</b> — for anyone with a site.</li>
</ol>

<h2>1. Just play at home (easiest)</h2>
<ol>
<li>Go to <b>📡 Server</b>, pick your media folder under <b>Server folder</b> and click <b>Start</b>.</li>
<li>DraveMedia shows one or more web links, e.g. <code>http://192.168.1.50:8000/</code>.</li>
<li>Open that link on your phone, tablet or TV — <b>on the same Wi-Fi</b>. Done: the continuous player streams straight from your PC.</li>
</ol>
<p>No install, no router settings. Note: your PC must stay on and DraveMedia must run, since the media lives on your PC. Tip: use the local <code>192.168...</code> address, not your external internet address.</p>
<h3>Plays every format (automatic conversion)</h3>
<p>Browsers can't play everything (e.g. <code>.mkv</code>, <code>.avi</code> or HEVC). DraveMedia
fixes this with FFmpeg: web-friendly files play directly (fast), files with the right codec but the
wrong container are remuxed instantly, and the rest is transcoded automatically to a format that
plays anywhere. You don't have to do anything — DraveMedia decides. DraveMedia uses <code>ffmpeg</code>/<code>ffprobe</code>; if they are missing, DraveMedia offers to
download them once automatically on first run (~80 MB). You can also place them next to DraveMedia
yourself. Without FFmpeg, only what the browser natively supports will play.</p>

<h2>2. Install to your home screen (as an app)</h2>
<p>Want a real app icon that opens in its own window? Then the page must be opened over <b>HTTPS</b>
(a secure connection) — every browser requires this for installing and for offline use. Over a plain
<code>http://</code> link the browser only lets you look.</p>
<p>Your media does <b>not</b> need to be copied anywhere — it stays on your disk and is streamed. You
only need a secure address. Two situations:</p>

<h3>2a. You already have a web server (e.g. Apache/XAMPP)</h3>
<p>Let your web server serve your media folder via an <i>Alias</i> (a link; the folder may be on
another drive — nothing is moved). In your Apache config:</p>
""" + _pre + """Alias /media "F:/Bewaren/muziek"
&lt;Directory "F:/Bewaren/muziek"&gt;
    Options +Indexes +FollowSymLinks
    Require all granted
&lt;/Directory&gt;
AddType application/manifest+json .webmanifest</pre>
<p>Restart Apache and test <code>https://your-domain/media/</code> — if you see the file listing, it
works. (On "Forbidden": grant the folder read access for the <b>Users</b> account in Windows.)</p>
<ol>
<li>Export in DraveMedia with <b>Media URL = /media/</b> (exactly the path from your Alias).</li>
<li>Put the exported files in a subfolder, e.g. <code>…/htdocs/yoursite/mediaspeler/</code>.</li>
<li>Open <code>https://your-domain/mediaspeler/</code> — playback and install now work.</li>
</ol>
<p>Important: the <b>Server folder and the Alias folder must be the same folder</b>, so the paths in
<code>media.json</code> match.</p>

<h3>2b. You have no web server</h3>
<p>Give your PC a free, secure address with a "tunnel" — without opening any ports:</p>
<ul>
<li><b>Cloudflare Tunnel</b> — links a (sub)domain to your PC; you then manage the domain via Cloudflare (free).</li>
<li><b>Tailscale Funnel</b> — gives your PC a fixed HTTPS address very quickly.</li>
</ul>
<p>Once your PC has such an HTTPS address, the <b>server page itself is already installable</b> — you
don't even need to export. Open the HTTPS address and install it.</p>

<h2>3. HTML5 code on your own website</h2>
<p>On the <b>&lt;/&gt; HTML5</b> tab you generate ready-made player code: for the <b>whole server</b>
(continuous player) or for a <b>single file/URL</b>. Use <b>Copy code</b> or <b>Save HTML</b> and place
it on your site. The built-in browser on the right shows a live preview.</p>

<h2>What is in the PWA export?</h2>
<p><b>Export website (PWA)…</b> (Server tab) creates <b>only</b> these files: <code>index.html</code>
(the player), <code>media.json</code> (the list), <code>manifest.webmanifest</code> (installable),
<code>sw.js</code> (offline shell), <code>dm-icon.svg</code> (icon). Your media is <b>not</b> copied;
it is streamed from the address you set in <b>Media URL</b> (empty = next to the player).</p>

<h2>Troubleshooting</h2>
<ul>
<li><b>List shows but nothing plays (404):</b> the Media URL is wrong. Make it point to where your
media really lives (e.g. <code>/media/</code>) and export again.</li>
<li><b>"Forbidden" at /media/:</b> grant read access to the media folder (Windows: user <b>Users</b> → Read).</li>
<li><b>Played before, not anymore / old version sticks:</b> the service worker caches the shell. Do
<b>Ctrl+F5</b> or open in an incognito window; or remove and reinstall the app.</li>
<li><b>Page on HTTPS but media on http://…:8000 → won't play:</b> "mixed content". A secure page can't
load insecure media. Make the media go over HTTPS too (see 2a/2b).</li>
<li><b>Phone won't load the home link:</b> use the local <code>192.168...</code> address on the same
Wi-Fi (not your external IP); set your Windows network to <b>Private</b>.</li>
<li><b>No install popup:</b> requires HTTPS; on iPhone there is never a popup (Share → "Add to Home Screen").</li>
</ul>

<h2>Support DraveMedia</h2>
<p>DraveMedia is made with care by Dravenlock. Like it? Click <b>♥ Donate</b> at the bottom right.
Questions? Email """ + CONTACT + """.</p>
""")
    return ("""
<h1>DraveMedia — Snelgids</h1>
<p>DraveMedia is een alles-in-één <b>mediaspeler</b>, <b>streaming-server</b> en
<b>HTML5/PWA-generator</b>. Speel media lokaal af, deel je hele mediamap als een doorlopende
webspeler, of maak een installeerbare web-app (PWA) voor op je eigen site.</p>

<h2>De vier tabbladen</h2>
<ul>
<li><b>🎬 Speler</b> — open bestanden of een map (of sleep ze erin) en speel video/audio af.
Spatie = afspelen/pauze, dubbelklik = volledig scherm, Esc = terug.</li>
<li><b>🖼 Afbeeldingen</b> — bekijk foto's met inzoomen, passend maken en draaien; blader met vorige/volgende.</li>
<li><b>📡 Server</b> — deel een mediamap als doorlopende webspeler op je netwerk, en exporteer een PWA-website.</li>
<li><b>&lt;/&gt; HTML5</b> — genereer kant-en-klare speler-code (hele server of één bestand) met live voorbeeld.</li>
</ul>

<h2>Welke manier past bij jou?</h2>
<p>Er zijn drie manieren om je media te delen — van heel eenvoudig naar geavanceerd:</p>
<ol>
<li><b>Gewoon thuis afspelen</b> (geen installatie) — ideaal op je eigen wifi.</li>
<li><b>Op je beginscherm installeren</b> (als app) — vereist een beveiligde verbinding (HTTPS).</li>
<li><b>HTML5-code op je eigen website</b> — voor wie een site heeft.</li>
</ol>

<h2>1. Gewoon thuis afspelen (het makkelijkst)</h2>
<ol>
<li>Ga naar <b>📡 Server</b>, kies je mediamap bij <b>Server-map</b> en klik <b>Starten</b>.</li>
<li>DraveMedia toont nu een of meer weblinks, bijv. <code>http://192.168.1.50:8000/</code>.</li>
<li>Open die link op je telefoon, tablet of tv — <b>op hetzelfde wifi</b>. Klaar: de doorlopende speler streamt rechtstreeks vanaf je pc.</li>
</ol>
<p>Geen installatie, geen router-instellingen. Let op: je pc moet aan blijven en DraveMedia moet draaien, want de media staat op je pc. Tip: gebruik het lokale <code>192.168...</code>-adres, niet je externe internet-adres.</p>
<h3>Speelt élk formaat af (automatisch omzetten)</h3>
<p>Browsers spelen lang niet alles af (bijv. <code>.mkv</code>, <code>.avi</code> of HEVC). DraveMedia
lost dat op met FFmpeg: web-vriendelijke bestanden gaan rechtstreeks (snel), bestanden met de
juiste codec maar verkeerde verpakking worden razendsnel "herverpakt", en de rest wordt automatisch
omgezet (transcode) naar een formaat dat overal speelt. Je hoeft niets te doen — DraveMedia kiest
zelf. Hiervoor gebruikt DraveMedia <code>ffmpeg</code>/<code>ffprobe</code>. Staan die er nog niet, dan
biedt DraveMedia bij de eerste start aan om ze eenmalig automatisch te downloaden (~80 MB). Je kunt
ze ook zelf naast DraveMedia zetten. Zonder FFmpeg speelt alleen wat de browser zelf aankan.</p>

<h2>2. Op je beginscherm installeren (als app)</h2>
<p>Wil je een echte app-knop die in een eigen venster opent? Dan moet de pagina via <b>HTTPS</b> (een
beveiligde verbinding) geopend worden — dat eisen alle browsers voor installeren én voor offline
gebruik. Over een gewone <code>http://</code>-link laat de browser alleen kijken toe.</p>
<p>Je media hoeft daarvoor <b>nergens heen gekopieerd</b> te worden — die blijft op je schijf en wordt
gestreamd. Je hebt alleen een beveiligd adres nodig. Twee situaties:</p>

<h3>2a. Je hebt al een eigen webserver (bijv. Apache/XAMPP)</h3>
<p>Laat je webserver je mediamap uitserveren via een <i>Alias</i> (een koppeling; de map mag op een
andere schijf staan, er wordt niets verplaatst). In je Apache-config:</p>
""" + _pre + """Alias /media "F:/Bewaren/muziek"
&lt;Directory "F:/Bewaren/muziek"&gt;
    Options +Indexes +FollowSymLinks
    Require all granted
&lt;/Directory&gt;
AddType application/manifest+json .webmanifest</pre>
<p>Herstart Apache en test <code>https://jouw-domein/media/</code> — zie je de maplijst, dan werkt het.
(Bij "Forbidden": geef de map in Windows leesrechten voor de gebruiker <b>Users</b>.)</p>
<ol>
<li>Exporteer in DraveMedia met <b>Media-URL = /media/</b> (precies het pad uit je Alias).</li>
<li>Zet de geëxporteerde bestanden in een submap, bijv. <code>…/htdocs/jouwsite/mediaspeler/</code>.</li>
<li>Open <code>https://jouw-domein/mediaspeler/</code> — afspelen én installeren werkt nu.</li>
</ol>
<p>Belangrijk: de <b>Server-map en de Alias-map moeten dezelfde map zijn</b>, zodat de paden in
<code>media.json</code> kloppen.</p>

<h3>2b. Je hebt geen webserver</h3>
<p>Geef je pc dan een gratis, beveiligd adres met een "tunnel" — zonder poorten open te zetten:</p>
<ul>
<li><b>Cloudflare Tunnel</b> — koppelt een eigen (sub)domein aan je pc; je beheert het domein dan via Cloudflare (gratis).</li>
<li><b>Tailscale Funnel</b> — geeft je pc razendsnel een vast HTTPS-adres.</li>
</ul>
<p>Zodra je pc zo'n HTTPS-adres heeft, is de <b>serverpagina zelf al installeerbaar</b> — je hoeft niet
eens te exporteren. Open het HTTPS-adres en installeer het.</p>

<h2>3. HTML5-code op je eigen website</h2>
<p>Op het tabblad <b>&lt;/&gt; HTML5</b> genereer je kant-en-klare speler-code: voor de <b>hele server</b>
(doorlopende speler) of voor <b>één bestand/URL</b>. Gebruik <b>Code kopiëren</b> of <b>HTML opslaan</b>
en zet het op je site. De ingebouwde browser rechts toont meteen een live voorbeeld.</p>

<h2>Wat zit er in de PWA-export?</h2>
<p><b>Website (PWA) exporteren…</b> (Server-tab) maakt <b>alleen</b> deze bestanden:
<code>index.html</code> (de speler), <code>media.json</code> (de lijst), <code>manifest.webmanifest</code>
(installeerbaar), <code>sw.js</code> (offline-schil), <code>dm-icon.svg</code> (icoon). Je media wordt
<b>niet</b> gekopieerd; die wordt gestreamd vanaf het adres dat je bij <b>Media-URL</b> opgeeft
(leeg = naast de speler).</p>

<h2>Problemen oplossen</h2>
<ul>
<li><b>Lijst verschijnt, maar niets speelt (404):</b> de Media-URL klopt niet. Laat 'm wijzen naar de
map waar je media écht staat (bijv. <code>/media/</code>) en exporteer opnieuw.</li>
<li><b>"Forbidden" bij /media/:</b> geef de mediamap leesrechten (Windows: gebruiker <b>Users</b> → Lezen).</li>
<li><b>Speelde eerst wél, nu niet meer / oude versie blijft hangen:</b> de service worker cachet de schil.
Doe <b>Ctrl+F5</b> of open in een incognito-venster; of verwijder en herinstalleer de app.</li>
<li><b>Pagina op HTTPS, maar media op http://…:8000 → speelt niet:</b> "mixed content". Een beveiligde
pagina mag geen onbeveiligde media laden. Zorg dat de media óók via HTTPS gaat (zie 2a/2b).</li>
<li><b>Telefoon laadt de thuislink niet:</b> gebruik het lokale <code>192.168...</code>-adres op
hetzelfde wifi (niet je externe IP); zet je netwerk in Windows op <b>Privé</b>.</li>
<li><b>Geen installeer-popup:</b> moet via HTTPS; op iPhone is er nooit een popup (Deel → "Zet op beginscherm").</li>
</ul>

<h2>Steun DraveMedia</h2>
<p>DraveMedia is met zorg gemaakt door Dravenlock. Waardeer je het? Klik op <b>♥ Donatie</b> rechtsonder.
Vragen? Mail """ + CONTACT + """.</p>
""")


MANIFEST_JSON = """{
  "name": "DraveMedia",
  "short_name": "DraveMedia",
  "description": "Doorlopende mediaspeler van je DraveMedia-server",
  "start_url": "./",
  "scope": "./",
  "display": "standalone",
  "orientation": "any",
  "background_color": "#0e0e11",
  "theme_color": "#0e0e11",
  "icons": [
    {"src": "dm-icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
    {"src": "dm-icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
    {"src": "dm-icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
    {"src": "dm-icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any"}
  ]
}"""

PWA_ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <rect width="512" height="512" rx="104" fill="#6fa3d6"/>
  <path d="M206 150 L378 256 L206 362 Z" fill="#0e0e11"/>
</svg>"""

_ICON_PNG_CACHE = {}


def make_icon_png(size):
    """Maak het DraveMedia-icoon als PNG (nodig voor 'installeren als app' op Android)."""
    if size in _ICON_PNG_CACHE:
        return _ICON_PNG_CACHE[size]
    from PIL import Image, ImageDraw
    import io
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = max(1, int(104 * size / 512))
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=(0x6f, 0xa3, 0xd6, 255))
    sc = size / 512.0
    tri = [(206 * sc, 150 * sc), (378 * sc, 256 * sc), (206 * sc, 362 * sc)]
    d.polygon(tri, fill=(0x0e, 0x0e, 0x11, 255))
    buf = io.BytesIO(); img.save(buf, "PNG")
    _ICON_PNG_CACHE[size] = buf.getvalue()
    return _ICON_PNG_CACHE[size]

SERVICE_WORKER_JS = """// DraveMedia service worker - cachet de app-schil, laat media streamen.
const CACHE = "dravemedia-shell-v1";
const SHELL = ["/"];

self.addEventListener("install", function(e){
  self.skipWaiting();
  e.waitUntil(caches.open(CACHE).then(function(c){ return c.addAll(SHELL).catch(function(){}); }));
});

self.addEventListener("activate", function(e){
  e.waitUntil(
    caches.keys().then(function(keys){
      return Promise.all(keys.filter(function(k){ return k !== CACHE; })
                             .map(function(k){ return caches.delete(k); }));
    }).then(function(){ return self.clients.claim(); })
  );
});

function isMedia(p){
  return /\\.(mp3|m4a|aac|flac|wav|ogg|opus|wma|mp4|webm|mkv|mov|avi|m4v|jpe?g|png|gif|webp|bmp|svg|heic|jfif)$/i.test(p);
}

self.addEventListener("fetch", function(e){
  var req = e.request;
  if (req.method !== "GET") return;                 // POST e.d. overslaan
  var url = new URL(req.url);
  // media + de lijst nooit cachen: laat streamen / altijd vers
  if (url.pathname === "/_list.json" || isMedia(url.pathname) || req.headers.has("range")) {
    return;
  }
  // navigatie / schil: eerst netwerk, val terug op cache (offline)
  if (req.mode === "navigate" || url.pathname === "/") {
    e.respondWith(
      fetch(req).then(function(resp){
        var copy = resp.clone();
        caches.open(CACHE).then(function(c){ c.put("/", copy); }).catch(function(){});
        return resp;
      }).catch(function(){ return caches.match("/"); })
    );
    return;
  }
  // overige (icoon/manifest): stale-while-revalidate
  e.respondWith(
    caches.match(req).then(function(cached){
      var net = fetch(req).then(function(resp){
        var copy = resp.clone();
        caches.open(CACHE).then(function(c){ c.put(req, copy); }).catch(function(){});
        return resp;
      }).catch(function(){ return cached; });
      return cached || net;
    })
  );
});
"""


_STREAM_APP_HTML = """<!DOCTYPE html>
<html lang="nl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DraveMedia</title>
<link rel="manifest" href="manifest.webmanifest">
<meta name="theme-color" content="#0e0e11">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="DraveMedia">
<link rel="apple-touch-icon" href="dm-icon.svg">
<link rel="icon" type="image/svg+xml" href="dm-icon.svg">
<link rel="stylesheet" href="https://cdn.plyr.io/3.7.8/plyr.css">
<script src="https://cdn.plyr.io/3.7.8/plyr.polyfilled.js"></script>
<script src="https://cdn.jsdelivr.net/npm/hls.js@1"></script>
<style>
 :root{--bg:#0e0e11;--panel:#15151b;--panel2:#0a0a0c;--silver:#d4d4d4;--accent:#6fa3d6;
       --plyr-color-main:#6fa3d6;--plyr-audio-controls-background:#15151b;
       --plyr-audio-control-color:#d4d4d4;--plyr-audio-control-color-hover:#fff;}
 *{box-sizing:border-box;}
 html,body{height:100%;}
 body{background:var(--bg);color:var(--silver);font-family:Segoe UI,Arial,sans-serif;
      font-size:15px;margin:0;display:flex;flex-direction:column;}
 .appbar{display:flex;align-items:center;gap:10px;background:var(--panel2);
         border-bottom:1px solid #20202a;padding:10px 16px;flex:none;flex-wrap:wrap;}
 .logo{width:30px;height:30px;flex:none;}
 .brand{color:#fff;font-size:19px;font-weight:bold;margin-right:8px;}
 .cat{background:#1b1b22;border:1px solid #2a2a31;color:var(--silver);border-radius:8px;
      padding:8px 14px;font-size:15px;cursor:pointer;}
 .cat:hover{border-color:var(--accent);}
 .cat.active{background:#24344a;border-color:var(--accent);color:#fff;font-weight:bold;}
 .spacer{flex:1;}
 .toggle{background:#1b1b22;border:1px solid #2a2a31;color:var(--silver);border-radius:8px;
         padding:8px 12px;font-size:14px;cursor:pointer;}
 .toggle.on{background:#24344a;border-color:var(--accent);color:#fff;}
 .playall{background:var(--accent);color:#06121f;border:none;border-radius:8px;
          padding:9px 16px;font-size:15px;font-weight:bold;cursor:pointer;}
 .main{flex:1;display:flex;min-height:0;}
 .side{width:360px;flex:none;display:flex;flex-direction:column;min-height:0;
       border-right:1px solid #20202a;padding:12px;}
 #zoek{width:100%;background:var(--panel);color:var(--silver);border:1px solid #2a2a31;
       border-radius:8px;padding:9px 12px;font-size:15px;margin-bottom:10px;flex:none;}
 #zoek:focus{outline:2px solid var(--accent);border-color:var(--accent);}
 .list{overflow:auto;display:flex;flex-direction:column;gap:5px;}
 .item{display:flex;align-items:center;gap:9px;color:var(--silver);text-decoration:none;
       background:var(--panel);border:1px solid #20202a;border-radius:8px;padding:9px 11px;
       white-space:nowrap;overflow:hidden;text-overflow:ellipsis;cursor:pointer;}
 .item .ic{flex:none;opacity:.85;}
 .item:hover,.item:focus{background:#1d2633;border-color:var(--accent);outline:none;}
 .item.active{background:#24344a;border-color:var(--accent);color:#fff;}
 .stagewrap{flex:1;display:flex;flex-direction:column;min-width:0;padding:16px;}
 .nowtitle{color:var(--accent);font-size:16px;font-weight:bold;margin-bottom:12px;
           white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
 .stage{flex:1;display:flex;align-items:center;justify-content:center;
        background:#000;border:1px solid #20202a;border-radius:12px;overflow:hidden;}
 .stage .hint{color:#666;font-size:16px;text-align:center;padding:20px;}
 .media{max-width:100%;max-height:100%;}
 video.media{width:100%;height:100%;}
 audio.media{width:90%;}
 .audiobox{display:flex;flex-direction:column;align-items:center;gap:18px;width:100%;}
 .audiobox .note{font-size:64px;}
 @media (max-width:760px){
   .main{flex-direction:column;}
   .side{width:auto;border-right:none;border-bottom:1px solid #20202a;max-height:42vh;}
   .stagewrap{min-height:46vh;}
 }
</style></head>
<body>
<div class="appbar">
  <svg class="logo" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <rect x="2" y="2" width="96" height="96" rx="22" fill="#6fa3d6"/>
    <polygon points="40,30 40,70 72,50" fill="#06121f"/></svg>
  <span class="brand">DraveMedia</span>
  <button class="cat active" id="cat-music"  onclick="setCat('music')">🎵 Muziek <small id="c-music"></small></button>
  <button class="cat"        id="cat-video"  onclick="setCat('video')">🎬 Video <small id="c-video"></small></button>
  <button class="cat"        id="cat-image"  onclick="setCat('image')">🖼 Afbeeldingen <small id="c-image"></small></button>
  <span class="spacer"></span>
  <button class="playall" onclick="playAll()">▶ Speel alles</button>
  <button class="toggle on" id="t-repeat" onclick="toggleRepeat()">↻ Herhaal alles</button>
  <button class="toggle" id="t-shuffle" onclick="toggleShuffle()">🔀 Shuffle</button>
</div>
<div class="main">
  <div class="side">
    <input id="zoek" type="search" placeholder="Zoeken…" autocomplete="off">
    <div class="list" id="list"></div>
  </div>
  <div class="stagewrap">
    <div class="nowtitle" id="nowtitle">Kies een categorie en druk op ▶ Speel alles</div>
    <div class="stage" id="stage"><span class="hint">▶ Speelt hier af — als een nummer klaar is, gaat de volgende vanzelf verder.</span></div>
  </div>
</div>
<script>
 var BASE="{{BASE}}";
 var DATA={music:[],video:[],image:[]};
 var cat="music", queue=[], pos=-1, shuffle=false, repeatAll=true, imgTimer=null;
 var listEl=document.getElementById("list"), stage=document.getElementById("stage"),
     nowt=document.getElementById("nowtitle"), zoek=document.getElementById("zoek");
 function counts(){
   document.getElementById("c-music").textContent="("+DATA.music.length+")";
   document.getElementById("c-video").textContent="("+DATA.video.length+")";
   document.getElementById("c-image").textContent="("+DATA.image.length+")";
 }
 fetch(BASE+"/_list.json").then(function(r){return r.json();})
   .then(function(d){DATA=d; counts(); render();})
   .catch(function(){ nowt.textContent="Kon de bibliotheek niet laden."; });
 function setCat(c){
   cat=c;
   ["music","video","image"].forEach(function(x){
     document.getElementById("cat-"+x).classList.toggle("active", x===c);});
   render();
 }
 function render(){
   var q=zoek.value.toLowerCase(), arr=DATA[cat]||[];
   listEl.innerHTML="";
   arr.forEach(function(it, i){
     if(q && it.name.toLowerCase().indexOf(q)<0) return;
     var ic = cat==="music"?"🎵":(cat==="video"?"🎬":"🖼");
     var a=document.createElement("div"); a.className="item"; a.dataset.idx=i;
     a.innerHTML='<span class="ic">'+ic+'</span> '+escapeHtml(it.name);
     a.onclick=function(){ queue=DATA[cat].slice(); pos=i; play(pos); };
     listEl.appendChild(a);
   });
 }
 function escapeHtml(s){return s.replace(/[&<>"]/g,function(c){
   return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
 function highlight(){
   [].slice.call(listEl.children).forEach(function(el){
     el.classList.toggle("active", parseInt(el.dataset.idx,10)===pos);});
 }
 function play(i){
   if(imgTimer){clearTimeout(imgTimer); imgTimer=null;}
   var it=queue[i]; if(!it) return;
   pos=i; nowt.textContent=it.name; highlight();
   var url=BASE+it.url; stage.innerHTML="";
   if(cat==="image"){
     var im=new Image(); im.src=url; im.className="media"; stage.appendChild(im);
     imgTimer=setTimeout(next, 6000);  // diavoorstelling: 6s per beeld
   } else if(cat==="music"){
     var box=document.createElement("div"); box.className="audiobox";
     var note=document.createElement("div"); note.className="note"; note.textContent="🎵";
     var au=document.createElement("audio"); au.src=url; au.controls=true; au.autoplay=true; au.className="media";
     au.onended=next; box.appendChild(note); box.appendChild(au); stage.appendChild(box);
     try{ if(window.Plyr){ new Plyr(au); } }catch(e){}
   } else {
     var v=document.createElement("video"); v.controls=true; v.autoplay=true; v.className="media";
     v.onended=next; stage.appendChild(v);
     if(window._dmHls){ try{window._dmHls.destroy();}catch(e){} window._dmHls=null;}
     function playDirect(){ v.src=url; try{ if(window.Plyr){ new Plyr(v); } }catch(e){} }
     // vraag de server hoe dit het best speelt (direct / HLS). Mislukt dat (statische export)
     // dan vallen we gewoon terug op direct afspelen.
     fetch("play.json?file="+encodeURIComponent(it.url)).then(function(r){
       if(!r.ok) throw 0; return r.json();
     }).then(function(d){
       if(d.mode==="hls"){
         var hu=BASE+d.url;
         if(v.canPlayType("application/vnd.apple.mpegurl")){ v.src=hu; }     // Safari/iOS: native HLS
         else if(window.Hls && window.Hls.isSupported()){
           var hls=new Hls(); window._dmHls=hls; hls.loadSource(hu); hls.attachMedia(v);
         } else { playDirect(); return; }
         try{ if(window.Plyr){ new Plyr(v); } }catch(e){}
       } else { url=BASE+d.url; playDirect(); }
     }).catch(function(){ playDirect(); });
   }
 }
 function next(){
   if(pos<queue.length-1){ pos++; }
   else if(repeatAll && queue.length){ pos=0; }
   else { return; }
   play(pos);
 }
 function playAll(){
   var arr=(DATA[cat]||[]).slice();
   if(!arr.length) return;
   if(shuffle){ for(var k=arr.length-1;k>0;k--){var j=Math.floor(Math.random()*(k+1));var t=arr[k];arr[k]=arr[j];arr[j]=t;} }
   queue=arr; pos=-1; next();
 }
 function toggleRepeat(){repeatAll=!repeatAll; document.getElementById("t-repeat").classList.toggle("on",repeatAll);}
 function toggleShuffle(){shuffle=!shuffle; document.getElementById("t-shuffle").classList.toggle("on",shuffle);}
 zoek.addEventListener("input", render);
 // PWA: registreer de service worker (cachet de schil; media blijft streamen)
 if("serviceWorker" in navigator){
   window.addEventListener("load", function(){
     navigator.serviceWorker.register(BASE + "/dm-sw.js").catch(function(){});
   });
 }
</script>
</body></html>
"""


# ----------------------------------------------------------------------------- HTML5-speler generator
def build_html5_player(src_url, title="", poster="", autoplay=False, loop=False,
                       controls=True, kind="video"):
    """Bouw een complete, zelfstandige HTML5-speler-pagina in Dravenlock-stijl."""
    title = title or "DraveMedia speler"
    attrs = []
    if controls:
        attrs.append("controls")
    if autoplay:
        attrs.append("autoplay")
        attrs.append("muted")  # autoplay werkt alleen betrouwbaar met muted
    if loop:
        attrs.append("loop")
    attrs.append('playsinline')
    attr_str = " ".join(attrs)
    src_esc = _html.escape(src_url, quote=True)
    poster_attr = f' poster="{_html.escape(poster, quote=True)}"' if (poster and kind == "video") else ""
    mime = guess_mime(src_url) if "." in src_url else ""
    type_attr = f' type="{mime}"' if mime and mime != "application/octet-stream" else ""

    if kind == "audio":
        media = (f'      <audio id="dm-media" {attr_str} preload="metadata">\n'
                 f'        <source src="{src_esc}"{type_attr}>\n'
                 f'        Je browser ondersteunt dit audioformaat niet.\n'
                 f'      </audio>')
    elif kind == "image":
        media = f'      <img id="dm-media" src="{src_esc}" alt="{_html.escape(title, quote=True)}">'
    else:
        media = (f'      <video id="dm-media" {attr_str}{poster_attr} preload="metadata">\n'
                 f'        <source src="{src_esc}"{type_attr}>\n'
                 f'        Je browser ondersteunt dit videoformaat niet.\n'
                 f'      </video>')

    return f"""<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_html.escape(title)}</title>
<link rel="stylesheet" href="https://cdn.plyr.io/3.7.8/plyr.css">
<script src="https://cdn.plyr.io/3.7.8/plyr.polyfilled.js"></script>
<style>
  :root {{ --bg:#0e0e11; --panel:#15151b; --silver:#d4d4d4; --accent:#6fa3d6;
           --plyr-color-main:#6fa3d6; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--silver);
          font-family:'Segoe UI',Arial,sans-serif; font-size:18px;
          display:flex; min-height:100vh; align-items:center; justify-content:center; }}
  .dm-wrap {{ width:100%; max-width:900px; padding:24px; }}
  .dm-title {{ color:var(--accent); font-size:22px; font-weight:bold; margin:0 0 14px; }}
  .dm-player {{ background:var(--panel); border:1px solid #20202a; border-radius:14px;
               padding:16px; box-shadow:0 10px 30px rgba(0,0,0,.45); }}
  #dm-media {{ width:100%; border-radius:10px; background:#000; display:block; outline:none; }}
  #dm-media:focus {{ outline:2px solid var(--accent); }}
  .dm-foot {{ margin-top:12px; color:#8b909a; font-size:14px; text-align:right; }}
  .dm-foot a {{ color:var(--accent); text-decoration:none; }}
</style>
</head>
<body>
  <div class="dm-wrap">
    <div class="dm-title">{_html.escape(title)}</div>
    <div class="dm-player">
{media}
    </div>
    <div class="dm-foot">Gemaakt met <a href="https://dravenlock.nl">DraveMedia</a></div>
  </div>
  <script>
    try {{ if (window.Plyr) {{ var _m = document.getElementById('dm-media');
      if (_m && _m.tagName !== 'IMG') new Plyr(_m); }} }} catch (e) {{}}
  </script>
</body>
</html>
"""


# (De grafische applicatie staat in het tweede deel van dit bestand.)

# ============================================================================= GUI
from PyQt6.QtCore import Qt, QUrl, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QImageReader, QKeySequence, QShortcut, QPolygonF
from PyQt6.QtCore import QPointF
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QSlider, QListWidget, QListWidgetItem,
    QFileDialog, QMessageBox, QComboBox, QCheckBox, QStackedWidget, QSizePolicy,
    QScrollArea, QPlainTextEdit, QSplitter, QDialog, QTextBrowser, QStatusBar,
    QProgressDialog,
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

# QtWebEngine MOET geïmporteerd worden vóórdat de QApplication bestaat.
# Optioneel: als het er niet is, werkt de app gewoon zonder ingebouwde browser.
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    HAS_WEBENGINE = True
except Exception:
    QWebEngineView = None
    HAS_WEBENGINE = False

# kleuren
BG = "#0e0e11"; PANEL = "#15151b"; PANEL2 = "#0a0a0c"; SILVER = "#d4d4d4"; ACCENT = "#6fa3d6"

DRAVENLOCK_QSS = f"""
* {{ font-size: 15px; color: {SILVER}; }}
QMainWindow, QDialog, QWidget {{ background: {BG}; }}
#header {{ background: {PANEL2}; border-bottom: 1px solid #20202a; }}
#title {{ color: #ffffff; font-size: 20px; font-weight: bold; }}
#ver {{ color: {ACCENT}; font-size: 12px; }}
#nav {{ background: {PANEL2}; border-right: 1px solid #20202a; }}
#nav QPushButton {{ text-align: left; padding: 12px 16px; border: none; border-radius: 8px;
    color: {SILVER}; background: transparent; font-size: 16px; }}
#nav QPushButton:hover {{ background: #1a1a22; }}
#nav QPushButton:checked {{ background: #1d2633; color: #ffffff; }}
QPushButton {{ background: #1b1b22; border: 1px solid #2a2a31; border-radius: 8px;
    padding: 8px 14px; }}
QPushButton:hover {{ border-color: {ACCENT}; }}
QPushButton:focus {{ outline: none; border: 2px solid {ACCENT}; }}
QPushButton#cta {{ background: {ACCENT}; color: #06121f; border: none; font-weight: bold; }}
QPushButton#modebtn {{ background: #1b1b22; border: 1px solid #2a2a31; border-radius: 8px; padding: 9px 16px; }}
QPushButton#modebtn:checked {{ background: #24344a; border: 1px solid {ACCENT}; color: #ffffff; }}
QPushButton#cta:hover {{ background: #84b4e0; }}
QLineEdit, QComboBox, QPlainTextEdit, QListWidget {{ background: {PANEL}; border: 1px solid #2a2a31;
    border-radius: 8px; padding: 7px; selection-background-color: {ACCENT}; }}
QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus, QListWidget:focus {{ border: 2px solid {ACCENT}; }}
QListWidget::item {{ padding: 7px; border-radius: 6px; }}
QListWidget::item:selected {{ background: #1d2633; color: #ffffff; }}
QSlider::groove:horizontal {{ height: 6px; background: #2a2a31; border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 3px; }}
QSlider::handle:horizontal {{ background: #ffffff; width: 16px; margin: -6px 0; border-radius: 8px; }}
QLabel#sectie {{ color: {ACCENT}; font-size: 13px; font-weight: bold; }}
QCheckBox {{ spacing: 8px; }}
QScrollArea {{ border: none; }}
"""


def make_logo(size):
    pm = QPixmap(size, size); pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm); p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setBrush(QColor(ACCENT)); p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(2, 2, size - 4, size - 4, size * 0.22, size * 0.22)
    # 'play'-driehoek
    p.setBrush(QColor("#06121f"))
    w = size; tri = QPolygonF([QPointF(w * 0.40, w * 0.30), QPointF(w * 0.40, w * 0.70),
                               QPointF(w * 0.72, w * 0.50)])
    p.drawPolygon(tri); p.end()
    return pm


def app_icon():
    for name in ("icon.ico", "logo.png"):
        fp = resource_path(name)
        if os.path.exists(fp):
            ic = QIcon(fp)
            if not ic.isNull():
                return ic
    return QIcon(make_logo(64))

# ----------------------------------------------------------------------------- hulp
def fmt_time(ms):
    if ms is None or ms < 0:
        ms = 0
    s = int(ms // 1000); h = s // 3600; m = (s % 3600) // 60; s = s % 60
    return (f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}")


def section(text):
    lbl = QLabel(text); lbl.setObjectName("sectie")
    return lbl


# ----------------------------------------------------------------------------- speler
class VideoView(QVideoWidget):
    """QVideoWidget met dubbelklik = fullscreen togglen en Escape = fullscreen verlaten."""
    def __init__(self, page):
        super().__init__()
        self.page = page

    def mouseDoubleClickEvent(self, e):
        self.page.fullscreen()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.page.exit_fullscreen()
        else:
            super().keyPressEvent(e)


class PlayerPage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.playlist = []
        self.index = -1
        self._build()
        self._make_qt_backend()

    def L(self, s):
        return t(s, self.app.lang)

    def _build(self):
        root = QHBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
        # links: afspeellijst
        side = QWidget(); side.setFixedWidth(260); sl = QVBoxLayout(side)
        sl.setContentsMargins(12, 12, 12, 12)
        sl.addWidget(section(self.L("Afspeellijst")))
        self.list = QListWidget(); self.list.itemDoubleClicked.connect(self._play_item)
        sl.addWidget(self.list, 1)
        brow = QHBoxLayout()
        ob = QPushButton(self.L("Openen…")); ob.clicked.connect(self.open_files); brow.addWidget(ob)
        fb = QPushButton(self.L("Map openen…")); fb.clicked.connect(self.open_folder); brow.addWidget(fb)
        sl.addLayout(brow)
        cl = QPushButton(self.L("Wissen")); cl.clicked.connect(self.clear_list); sl.addWidget(cl)
        brow2 = QHBoxLayout()
        brow2.addWidget(QLabel(self.L("Backend")))
        self.backend_combo = QComboBox()
        self.backend_combo.addItem(self.L("Systeem (Qt)"), "qt")
        self.backend_combo.addItem(self.L("VLC (alle formaten)"), "vlc")
        i = self.backend_combo.findData(self.app.cfg.get("backend", "qt"))
        self.backend_combo.setCurrentIndex(max(0, i))
        self.backend_combo.currentIndexChanged.connect(self._backend_changed)
        brow2.addWidget(self.backend_combo, 1)
        sl.addLayout(brow2)
        root.addWidget(side)

        # rechts: video + bediening
        right = QWidget(); rl = QVBoxLayout(right); rl.setContentsMargins(10, 10, 10, 10)
        self.video = VideoView(self); self.video.setStyleSheet("background:#000;")
        self.video.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._fs_on = False
        self.cover = QLabel(self.L("Sleep media hierheen of klik op Openen."))
        self.cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover.setStyleSheet("color:#777;")
        self.stack = QStackedWidget(); self.stack.addWidget(self.video); self.stack.addWidget(self.cover)
        self.stack.setCurrentWidget(self.cover)
        rl.addWidget(self.stack, 1)

        # tijdbalk
        trow = QHBoxLayout()
        self.cur = QLabel("0:00"); trow.addWidget(self.cur)
        self.seek = QSlider(Qt.Orientation.Horizontal); self.seek.setRange(0, 0)
        self.seek.sliderMoved.connect(self._seek); trow.addWidget(self.seek, 1)
        self.dur = QLabel("0:00"); trow.addWidget(self.dur)
        rl.addLayout(trow)

        # knoppen
        crow = QHBoxLayout()
        self.b_prev = QPushButton("⏮"); self.b_prev.clicked.connect(self.prev)
        self.b_play = QPushButton("▶"); self.b_play.setObjectName("cta"); self.b_play.clicked.connect(self.toggle_play)
        self.b_stop = QPushButton("⏹"); self.b_stop.clicked.connect(self.stop)
        self.b_next = QPushButton("⏭"); self.b_next.clicked.connect(self.next)
        for b in (self.b_prev, self.b_play, self.b_stop, self.b_next):
            b.setFixedWidth(64); crow.addWidget(b)
        crow.addStretch(1)
        self.b_mute = QPushButton("🔊"); self.b_mute.setFixedWidth(48); self.b_mute.clicked.connect(self.toggle_mute)
        crow.addWidget(self.b_mute)
        self.vol = QSlider(Qt.Orientation.Horizontal); self.vol.setFixedWidth(140)
        self.vol.setRange(0, 100); self.vol.setValue(int(self.app.cfg.get("volume", 80)))
        self.vol.valueChanged.connect(self.set_volume); crow.addWidget(self.vol)
        self.b_full = QPushButton("⛶"); self.b_full.setFixedWidth(48); self.b_full.clicked.connect(self.fullscreen)
        crow.addWidget(self.b_full)
        rl.addLayout(crow)
        root.addWidget(right, 1)

        self.setAcceptDrops(True)

    # ---- Qt-backend
    def _make_qt_backend(self):
        self.audio = QAudioOutput()
        self.audio.setVolume(self.vol.value() / 100.0)
        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video)
        self.player.positionChanged.connect(self._on_pos)
        self.player.durationChanged.connect(self._on_dur)
        self.player.playbackStateChanged.connect(self._on_state)
        self.vlc = None  # wordt lui aangemaakt indien gekozen

    def _backend_changed(self):
        be = self.backend_combo.currentData()
        if be == "vlc":
            import importlib.util as _il
            if _il.find_spec("vlc") is None:
                QMessageBox.information(self, self.L("VLC niet gevonden"),
                    self.L("De VLC-backend vereist dat VLC is geïnstalleerd (of python-vlc). "
                           "Ik val nu terug op de systeemspeler (Qt)."))
                self.backend_combo.blockSignals(True)
                self.backend_combo.setCurrentIndex(self.backend_combo.findData("qt"))
                self.backend_combo.blockSignals(False)
                be = "qt"
        self.app.cfg["backend"] = be; save_config(self.app.cfg)

    # ---- afspeellijst
    def open_files(self):
        exts = " ".join("*" + e for e in sorted(MEDIA_EXT))
        paths, _ = QFileDialog.getOpenFileNames(self, self.L("Openen…"),
            self.app.cfg.get("last_dir", APP_DIR), f"Media ({exts});;Alle bestanden (*)")
        if paths:
            self.app.cfg["last_dir"] = os.path.dirname(paths[0]); save_config(self.app.cfg)
            self._add(paths); 
            if self.index < 0:
                self._set_index(0); self._load_current(autoplay=True)

    def open_folder(self):
        d = QFileDialog.getExistingDirectory(self, self.L("Map openen…"),
                                             self.app.cfg.get("last_dir", APP_DIR))
        if not d:
            return
        self.app.cfg["last_dir"] = d; save_config(self.app.cfg)
        found = [os.path.join(d, n) for n in sorted(os.listdir(d))
                 if kind_of(os.path.join(d, n)) in ("video", "audio")]
        if found:
            self._add(found)
            if self.index < 0:
                self._set_index(0); self._load_current(autoplay=True)

    def _add(self, paths):
        for p in paths:
            self.playlist.append(p)
            self.list.addItem(QListWidgetItem(os.path.basename(p)))

    def clear_list(self):
        self.stop(); self.playlist = []; self.index = -1; self.list.clear()
        self.stack.setCurrentWidget(self.cover)

    def _play_item(self, item):
        self._set_index(self.list.row(item)); self._load_current(autoplay=True)

    def _set_index(self, i):
        self.index = i
        self.list.setCurrentRow(i)

    def _load_current(self, autoplay=False):
        if not (0 <= self.index < len(self.playlist)):
            return
        path = self.playlist[self.index]
        is_video = kind_of(path) == "video"
        self.stack.setCurrentWidget(self.video if is_video else self.cover)
        if not is_video:
            self.cover.setText("🎵  " + os.path.basename(path))
        self.player.setSource(QUrl.fromLocalFile(path))
        if autoplay:
            self.player.play()

    # ---- transport
    def toggle_play(self):
        if not self.playlist:
            self.open_files(); return
        st = self.player.playbackState()
        if st == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            if self.index < 0:
                self._set_index(0); self._load_current()
            self.player.play()

    def stop(self):
        self.player.stop()

    def prev(self):
        if self.playlist:
            self._set_index((self.index - 1) % len(self.playlist)); self._load_current(autoplay=True)

    def next(self):
        if self.playlist:
            self._set_index((self.index + 1) % len(self.playlist)); self._load_current(autoplay=True)

    def set_volume(self, v):
        self.audio.setVolume(v / 100.0)
        self.app.cfg["volume"] = v; save_config(self.app.cfg)
        self.b_mute.setText("🔇" if v == 0 else "🔊")

    def toggle_mute(self):
        self.audio.setMuted(not self.audio.isMuted())
        self.b_mute.setText("🔇" if self.audio.isMuted() else "🔊")

    def fullscreen(self):
        if self._fs_on:
            self.exit_fullscreen(); return
        # alleen zinvol voor video
        if not (0 <= self.index < len(self.playlist)) or kind_of(self.playlist[self.index]) != "video":
            return
        self._fs_on = True
        self._fs_stack_index = self.stack.indexOf(self.video)
        self.video.setParent(None)
        self.video.setWindowFlags(Qt.WindowType.Window)
        self.video.showFullScreen()
        self.video.setFocus()

    def exit_fullscreen(self):
        if not self._fs_on:
            return
        self._fs_on = False
        self.video.setWindowFlags(Qt.WindowType.Widget)
        self.stack.insertWidget(0, self.video)
        self.stack.setCurrentWidget(self.video)
        self.video.showNormal()

    def _seek(self, v):
        self.player.setPosition(v)

    def _on_pos(self, ms):
        if not self.seek.isSliderDown():
            self.seek.setValue(ms)
        self.cur.setText(fmt_time(ms))

    def _on_dur(self, ms):
        self.seek.setRange(0, ms); self.dur.setText(fmt_time(ms))

    def _on_state(self, st):
        playing = st == QMediaPlayer.PlaybackState.PlayingState
        self.b_play.setText("⏸" if playing else "▶")
        if st == QMediaPlayer.PlaybackState.StoppedState and self.player.position() and \
                self.player.duration() and self.player.position() >= self.player.duration() - 50:
            self.next()  # auto-door naar volgende

    # ---- drag & drop
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        media = [p for p in paths if kind_of(p) in ("video", "audio")]
        if media:
            self._add(media)
            if self.index < 0:
                self._set_index(0); self._load_current(autoplay=True)

# ----------------------------------------------------------------------------- afbeeldingen
class ImagePage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.files = []
        self.index = -1
        self.zoom = 1.0
        self.angle = 0
        self._pix = None
        self._build()

    def L(self, s):
        return t(s, self.app.lang)

    def _build(self):
        root = QVBoxLayout(self); root.setContentsMargins(10, 10, 10, 10)
        bar = QHBoxLayout()
        ob = QPushButton(self.L("Openen…")); ob.clicked.connect(self.open_files); bar.addWidget(ob)
        fb = QPushButton(self.L("Map openen…")); fb.clicked.connect(self.open_folder); bar.addWidget(fb)
        bar.addStretch(1)
        for txt, fn in [("⏮", self.prev), ("⏭", self.next), (self.L("Zoom -"), lambda: self._zoom(0.8)),
                        (self.L("Zoom +"), lambda: self._zoom(1.25)), (self.L("Passend"), self.fit),
                        (self.L("Draaien"), self.rotate)]:
            b = QPushButton(txt); b.clicked.connect(fn); bar.addWidget(b)
        root.addLayout(bar)
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(False)
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.canvas = QLabel(self.L("Niets geladen")); self.canvas.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.canvas.setStyleSheet("color:#777;")
        self.scroll.setWidget(self.canvas)
        root.addWidget(self.scroll, 1)
        self.info = QLabel(""); self.info.setStyleSheet("color:#8b909a;"); root.addWidget(self.info)
        self.setAcceptDrops(True)

    def open_files(self):
        exts = " ".join("*" + e for e in sorted(IMAGE_EXT))
        paths, _ = QFileDialog.getOpenFileNames(self, self.L("Openen…"),
            self.app.cfg.get("last_dir", APP_DIR), f"Afbeeldingen ({exts});;Alle bestanden (*)")
        if paths:
            self.app.cfg["last_dir"] = os.path.dirname(paths[0]); save_config(self.app.cfg)
            self.files = paths; self.index = 0; self._show()

    def open_folder(self):
        d = QFileDialog.getExistingDirectory(self, self.L("Map openen…"),
                                             self.app.cfg.get("last_dir", APP_DIR))
        if not d:
            return
        self.app.cfg["last_dir"] = d; save_config(self.app.cfg)
        self.files = [os.path.join(d, n) for n in sorted(os.listdir(d))
                      if kind_of(os.path.join(d, n)) == "image"]
        if self.files:
            self.index = 0; self._show()

    def _load_qimage(self, path):
        rd = QImageReader(path); rd.setAutoTransform(True)
        img = rd.read()
        if not img.isNull():
            return img
        # Pillow-terugval voor exotische formaten
        try:
            from PIL import Image, ImageQt
            im = Image.open(path).convert("RGBA")
            return ImageQt.ImageQt(im).copy()
        except Exception:
            return None

    def _show(self):
        if not (0 <= self.index < len(self.files)):
            return
        path = self.files[self.index]
        img = self._load_qimage(path)
        if img is None:
            self.canvas.setText(self.L("Kon dit bestand niet laden."))
            self._pix = None
            self.info.setText(os.path.basename(path)); return
        self._pix = QPixmap.fromImage(img)
        self.angle = 0
        self.fit()
        self.info.setText(f"{os.path.basename(path)}   ({self._pix.width()}×{self._pix.height()})   "
                          f"[{self.index + 1}/{len(self.files)}]")

    def _render(self):
        if self._pix is None:
            return
        pm = self._pix
        if self.angle:
            from PyQt6.QtGui import QTransform
            pm = pm.transformed(QTransform().rotate(self.angle), Qt.TransformationMode.SmoothTransformation)
        w = max(1, int(pm.width() * self.zoom)); h = max(1, int(pm.height() * self.zoom))
        scaled = pm.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.canvas.setPixmap(scaled); self.canvas.resize(scaled.size())

    def fit(self):
        if self._pix is None:
            return
        vp = self.scroll.viewport().size()
        pw, ph = self._pix.width(), self._pix.height()
        if pw and ph:
            self.zoom = min(vp.width() / pw, vp.height() / ph, 4.0) * 0.98
            self.zoom = max(0.05, self.zoom)
        self._render()

    def _zoom(self, f):
        if self._pix is not None:
            self.zoom = max(0.05, min(8.0, self.zoom * f)); self._render()

    def rotate(self):
        if self._pix is not None:
            self.angle = (self.angle + 90) % 360; self._render()

    def prev(self):
        if self.files:
            self.index = (self.index - 1) % len(self.files); self._show()

    def next(self):
        if self.files:
            self.index = (self.index + 1) % len(self.files); self._show()

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        imgs = [u.toLocalFile() for u in e.mimeData().urls()
                if u.isLocalFile() and kind_of(u.toLocalFile()) == "image"]
        if imgs:
            self.files = imgs; self.index = 0; self._show()

# ----------------------------------------------------------------------------- server-paneel
class ServerPage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.server = MediaServer()
        self._build()

    def L(self, s):
        return t(s, self.app.lang)

    def _build(self):
        root = QVBoxLayout(self); root.setContentsMargins(16, 16, 16, 16); root.setSpacing(12)
        root.addWidget(section(self.L("Server")))
        frow = QHBoxLayout()
        frow.addWidget(QLabel(self.L("Server-map:")))
        self.dir_edit = QLineEdit(self.app.cfg.get("server_dir", "")); frow.addWidget(self.dir_edit, 1)
        ch = QPushButton(self.L("Map kiezen…")); ch.clicked.connect(self._choose); frow.addWidget(ch)
        root.addLayout(frow)
        prow = QHBoxLayout()
        prow.addWidget(QLabel(self.L("Poort:")))
        self.port_edit = QLineEdit(str(self.app.cfg.get("server_port", 8000))); self.port_edit.setFixedWidth(90)
        prow.addWidget(self.port_edit)
        self.btn = QPushButton(self.L("Starten")); self.btn.setObjectName("cta"); self.btn.clicked.connect(self.toggle)
        prow.addWidget(self.btn)
        prow.addStretch(1)
        root.addLayout(prow)

        crow = QHBoxLayout()
        crow.addWidget(QLabel(self.L("Toegangscode (voor toegang van buitenaf):")))
        self.code_edit = QLineEdit(self.app.cfg.get("access_code", ""))
        self.code_edit.setPlaceholderText(self.L("leeg = open (alleen veilig op je eigen wifi)"))
        crow.addWidget(self.code_edit, 1)
        root.addLayout(crow)
        code_info = QLabel(self.L(
            "Sterk aangeraden als je de server via internet bereikbaar maakt. De browser vraagt de "
            "code eenmalig en onthoudt 'm. Let op: via http is de code onderweg niet versleuteld."))
        code_info.setWordWrap(True); code_info.setStyleSheet("color:#8b909a;")
        root.addWidget(code_info)

        # HTTPS (nodig om de app te kunnen installeren als PWA)
        self.use_https = QCheckBox(self.L("HTTPS gebruiken (nodig om te installeren als app)"))
        self.use_https.setChecked(bool(self.app.cfg.get("use_https", False)))
        root.addWidget(self.use_https)
        certrow = QHBoxLayout()
        certrow.addWidget(QLabel(self.L("Certificaat:")))
        self.cert_edit = QLineEdit(self.app.cfg.get("ssl_cert", ""))
        self.cert_edit.setPlaceholderText("bv. C:\\Certbot\\live\\rogersoft.dravenlock.nl\\fullchain.pem")
        certrow.addWidget(self.cert_edit, 1)
        cpick = QPushButton(self.L("Kies…")); cpick.clicked.connect(lambda: self._pick_into(self.cert_edit))
        certrow.addWidget(cpick)
        root.addLayout(certrow)
        keyrow = QHBoxLayout()
        keyrow.addWidget(QLabel(self.L("Sleutel:")))
        self.key_edit = QLineEdit(self.app.cfg.get("ssl_key", ""))
        self.key_edit.setPlaceholderText("bv. C:\\Certbot\\live\\rogersoft.dravenlock.nl\\privkey.pem")
        keyrow.addWidget(self.key_edit, 1)
        kpick = QPushButton(self.L("Kies…")); kpick.clicked.connect(lambda: self._pick_into(self.key_edit))
        keyrow.addWidget(kpick)
        root.addLayout(keyrow)
        drow = QHBoxLayout()
        drow.addWidget(QLabel(self.L("Domein (voor de link):")))
        self.domain_edit = QLineEdit(self.app.cfg.get("public_domain", ""))
        self.domain_edit.setPlaceholderText(self.L("bv. rogersoft.dravenlock.nl — leeg = toon IP"))
        drow.addWidget(self.domain_edit, 1)
        root.addLayout(drow)
        https_info = QLabel(self.L(
            "Wijs Certificaat/Sleutel naar je Let's Encrypt-bestanden (fullchain.pem en privkey.pem). "
            "Open de app daarna via https://JOUW-DOMEIN:poort/ — dan is 'm installeerbaar. "
            "Via het IP werkt installeren niet (certificaat hoort bij je domein)."))
        https_info.setWordWrap(True); https_info.setStyleSheet("color:#8b909a;")
        root.addWidget(https_info)

        self.status = QLabel(self.L("Server gestopt.")); self.status.setStyleSheet("color:#8b909a;")
        root.addWidget(self.status)
        self.urls = QListWidget(); self.urls.itemDoubleClicked.connect(self._open_url)
        root.addWidget(self.urls)
        arow = QHBoxLayout()
        ob = QPushButton(self.L("Open in browser")); ob.clicked.connect(lambda: self._open_sel()); arow.addWidget(ob)
        cb = QPushButton(self.L("Kopieer link")); cb.clicked.connect(lambda: self._copy_sel()); arow.addWidget(cb)
        arow.addStretch(1)
        root.addLayout(arow)
        # --- statische PWA-website exporteren (voor op een beveiligde site) ---
        mbrow = QHBoxLayout()
        mbrow.addWidget(QLabel(self.L("Media-URL (waar de media staat):")))
        self.media_base = QLineEdit(self.app.cfg.get("pwa_media_base", ""))
        self.media_base.setPlaceholderText(self.L("leeg = media staat naast de speler   ·   anders bijv. https://dravenlock.nl/media/"))
        mbrow.addWidget(self.media_base, 1)
        root.addLayout(mbrow)
        self.live_php = QCheckBox(self.L("Live lijst via PHP (server met PHP, bijv. XAMPP) — werkt altijd bij, geen her-export nodig"))
        self.live_php.setChecked(bool(self.app.cfg.get("pwa_live_php", False)))
        root.addWidget(self.live_php)
        exrow = QHBoxLayout()
        exb = QPushButton(self.L("Website (PWA) exporteren…")); exb.setObjectName("cta")
        exb.clicked.connect(lambda: self._export_pwa()); exrow.addWidget(exb)
        exrow.addStretch(1)
        root.addLayout(exrow)
        ex_info = QLabel(self.L(
            "Maakt alleen de PWA-bestanden (speler + manifest + service worker + icoon). "
            "De media blijft op de server staan en wordt gestreamd. Upload de map naar je "
            "beveiligde site, bijv. onder /mediaspeler/."))
        ex_info.setWordWrap(True); ex_info.setStyleSheet("color:#8b909a;")
        root.addWidget(ex_info)
        root.addStretch(1)

    def _export_pwa(self):
        src = self.dir_edit.text().strip()
        if not src or not os.path.isdir(src):
            QMessageBox.warning(self, self.L("Exporteren"),
                                self.L("Kies eerst een Server-map (de map met je media).")); return
        out = QFileDialog.getExistingDirectory(
            self, self.L("Kies waar de website-map komt te staan"), src)
        if not out:
            return
        dest = os.path.join(out, "mediaspeler")
        cats, _files = scan_media(src)
        total = sum(len(v) for v in cats.values())
        if total == 0:
            QMessageBox.warning(self, self.L("Exporteren"),
                                self.L("In deze map staan geen media-bestanden.")); return
        # waar staat de media op de server? (leeg = naast de speler)
        base = self.media_base.text().strip()
        if base and not base.endswith("/"):
            base += "/"
        self.app.cfg["pwa_media_base"] = self.media_base.text().strip()
        live = self.live_php.isChecked()
        self.app.cfg["pwa_live_php"] = live
        save_config(self.app.cfg)
        list_url = "media.php" if live else "media.json"
        try:
            os.makedirs(dest, exist_ok=True)
            with open(os.path.join(dest, "index.html"), "w", encoding="utf-8") as f:
                f.write(build_static_index(base, list_url))
            with open(os.path.join(dest, "media.json"), "w", encoding="utf-8") as f:
                json.dump(cats, f, ensure_ascii=False)
            if live:
                with open(os.path.join(dest, "media.php"), "w", encoding="utf-8") as f:
                    f.write(build_media_php(src))
            with open(os.path.join(dest, "manifest.webmanifest"), "w", encoding="utf-8") as f:
                f.write(STATIC_MANIFEST_JSON)
            with open(os.path.join(dest, "sw.js"), "w", encoding="utf-8") as f:
                f.write(STATIC_SERVICE_WORKER_JS)
            with open(os.path.join(dest, "dm-icon.svg"), "w", encoding="utf-8") as f:
                f.write(PWA_ICON_SVG)
            with open(os.path.join(dest, "dm-icon-192.png"), "wb") as f:
                f.write(make_icon_png(192))
            with open(os.path.join(dest, "dm-icon-512.png"), "wb") as f:
                f.write(make_icon_png(512))
        except Exception as e:
            QMessageBox.warning(self, self.L("Exporteren"), str(e)); return
        # GEEN media kopiëren: die blijft op de server en wordt gestreamd.
        where = self.L("De media wordt gestreamd vanaf: ") + (base or self.L("dezelfde map als de speler"))
        live_note = ("\n\n" + self.L("Live lijst: media.php scant je map automatisch — bij nieuwe media gewoon vernieuwen, geen her-export nodig.")) if live else ""
        msg = (self.L("Klaar! De PWA-bestanden staan hier:") + f"\n{dest}\n\n" +
               self.L("Upload alleen deze map naar je beveiligde site (bijv. /mediaspeler/). "
                      "De media zelf blijft op de server staan.") + "\n\n" + where + live_note)
        box = QMessageBox(self); box.setWindowTitle(self.L("Exporteren"))
        box.setText(msg)
        openbtn = box.addButton(self.L("Map openen"), QMessageBox.ButtonRole.AcceptRole)
        box.addButton(QMessageBox.StandardButton.Ok)
        box.exec()
        if box.clickedButton() is openbtn:
            from PyQt6.QtGui import QDesktopServices
            QDesktopServices.openUrl(QUrl.fromLocalFile(dest))

    def _choose(self):
        d = QFileDialog.getExistingDirectory(self, self.L("Map kiezen…"),
                                             self.dir_edit.text() or APP_DIR)
        if d:
            self.dir_edit.setText(d)

    def _pick_into(self, edit):
        path, _ = QFileDialog.getOpenFileName(self, self.L("Bestand kiezen…"),
                                              edit.text() or APP_DIR, "Certificaat (*.pem *.crt *.key);;Alle bestanden (*)")
        if path:
            edit.setText(path)

    def toggle(self):
        if self.server.running:
            self.server.stop()
            self.btn.setText(self.L("Starten")); self.status.setText(self.L("Server gestopt."))
            self.urls.clear(); return
        d = self.dir_edit.text().strip()
        if not d or not os.path.isdir(d):
            QMessageBox.warning(self, self.L("Server"), self.L("Geen map gekozen.")); return
        try:
            port = int(self.port_edit.text().strip() or "8000")
        except ValueError:
            port = 8000
        code = self.code_edit.text().strip()
        use_https = self.use_https.isChecked()
        cert = self.cert_edit.text().strip() if use_https else ""
        key = self.key_edit.text().strip() if use_https else ""
        domain = self.domain_edit.text().strip()
        if use_https and not (os.path.isfile(cert) and os.path.isfile(key)):
            QMessageBox.warning(self, self.L("Server"),
                                self.L("HTTPS aan, maar certificaat of sleutel niet gevonden. "
                                       "Controleer de bestandspaden.")); return
        try:
            port = self.server.start(d, port, code, cert, key)
        except Exception as e:
            QMessageBox.warning(self, self.L("Server"), str(e)); return
        self.app.cfg["server_dir"] = d; self.app.cfg["server_port"] = port
        self.app.cfg["access_code"] = code
        self.app.cfg["use_https"] = use_https
        self.app.cfg["ssl_cert"] = self.cert_edit.text().strip()
        self.app.cfg["ssl_key"] = self.key_edit.text().strip()
        self.app.cfg["public_domain"] = domain
        save_config(self.app.cfg)
        self.btn.setText(self.L("Stoppen"))
        self.status.setText(self.L("De server draait op:") +
                            ("  🔒" if code else "  ⚠ open (geen code)"))
        self.urls.clear()
        scheme = "https" if self.server.secure else "http"
        if domain:
            self.urls.addItem(f"{scheme}://{domain}:{port}/")
        ips = local_ips() or ["127.0.0.1"]
        for ip in ips:
            self.urls.addItem(f"{scheme}://{ip}:{port}/")

    def _sel_url(self):
        it = self.urls.currentItem()
        if it is None and self.urls.count() > 0:
            it = self.urls.item(0)            # niets geselecteerd -> pak de eerste
        return it.text() if it else None

    def _open_url(self, item):
        self._open(item.text())

    def _open_sel(self):
        if not self.server.running:
            return
        u = self._sel_url()
        if u:
            self._open(u)
        else:
            QMessageBox.information(self, self.L("Server"), self.L("Start eerst de server."))

    def _open(self, url):
        from PyQt6.QtGui import QDesktopServices
        ok = QDesktopServices.openUrl(QUrl(url))
        if not ok:
            QApplication.clipboard().setText(url)
            QMessageBox.information(self, self.L("Open in browser"),
                self.L("Kon de browser niet openen. De link is gekopieerd; plak 'm zelf in de browser:")
                + "\n" + url)

    def _copy_sel(self):
        u = self._sel_url()
        if u:
            QApplication.clipboard().setText(u)


# ----------------------------------------------------------------------------- HTML5-generator
class Html5Page(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self._build()

    def L(self, s):
        return t(s, self.app.lang)

    def _build(self):
        root = QVBoxLayout(self); root.setContentsMargins(16, 16, 16, 16); root.setSpacing(10)
        root.addWidget(section(self.L("HTML5")))

        # --- moduskeuze bovenin ---
        mrow = QHBoxLayout()
        self.m_server = QPushButton(self.L("Hele server (doorlopende speler)"))
        self.m_single = QPushButton(self.L("Eén bestand of URL"))
        for b in (self.m_server, self.m_single):
            b.setCheckable(True); b.setObjectName("modebtn")
        self.m_server.setChecked(True)
        self.m_server.clicked.connect(lambda: self._set_mode("server"))
        self.m_single.clicked.connect(lambda: self._set_mode("single"))
        mrow.addWidget(self.m_server); mrow.addWidget(self.m_single); mrow.addStretch(1)
        root.addLayout(mrow)

        # --- server-URL (in beide modi nodig/zinvol) ---
        srow = QHBoxLayout()
        srow.addWidget(QLabel(self.L("Server-URL:")))
        self.server_url = QLineEdit()
        self.server_url.setPlaceholderText("http://192.168.x.x:8000/")
        srow.addWidget(self.server_url, 1)
        fromsrv = QPushButton(self.L("van server")); fromsrv.clicked.connect(lambda: self._from_server())
        srow.addWidget(fromsrv)
        root.addLayout(srow)

        # --- uitleg in servermodus ---
        self.server_info = QLabel(self.L(
            "De speler speelt alle media van de server automatisch achter elkaar af "
            "(Muziek/Video/Afbeeldingen). Alleen de server-URL hierboven is nodig."))
        self.server_info.setWordWrap(True); self.server_info.setStyleSheet("color:#8b909a;")
        root.addWidget(self.server_info)

        # --- alle velden voor 'één bestand' in een apart, verbergbaar blok ---
        self.single_box = QWidget(); sb = QVBoxLayout(self.single_box)
        sb.setContentsMargins(0, 0, 0, 0); sb.setSpacing(10)
        g = QGridLayout()
        g.addWidget(QLabel(self.L("Mediabestand of URL:")), 0, 0)
        self.src = QLineEdit(); g.addWidget(self.src, 0, 1)
        br = QPushButton(self.L("Bladeren…")); br.clicked.connect(lambda: self._browse()); g.addWidget(br, 0, 2)
        g.addWidget(QLabel(self.L("Titel:")), 1, 0)
        self.title = QLineEdit(); g.addWidget(self.title, 1, 1, 1, 2)
        g.addWidget(QLabel(self.L("Poster (optioneel):")), 2, 0)
        self.poster = QLineEdit(); g.addWidget(self.poster, 2, 1, 1, 2)
        sb.addLayout(g)
        orow = QHBoxLayout()
        orow.addWidget(QLabel(self.L("Bestand op server:")))
        self.srv_file = QComboBox()
        self.srv_file.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.srv_file.currentIndexChanged.connect(self._pick_server_file)
        orow.addWidget(self.srv_file, 1)
        rf = QPushButton("↻"); rf.setFixedWidth(40); rf.clicked.connect(lambda: self._refresh_server_files())
        orow.addWidget(rf)
        sb.addLayout(orow)
        orow2 = QHBoxLayout()
        self.c_controls = QCheckBox(self.L("Bediening tonen")); self.c_controls.setChecked(True)
        self.c_auto = QCheckBox(self.L("Automatisch afspelen"))
        self.c_loop = QCheckBox(self.L("Herhalen"))
        self.c_copy = QCheckBox(self.L("Ook het mediabestand ernaast kopiëren"))
        for c in (self.c_controls, self.c_auto, self.c_loop):
            orow2.addWidget(c)
        orow2.addStretch(1)
        sb.addLayout(orow2)
        sb.addWidget(self.c_copy)
        root.addWidget(self.single_box)

        # --- knoppen + voorbeeld (gedeeld) ---
        brow = QHBoxLayout()
        gen = QPushButton(self.L("Genereer")); gen.clicked.connect(lambda: self.generate()); brow.addWidget(gen)
        view = QPushButton(self.L("Bekijk in browser")); view.clicked.connect(lambda: self._open_in_browser())
        brow.addWidget(view)
        copybtn = QPushButton(self.L("Code kopiëren")); copybtn.clicked.connect(lambda: self._copy_code())
        brow.addWidget(copybtn)
        self.save = QPushButton(self.L("HTML opslaan…")); self.save.setObjectName("cta")
        self.save.clicked.connect(lambda: self.save_html()); brow.addWidget(self.save)
        brow.addStretch(1)
        root.addLayout(brow)
        split = QSplitter(Qt.Orientation.Horizontal)
        # links: broncode
        left = QWidget(); ll = QVBoxLayout(left); ll.setContentsMargins(0, 0, 0, 0); ll.setSpacing(6)
        ll.addWidget(QLabel(self.L("Voorbeeld (broncode):")))
        self.preview = QPlainTextEdit(); self.preview.setReadOnly(True)
        self.preview.setStyleSheet("font-family:Consolas,monospace; font-size:13px;")
        ll.addWidget(self.preview, 1)
        split.addWidget(left)
        # rechts: live voorbeeld (ingebouwde browser, indien beschikbaar)
        right = QWidget(); rl = QVBoxLayout(right); rl.setContentsMargins(0, 0, 0, 0); rl.setSpacing(6)
        rl.addWidget(QLabel(self.L("Live voorbeeld:")))
        self.webview = None
        self._web_layout = rl
        ph = QLabel(self.L("Ingebouwde browser niet beschikbaar.\n"
                           "Draai herstel.bat om hem te installeren,\n"
                           "of gebruik 'Bekijk in browser'.")
                    if not HAS_WEBENGINE else
                    self.L("Live voorbeeld verschijnt zodra je dit tabblad opent."))
        ph.setWordWrap(True); ph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph.setStyleSheet("color:#777; background:#0a0a0c; border:1px solid #20202a; border-radius:10px;")
        rl.addWidget(ph, 1); self._web_ph = ph
        split.addWidget(right)
        split.setSizes([520, 520])
        root.addWidget(split, 1)

        self.mode = "server"
        self._set_mode("server")

    def _set_mode(self, mode):
        self.mode = mode
        self.m_server.setChecked(mode == "server")
        self.m_single.setChecked(mode == "single")
        self.single_box.setVisible(mode == "single")
        self.server_info.setVisible(mode == "server")
        self.preview.setPlainText("")

    def _ensure_webview(self):
        """Maak de Chromium-view pas aan als het HTML5-tabblad echt geopend wordt
        (scheelt veel geheugen als je 'm nooit gebruikt)."""
        if self.webview is not None or not HAS_WEBENGINE:
            return
        try:
            self.webview = QWebEngineView()
            self.webview.setMinimumWidth(280)
            if getattr(self, "_web_ph", None) is not None:
                self._web_ph.setParent(None); self._web_ph = None
            self._web_layout.addWidget(self.webview, 1)
        except Exception:
            self.webview = None

    def showEvent(self, e):
        super().showEvent(e)
        self._ensure_webview()
        try:
            self._refresh_server_files()
            # in servermodus alvast de URL invullen als de server draait
            if self.mode == "server" and not self.server_url.text().strip():
                sp = self.app.server_page
                if sp.server.running:
                    ips = local_ips() or ["127.0.0.1"]
                    self.server_url.setText(f"http://{ips[0]}:{sp.server.port}/")
        except Exception:
            pass

    def _browse(self):
        exts = " ".join("*" + e for e in sorted(MEDIA_EXT | IMAGE_EXT))
        path, _ = QFileDialog.getOpenFileName(self, self.L("Bladeren…"),
            self.app.cfg.get("last_dir", APP_DIR), f"Media ({exts});;Alle bestanden (*)")
        if path:
            self.src.setText(path)
            if not self.title.text():
                self.title.setText(os.path.splitext(os.path.basename(path))[0])

    def _from_server(self):
        sp = self.app.server_page
        if sp.server.running:
            ips = local_ips() or ["127.0.0.1"]
            self.server_url.setText(f"http://{ips[0]}:{sp.server.port}/")
            self._refresh_server_files()
        else:
            QMessageBox.information(self, "Server", self.L("Start eerst de server op het Server-tabblad."))

    def _server_base(self):
        """Map die de server bedient (indien actief), anders de ingestelde server-map."""
        sp = self.app.server_page
        if sp.server.running and sp.server.base_dir:
            return sp.server.base_dir
        return self.app.cfg.get("server_dir", "")

    def _refresh_server_files(self):
        """Vul de keuzelijst met media/afbeeldingen die op de server staan (recursief)."""
        base = self._server_base()
        self.srv_file.blockSignals(True)
        self.srv_file.clear()
        self.srv_file.addItem(self.L("— kies een bestand op de server —"), "")
        if base and os.path.isdir(base):
            found = []
            for dirpath, _dirs, files in os.walk(base):
                for fn in files:
                    full = os.path.join(dirpath, fn)
                    if kind_of(full) in ("video", "audio", "image"):
                        rel = os.path.relpath(full, base).replace(os.sep, "/")
                        found.append(rel)
            for rel in sorted(found, key=str.lower):
                self.srv_file.addItem(rel, rel)
        self.srv_file.blockSignals(False)

    def _pick_server_file(self, idx):
        rel = self.srv_file.currentData()
        if not rel:
            return
        base = self.server_url.text().strip()
        if not base:
            # geen server-URL ingevuld: probeer 'm automatisch te vullen
            sp = self.app.server_page
            if sp.server.running:
                ips = local_ips() or ["127.0.0.1"]
                base = f"http://{ips[0]}:{sp.server.port}/"
                self.server_url.setText(base)
            else:
                QMessageBox.information(self, "Server", self.L("Start eerst de server op het Server-tabblad."))
                return
        url = base.rstrip("/") + "/" + urllib.parse.quote(rel)
        self.src.setText(url)
        if not self.title.text():
            self.title.setText(os.path.splitext(os.path.basename(rel))[0])

    def _kind_and_url(self):
        raw = self.src.text().strip()
        is_url = raw.lower().startswith(("http://", "https://"))
        base = self.server_url.text().strip()
        if is_url:
            url = raw
        elif base:
            name = os.path.basename(raw)
            rel = name
            sd = self.app.cfg.get("server_dir", "")
            if sd and os.path.isfile(raw):
                try:
                    r = os.path.relpath(raw, sd)
                    if not r.startswith(".."):
                        rel = r.replace(os.sep, "/")
                except Exception:
                    pass
            url = base.rstrip("/") + "/" + urllib.parse.quote(rel)
        else:
            url = os.path.basename(raw)  # relatief, naast de html
        k = kind_of(raw)
        kind = k if k in ("audio", "image") else "video"
        return kind, url, is_url

    def generate(self):
        # Modus: hele server als doorlopende speler (alleen de server-URL nodig)
        if self.mode == "server":
            base = self.server_url.text().strip()
            if not base:
                sp = self.app.server_page
                if sp.server.running:
                    ips = local_ips() or ["127.0.0.1"]
                    base = f"http://{ips[0]}:{sp.server.port}/"
                    self.server_url.setText(base)
                else:
                    self.preview.setPlainText("")
                    QMessageBox.information(self, "HTML5",
                        self.L("Vul de server-URL in (of start de server en klik 'van server')."))
                    return ""
            code = build_stream_app(base.rstrip("/"))
            self.preview.setPlainText(code)
            self._update_live(code)
            return code
        if not self.src.text().strip():
            self.preview.setPlainText("")
            QMessageBox.information(self, "HTML5", self.L("Vul eerst een mediabestand of URL in."))
            return ""
        try:
            kind, url, _ = self._kind_and_url()
            code = build_html5_player(
                url, title=self.title.text().strip(),
                poster=os.path.basename(self.poster.text().strip()) if self.poster.text().strip() else "",
                autoplay=self.c_auto.isChecked(), loop=self.c_loop.isChecked(),
                controls=self.c_controls.isChecked(), kind=kind)
        except Exception as e:
            self.preview.setPlainText("")
            QMessageBox.warning(self, "HTML5", self.L("Er ging iets mis bij het genereren:") + "\n" + str(e))
            return ""
        self.preview.setPlainText(code)
        self._update_live(code)
        return code

    def _copy_code(self):
        code = self.preview.toPlainText()
        if not code.strip():
            code = self.generate()
        if not code:
            return
        QApplication.clipboard().setText(code)
        QMessageBox.information(self, "HTML5", self.L("De code is gekopieerd naar het klembord."))

    def _update_live(self, code):
        """Toon het resultaat meteen in de ingebouwde browser naast de code."""
        if self.webview is None:
            return
        try:
            if self.mode == "server":
                url = self.server_url.text().strip()
                if url:
                    self.webview.load(QUrl(url))
            else:
                import tempfile
                path = os.path.join(tempfile.gettempdir(), "dravemedia_preview.html")
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(code)
                self.webview.load(QUrl.fromLocalFile(path))
        except Exception:
            pass

    def _open_in_browser(self):
        from PyQt6.QtGui import QDesktopServices
        if self.mode == "server":
            base = self.server_url.text().strip()
            if not base:
                sp = self.app.server_page
                if sp.server.running:
                    ips = local_ips() or ["127.0.0.1"]
                    base = f"http://{ips[0]}:{sp.server.port}/"
                    self.server_url.setText(base)
                else:
                    QMessageBox.information(self, "HTML5",
                        self.L("Vul de server-URL in (of start de server en klik 'van server')."))
                    return
            self.generate()  # toon ook de broncode
            url = base
        else:
            code = self.generate()
            if not code:
                return
            import tempfile
            path = os.path.join(tempfile.gettempdir(), "dravemedia_preview.html")
            try:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(code)
            except Exception as e:
                QMessageBox.warning(self, "HTML5", str(e)); return
            url = QUrl.fromLocalFile(path).toString()
        # 1) probeer de ingebouwde browser (QtWebEngine, zoals DraveMaster)
        try:
            if HAS_WEBENGINE:
                self.app._browser_win = MiniBrowser(url, self.app.lang)
                self.app._browser_win.show()
                return
        except Exception:
            pass
        # 2) val terug op de systeembrowser
        ok = QDesktopServices.openUrl(QUrl(url))
        if not ok:
            QMessageBox.information(self, "HTML5", self.L("Kon de browser niet openen.") + "\n" + url)

    def save_html(self):
        code = self.generate()
        if not code:
            return
        path, _ = QFileDialog.getSaveFileName(self, self.L("HTML opslaan…"),
            os.path.join(self.app.cfg.get("last_dir", APP_DIR), "speler.html"), "HTML (*.html)")
        if not path:
            return
        if not path.lower().endswith(".html"):
            path += ".html"
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(code)
            # optioneel media ernaast kopiëren
            raw = self.src.text().strip()
            if self.c_copy.isChecked() and os.path.isfile(raw):
                import shutil
                shutil.copy2(raw, os.path.join(os.path.dirname(path), os.path.basename(raw)))
                if self.poster.text().strip() and os.path.isfile(self.poster.text().strip()):
                    shutil.copy2(self.poster.text().strip(),
                                 os.path.join(os.path.dirname(path), os.path.basename(self.poster.text().strip())))
            QMessageBox.information(self, "HTML5", self.L("Opgeslagen."))
        except Exception as e:
            QMessageBox.warning(self, "HTML5", str(e))

# ----------------------------------------------------------------------------- hoofdvenster
class QuickGuideDialog(QDialog):
    """In-app snelgids (donker/zilver, grote tekst), net als de andere Dravenlock-apps."""
    def __init__(self, parent, lang="nl"):
        super().__init__(parent)
        self.setWindowTitle(t("Snelgids", lang))
        self.resize(720, 640)
        lay = QVBoxLayout(self); lay.setContentsMargins(16, 16, 16, 16); lay.setSpacing(12)
        view = QTextBrowser()
        view.setOpenExternalLinks(True)
        view.setStyleSheet(
            "QTextBrowser{background:#0e0e11;color:#d4d4d4;border:1px solid #20202a;"
            "border-radius:10px;font-size:17px;padding:8px;}")
        view.setHtml(guide_html(lang))
        lay.addWidget(view, 1)
        row = QHBoxLayout(); row.addStretch(1)
        close = QPushButton(t("Sluiten", lang)); close.clicked.connect(self.accept)
        row.addWidget(close)
        lay.addLayout(row)


class MiniBrowser(QWidget):
    """Eenvoudige ingebouwde browser (QtWebEngine), net als in DraveMaster.
    Wordt alleen gebruikt als QtWebEngine beschikbaar is; anders systeembrowser."""
    def __init__(self, url, lang="nl"):
        super().__init__()
        self.setWindowTitle("DraveMedia — voorbeeld")
        self.resize(1040, 720)
        lay = QVBoxLayout(self); lay.setContentsMargins(8, 8, 8, 8); lay.setSpacing(8)
        nav = QHBoxLayout()
        self.view = QWebEngineView()
        b_back = QPushButton("◀"); b_fwd = QPushButton("▶"); b_rel = QPushButton("↻")
        for b in (b_back, b_fwd, b_rel):
            b.setFixedWidth(44); nav.addWidget(b)
        b_back.clicked.connect(lambda: self.view.back())
        b_fwd.clicked.connect(lambda: self.view.forward())
        b_rel.clicked.connect(lambda: self.view.reload())
        self.addr = QLineEdit(url)
        self.addr.returnPressed.connect(lambda: self.view.load(QUrl(self.addr.text().strip())))
        nav.addWidget(self.addr, 1)
        b_ext = QPushButton(t("Open in browser", lang)); b_ext.setFixedWidth(150)
        b_ext.clicked.connect(lambda: self._external())
        nav.addWidget(b_ext)
        lay.addLayout(nav)
        lay.addWidget(self.view, 1)
        self.view.urlChanged.connect(lambda u: self.addr.setText(u.toString()))
        self.view.load(QUrl(url))

    def _external(self):
        from PyQt6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl(self.addr.text().strip()))


class _FfmpegDownloadThread(QThread):
    progress = pyqtSignal(int, int)
    done = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        ok = download_ffmpeg(progress=lambda d, t: self.progress.emit(d, t),
                             cancel=lambda: self._cancel)
        self.done.emit(bool(ok))


class DraveMedia(QMainWindow):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        self.lang = self.cfg.get("lang") or system_lang()
        self.setWindowTitle(APP_NAME)
        self.resize(1100, 720)
        self.setMinimumSize(820, 560)

        central = QWidget(); self.setCentralWidget(central)
        outer = QVBoxLayout(central); outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)
        outer.addWidget(self._header())

        body = QHBoxLayout(); body.setContentsMargins(0, 0, 0, 0); body.setSpacing(0)
        # navigatie
        nav = QWidget(); nav.setObjectName("nav"); nav.setFixedWidth(190)
        nl = QVBoxLayout(nav); nl.setContentsMargins(10, 14, 10, 14); nl.setSpacing(6)
        self.nav_btns = []
        self.pages = QStackedWidget()
        self.player_page = PlayerPage(self)
        self.image_page = ImagePage(self)
        self.server_page = ServerPage(self)
        self.html5_page = Html5Page(self)
        items = [("🎬", self.L("Speler"), self.player_page),
                 ("🖼", self.L("Afbeeldingen"), self.image_page),
                 ("📡", self.L("Server"), self.server_page),
                 ("</>", self.L("HTML5"), self.html5_page)]
        for i, (icon, label, page) in enumerate(items):
            b = QPushButton(f"  {icon}  {label}"); b.setCheckable(True)
            b.clicked.connect(lambda _c=False, idx=i: self._go(idx))
            nl.addWidget(b); self.nav_btns.append(b); self.pages.addWidget(page)
        nl.addStretch(1)
        body.addWidget(nav)
        body.addWidget(self.pages, 1)
        bw = QWidget(); bw.setLayout(body); outer.addWidget(bw, 1)

        self._go(0)
        QShortcut(QKeySequence(Qt.Key.Key_Space), self, activated=self.player_page.toggle_play)

        # statusbalk met donatieknop (huisstijl)
        sb = QStatusBar(); self.setStatusBar(sb)
        sb.showMessage(f"{APP_NAME} v{APP_VERSION}")
        donate = QPushButton(self.L("♥ Donatie")); donate.setObjectName("cta")
        donate.setToolTip(self.L("Steun Dravenlock"))
        donate.clicked.connect(self._donate)
        sb.addPermanentWidget(donate)

        # Eerste start: download FFmpeg automatisch als 't ontbreekt (nodig voor alle formaten)
        QTimer.singleShot(600, self._ensure_ffmpeg)

    def _ensure_ffmpeg(self):
        if os.name != "nt":
            return  # op Windows downloaden we .exe's; elders via pakketbeheer
        if ffmpeg_path() and ffprobe_path():
            return
        self._download_ffmpeg()

    def _download_ffmpeg(self):
        dlg = QProgressDialog(self.L("FFmpeg downloaden… (eenmalig, voor alle formaten)"),
                              self.L("Annuleren"), 0, 100, self)
        dlg.setWindowTitle("FFmpeg")
        dlg.setWindowModality(Qt.WindowModality.ApplicationModal)
        dlg.setAutoClose(False); dlg.setAutoReset(False)
        dlg.setMinimumDuration(0); dlg.setValue(0)
        self._ff_worker = _FfmpegDownloadThread()
        self._ff_worker.progress.connect(
            lambda done, total: dlg.setValue(int(done * 100 / total)) if total else dlg.setLabelText(
                self.L("FFmpeg downloaden…") + " %.1f MB" % (done / 1048576.0)))

        def finished(ok):
            dlg.close()
            if ok:
                QMessageBox.information(self, "FFmpeg",
                                        self.L("FFmpeg is geïnstalleerd. Alle formaten spelen nu af."))
            else:
                QMessageBox.warning(self, "FFmpeg",
                                    self.L("Downloaden is niet gelukt. Controleer je internet, of "
                                           "zet ffmpeg.exe en ffprobe.exe zelf naast DraveMedia."))
        self._ff_worker.done.connect(finished)
        dlg.canceled.connect(self._ff_worker.cancel)
        self._ff_worker.start()

    def L(self, s):
        return t(s, self.lang)

    def _header(self):
        w = QWidget(); w.setObjectName("header"); w.setFixedHeight(58)
        lay = QHBoxLayout(w); lay.setContentsMargins(14, 8, 14, 8)
        logo = QLabel(); logo.setPixmap(make_logo(34)); lay.addWidget(logo)
        title = QLabel(APP_NAME); title.setObjectName("title"); lay.addWidget(title)
        ver = QLabel("v" + APP_VERSION); ver.setObjectName("ver"); lay.addWidget(ver)
        lay.addStretch(1)
        guide = QPushButton(self.L("Snelgids")); guide.clicked.connect(self._guide); lay.addWidget(guide)
        about = QPushButton(self.L("Over")); about.clicked.connect(self._about); lay.addWidget(about)
        return w

    def _guide(self):
        QuickGuideDialog(self, self.lang).exec()

    def _donate(self):
        from PyQt6.QtGui import QDesktopServices
        if not QDesktopServices.openUrl(QUrl(DONATE_URL)):
            QMessageBox.information(self, self.L("Donatie"),
                                    self.L("Steun Dravenlock — bedankt!") + f"\n{DONATE_URL}")

    def _go(self, idx):
        self.pages.setCurrentIndex(idx)
        for i, b in enumerate(self.nav_btns):
            b.setChecked(i == idx)

    def _about(self):
        QMessageBox.information(self, self.L("Over"),
            f"{APP_NAME} v{APP_VERSION}\n\nAlles-in-een mediaspeler, -server en HTML5-generator.\n"
            f"Dravenlock\n{CONTACT}")

    def closeEvent(self, e):
        try:
            self.server_page.server.stop()
            self.player_page.player.stop()
        except Exception:
            pass
        save_config(self.cfg)
        super().closeEvent(e)


def main():
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_DontShowIconsInMenus, False)
    if HAS_WEBENGINE:
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyleSheet(DRAVENLOCK_QSS)
    ic = app_icon(); app.setWindowIcon(ic)
    win = DraveMedia(); win.setWindowIcon(ic); win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
