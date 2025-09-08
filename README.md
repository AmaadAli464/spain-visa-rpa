# Spain Visa RPA Bot (Playwright + PyQt5)

An **Robotic Process Automation (RPA)** project to automate the Spain Visa appointment workflow using **Playwright** and **PyQt5**.

This project is **not a test automation framework**, but a real **business workflow automation (RPA)** project designed to simulate human behavior on the visa booking website.

---

## 📌 Features

### Built So Far
**Desktop GUI (PyQt5)**
- One-click button to start the automation workflow.
- Window is minimizable and user-friendly.

**Playwright Automation**
- Loads the Spain Visa website.
- Handles and closes the disclaimer popup automatically.
- Navigates through the **"Book Appointment"** dropdown.
- Opens the **Login page** in a new tab for further actions.

**Scalable Architecture**
- `configs/` → Playwright browser configuration.
- `pages/` → Page Object Model classes (`HomePage`, upcoming `LoginPage`).
- `ui/` → PyQt5 desktop application interface.
- `main.py` → Orchestrates the workflow.

---

## 🛠️ Tech Stack
- Python 3.10+
- Playwright (sync API)
- PyQt5 (desktop GUI)
- Pandas / OpenPyXL *(planned: Excel/CSV data integration)*
- Pillow (PIL) *(planned: image upload/resizing)*
- Proxy + CAPTCHA API integration *(planned)*

---

## 📂 Project Structure

```bash
spain-visa-rpa/
│── configs/
│   └── browser_config.py      # Playwright browser launch config
│
│── pages/
│   └── home_page.py           # Home page automation logic
│   └── login_page.py          # (planned) Login page logic
│
│── ui/
│   └── main_window.py         # PyQt5 desktop UI
│
│── main.py                    # Orchestrates workflow
│── requirements.txt           # Python dependencies
│── README.md                  # Project documentation
```

## ⚙️ Installation

**Clone the repo:**

```bash
git clone https://github.com/YOUR_USERNAME/spain-visa-rpa.git
cd spain-visa-rpa
```


**Install dependencies:**

```bash
pip install -r requirements.txt
playwright install
```

## ▶️ Run the Bot
- Start the GUI:
```bash
python app.py
```
- Click the “Start Workflow” button in the app to begin the automation. 🎉


## 🚧 Roadmap
- [x] Load homepage + close disclaimer
- [x] Navigate to Book Appointment → Login page
- [ ] Implement login workflow
- [ ] Add CSV/Excel data integration
- [ ] Add CAPTCHA solving
- [ ] Add proxy rotation
- [ ] Add sniper engine for appointment slots
- [ ] Full RPA delivery with logging & error handling


## 📜 License
- This project is for educational & research purposes only.
- Not affiliated with BLS Spain or official visa centers.

