# 🔓 OAuth 2.0 Attack Simulation Tool

This repository contains a Python-based **security testing toolkit** designed to evaluate vulnerabilities in **OAuth 2.0**-secured APIs.  
It simulates **Token Injection**, **Session Hijacking**, and **Replay Attacks** under controlled laboratory conditions to measure attack feasibility, performance impact, and security effectiveness.

This project is part of an academic thesis comparing **OAuth 2.0** with **SPHINCS+** in mitigating API-based attacks.

---

## 📌 Key Features

- **Attack Types Supported**
  - **Token Injection** – Reuses a stolen or intercepted OAuth 2.0 token to access protected APIs without authorization.
  - **Session Hijacking** – Uses an active session token to impersonate a legitimate user.
  - **Replay Attack** – Resends previously valid requests to bypass security.
- **Detailed Logging**
  - Signing time (ms)
  - API response time (ms)
  - HTTP status codes
  - Attack success/failure
- **Multiple Output Formats**
  - Console output
  - CSV and Excel file logging
  - Optional `.log` file with detailed traces
- **Graphical User Interface (GUI)**
  - Start/stop attacks with a single click
  - Real-time status updates
  - Data visualization of attack results

---
## 📷 ScreenShots
<img width="1104" height="621" alt="image" src="https://github.com/user-attachments/assets/84ed9499-2c84-4f8f-807a-199b712d4d8a" />
<img width="1919" height="1025" alt="image" src="https://github.com/user-attachments/assets/a10b78d4-fd19-4897-a9b3-8bbac66f1bb8" />

<img width="1105" height="621" alt="image" src="https://github.com/user-attachments/assets/f38c4d29-cf3e-4a2a-b611-0663bcbb2e6e" />
<img width="1919" height="1031" alt="image" src="https://github.com/user-attachments/assets/4eb428b6-3bf8-4c2d-a2ec-e11464af80a2" />

<img width="1107" height="622" alt="image" src="https://github.com/user-attachments/assets/f7317899-668a-45e0-804a-06f605c9a9ca" />
<img width="1919" height="1031" alt="image" src="https://github.com/user-attachments/assets/eb28c8ae-cd52-45cf-a47f-115565af62ff" />

---

## 📂 Project Structure
OAUTH2-API-Web-Security/.venv
│
├── /attacks
  ├── /dist
    ├── vulnerable_attack.exe
    ├── session_hijack_replay_oauth2.exe
  ├── vulnerable_attack.py
  ├── session_hijack_replay_oauth2.py
├── /dist
  ├── app.exe
├── app.exe

---

## ⚙️ Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/UNIQUELO2001/OAUTH2-API-Web-Security
   cd OAUTH2-API-Web-Security
   
## 🚀 Usage
1. Command-Line Mode
Run the attack directly in the terminal:

bash
Copy
Edit
python oauth2_attack.py

2. GUI Mode
Launch the interactive interface:

bash
Copy
Edit
python oauth2_attack_ui.py
A browser window will open

You can start/stop the attack and view live logs

Charts show attack success rate and response times over time

📊 Example Output
Console Output
yaml
Copy
Edit

🚨 Starting token injection attack for 30 minutes...

[2025-08-06 23:09:59.521463] [FAIL] Status: 401 | Signing: 0.0005 ms | Response: 2039.3776 ms
[2025-08-06 23:10:02.542721] [FAIL] Status: 401 | Signing: 0.0009 ms | Response: 2020.3175 ms
[2025-08-06 23:10:05.595447] [FAIL] Status: 401 | Signing: 0.0011 ms | Response: 2051.8251 ms
CSV Output
Timestamp	Signing Time (ms)	Response Time (ms)	Status Code	Result	Response Body
2025-08-06T23:09:59	0.0005	2039.3776	401	FAIL	Unauthorized

📈 Research Context
This tool was developed as part of a thesis comparing OAuth 2.0 and SPHINCS+ for securing API requests against:

Session Hijacking

Replay Attacks

Token Injection Attacks

The objective is to measure quantitatively:

Attack Success Rate – How often each attack bypasses the security mechanism.

Performance Overhead – The added signing time and response time.

Protocol Resilience – The ability to block unauthorized requests.

⚠️ Disclaimer
This tool is for educational and research purposes only.
Please don't run it against systems you do not own or have explicit permission to test.
Unauthorized use may violate local, national, or international laws.

📜 License
This project is licensed under the MIT License – see the LICENSE file for details.
