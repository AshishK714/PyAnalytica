# Module 0 — Installing PyAnalytica

You will install two things: **Python**, and then **PyAnalytica** itself. Budget about 20 minutes. You only do this once, and at the end you'll have a file you double-click to start the software from then on.

Follow your operating system's section from top to bottom. Don't skip steps, even ones that look unnecessary — several exist to prevent a specific error later.

> **You need a Windows PC or a Mac.** If you have neither, or something blocks installation, use **UIUC AnyWare** — see [Using UIUC AnyWare instead](#using-uiuc-anyware-instead). Don't spend an evening fighting your laptop; AnyWare works and takes minutes.

---

## Which Python version

PyAnalytica needs **Python 3.10 or newer**. We recommend **3.12**.

Python's website offers a newer version than 3.12 on its front page. **Don't click the big yellow button.** Use the links below, which take you to the list of releases, and pick the newest **3.12.x** installer.

---

## Windows

### Step 1 — Install Python

1. Go to **https://www.python.org/downloads/windows/**
2. Under "Stable Releases", find the newest **Python 3.12.x** entry and click **Windows installer (64-bit)**.
3. Run the downloaded file. On the first screen, **tick "Add python.exe to PATH"** at the bottom **before** clicking Install.

   This single checkbox causes more problems in this course than everything else combined. If you miss it, Windows will not know what `python` means. You can re-run the installer later and choose **Modify** to fix it.
4. Click **Install Now** and wait for it to finish.

### Step 2 — Open the Command Prompt

Press the **Windows key**, type `cmd`, and press Enter. A black window opens. You type commands here and press Enter after each one.

### Step 3 — Check Python is installed

```
python --version
```

You should see `Python 3.12.x` (any 3.10 or newer is fine).

**If the Microsoft Store opens instead**, Windows is intercepting the command because Python isn't properly installed — go back to Step 1 and make sure you tick the PATH box. If you've already done that, see [troubleshooting](#windows-typing-python-opens-the-microsoft-store).

**If you get "not recognized"**, see [troubleshooting](#windows-python-is-not-recognized).

### Step 4 — Create a folder and a virtual environment

A virtual environment is a private space for this course's software, so it can't interfere with anything else on your computer.

```
mkdir %USERPROFILE%\Documents\pyanalytica
cd /d %USERPROFILE%\Documents\pyanalytica
python -m venv .venv
.venv\Scripts\activate.bat
```

After the last command your prompt starts with `(.venv)`. **That prefix means the environment is active** — you need it every time you use PyAnalytica.

### Step 5 — Update pip, then install PyAnalytica

```
python -m pip install --upgrade pip
pip install pyanalytica==0.7.1
```

The first command prevents a family of confusing installation errors. The second downloads roughly 100 MB and takes a few minutes.

You may see yellow warnings about scripts "not on PATH". If your prompt shows `(.venv)`, ignore them — see [troubleshooting](#pyanalytica-is-not-recognized--command-not-found) if the next step fails.

### Step 6 — Start it

```
pyanalytica
```

Your browser opens automatically, and the window shows:

```
PyAnalytica is starting at http://127.0.0.1:8000
Open that address in your browser if it does not open by itself.
Press Ctrl+C in this window to stop.
```

To stop the app, click back on the black window and press **Ctrl+C**.

**The window will fill with technical log lines** — `INFO:` messages, and on a
Mac possibly `Matplotlib is building the font cache`. That is normal output,
not errors. **You know it worked if your browser opens the app.** Leave the
window alone while you work; closing it stops the app.

### Step 7 — Make a one-click launcher

Do this now and you never type those commands again.

**1.** In the Command Prompt, run:

```
notepad %USERPROFILE%\Documents\pyanalytica\start-pyanalytica.bat
```

**2.** Notepad says the file doesn't exist and asks whether to create it. Click **Yes**.

**3.** Copy these lines and paste them into Notepad:

```
@echo off
title PyAnalytica - leave this window open
cd /d %~dp0
call .venv\Scripts\activate.bat
echo.
echo  ---------------------------------------------------------------
echo   This window IS PyAnalytica. Leave it open while you work.
echo   You can minimise it - just do not close it.
echo   When you have finished, close it or press Ctrl+C to stop.
echo  ---------------------------------------------------------------
echo.
pyanalytica
echo.
echo  PyAnalytica has stopped. You can close this window.
pause
```

**4.** Press **Ctrl+S** to save, then close Notepad.

From now on, open **Documents → pyanalytica** and **double-click `start-pyanalytica.bat`**. It opens the window, activates the environment, and starts PyAnalytica by itself.

> Running the `notepad ...` command in step 1 matters: it creates the file with the right name immediately. If you instead open Notepad and use *Save As*, Notepad quietly adds `.txt` to the end and the file will not run.

**Optional — put it on the Desktop and start it minimised.** Right-click
`start-pyanalytica.bat` → **Show more options → Send to → Desktop (create
shortcut)**. Then right-click the new Desktop shortcut → **Properties** → set
**Run:** to **Minimised** → **OK**. Now one click starts PyAnalytica, the black
window goes straight to the taskbar, and your browser is the only thing you see.

---

## Mac

### Step 1 — Install Python

1. Go to **https://www.python.org/downloads/macos/**
2. Under "Stable Releases", find the newest **Python 3.12.x** entry and click **macOS 64-bit universal2 installer**.
3. Open the downloaded `.pkg` file and click through the installer.

### Step 2 — Install Python's security certificates

**Do not skip this.** The macOS installer does not set up SSL certificates, and without them Step 5 fails with a security error that never mentions certificates.

Open **Finder → Applications → Python 3.12**, and double-click **Install Certificates.command**. A window opens, runs for a few seconds, and finishes. Close it.

### Step 3 — Open Terminal

Press **Cmd + Space**, type `terminal`, and press Enter. A window opens where you type commands and press Enter after each one.

### Step 4 — Create a folder and a virtual environment

```bash
mkdir -p ~/Documents/pyanalytica
cd ~/Documents/pyanalytica
python3 -m venv .venv
source .venv/bin/activate
```

After the last command your prompt starts with `(.venv)`. That prefix means the environment is active.

> **`python` vs `python3`.** On a Mac, plain `python` may not exist or may point at an old system version — use **`python3`** for the line above. Once the environment is active, plain `python` and `pip` are correct.

### Step 5 — Update pip, then install PyAnalytica

```bash
python -m pip install --upgrade pip
pip install pyanalytica==0.7.1
```

### Step 6 — Start it

```bash
pyanalytica
```

Your browser opens automatically. To stop the app, click back on the Terminal window and press **Control+C**.

**The window will fill with technical log lines** — `INFO:` messages, and on a
Mac possibly `Matplotlib is building the font cache`. That is normal output,
not errors. **You know it worked if your browser opens the app.** Leave the
window alone while you work; closing it stops the app.

### Step 7 — Make a one-click launcher

**1.** In Terminal, run this to create the file and open it:

```bash
touch ~/Documents/pyanalytica/start-pyanalytica.command
open -e ~/Documents/pyanalytica/start-pyanalytica.command
```

**2.** TextEdit opens. Paste these lines:

```bash
#!/bin/bash
printf '\033]0;PyAnalytica — leave this window open\007'
cd "$(dirname "$0")"
source .venv/bin/activate
echo
echo "  ---------------------------------------------------------------"
echo "   This window IS PyAnalytica. Leave it open while you work."
echo "   You can minimise it — just do not close it."
echo "   When you have finished, press Ctrl+C to stop."
echo "  ---------------------------------------------------------------"
echo
pyanalytica
```

**3.** Save with **Cmd+S** and close TextEdit.

**4.** Back in Terminal, make it runnable — this line is required, and only needed once:

```bash
chmod +x ~/Documents/pyanalytica/start-pyanalytica.command
```

From now on, open **Documents → pyanalytica** in Finder and **double-click `start-pyanalytica.command`**. Terminal opens and starts PyAnalytica by itself.

> The first time you double-click it, macOS may warn that it's from an unidentified developer. Right-click the file, choose **Open**, then **Open** again. You only do this once.

---

## Every time you use PyAnalytica after today

**Double-click your launcher** — `start-pyanalytica.bat` (Windows) or `start-pyanalytica.command` (Mac) in your `Documents/pyanalytica` folder.

If the launcher is missing, these do the same thing:

**Windows (Command Prompt):**

```
cd /d %USERPROFILE%\Documents\pyanalytica
.venv\Scripts\activate.bat
pyanalytica
```

**Mac (Terminal):**

```bash
cd ~/Documents/pyanalytica
source .venv/bin/activate
pyanalytica
```

### About the black window

That window is not a leftover from starting the app — **it is the app**.
PyAnalytica runs a small web server there, and your browser is just the screen
it draws on.

- **Leave it open** for as long as you are working. Minimise it if it is in the
  way.
- **Closing it stops PyAnalytica.** The browser tab will stop responding.
- **To stop deliberately:** close the window, or click it and press **Ctrl+C**.
- If something goes wrong, the explanation is usually in that window — copy the
  text into your email to the course address.

You do not need to type anything into it. It is safe to ignore.

---

## Check your installation worked

First, confirm the version. With the environment active:

```
pyanalytica --version
```

It should print `pyanalytica 0.7.1`.

Then, with the app open in your browser:

1. Go to the **Data** tab. In the **Load** sub-tab, choose the bundled dataset **tips** and load it.
2. Go to the **Visualize** tab, **Distribute** sub-tab. Choose `total_bill`, leave the chart type as histogram, and click **Plot**.
3. You should see a histogram.
4. Click **Show Code** underneath it. You should see the equivalent pandas/seaborn code.

If all four steps work, you're done. **Post a screenshot of your histogram to the course Teams channel** to complete this module.

---

## Troubleshooting

### Start over from scratch

If your environment gets into a confusing state, delete it and rebuild. You lose nothing — the environment holds only installed software, not your work.

**Windows:**

```
cd /d %USERPROFILE%\Documents\pyanalytica
rmdir /s /q .venv
```

**Mac:**

```bash
cd ~/Documents/pyanalytica
rm -rf .venv
```

Then redo Step 4 onwards.

### Windows: typing `python` opens the Microsoft Store

Windows ships a placeholder that opens the Store when Python isn't installed. Installing from python.org with the PATH box ticked normally resolves it.

If it still happens, switch the placeholder off: **Settings → Apps → Advanced app settings → App execution aliases**, and turn **off** `python.exe` and `python3.exe`. Close the Command Prompt, open it again, and retry.

### Windows: "python is not recognized"

The "Add python.exe to PATH" box was not ticked during installation.

**Fix:** re-run the Python installer, choose **Modify**, click Next, tick **Add Python to environment variables**, and click Install. Then close the Command Prompt, open it again, and retry.

### "pyanalytica is not recognized" / "command not found"

Almost always the virtual environment is not active — your prompt is missing the `(.venv)` prefix.

**Fix:** double-click your launcher, or `cd` back into the folder and run the activate line from the section above.

**If you installed without a virtual environment**, you may have seen a yellow warning saying the scripts were installed somewhere "which is not on PATH". That is this problem: the program is installed, but Windows cannot find the name. Either redo Steps 4–5 with the virtual environment, or start it this way, which works regardless of PATH:

```
python -m pyanalytica
```

`python -m pyanalytica --version` and `python -m pyanalytica --port 8001` behave exactly like the short command.

### Mac: "SSL: CERTIFICATE_VERIFY_FAILED" during pip install

You skipped Step 2. Open **Applications → Python 3.12 → Install Certificates.command**, let it finish, then retry the install.

### PowerShell: "cannot be loaded because running scripts is disabled"

This guide uses the Command Prompt (`cmd`), which doesn't have this restriction. If you prefer PowerShell, run this once and then use `.\.venv\Scripts\Activate.ps1` to activate:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### The app started on a strange port number

If you see `Port 8000 was busy, using 61699 instead.`, that's normal — PyAnalytica was already running in another window, so this copy moved to a free port. Use whichever address it printed.

To ask for a specific port:

```
pyanalytica --port 8001
```

### The window is full of INFO messages or warnings

That is the normal running log, not an error. PyAnalytica prints what it is
serving while it runs, and Python libraries occasionally print notices of their
own. **If the app opened in your browser, it is working.**

Errors look different: they stop the app and return you to the prompt. If the
window still says "PyAnalytica is starting" and the browser tab loads, nothing
is wrong.

### The browser shows "can't reach this page"

Check the terminal window. If it isn't showing the "PyAnalytica is starting" banner, the app has stopped — start it again. If it is showing that banner, use the exact address printed there, and note it's `http`, not `https`.

---

## Using UIUC AnyWare instead

**UIUC AnyWare** is a Windows desktop that runs in your browser. You have the rights to install software there, so it solves every case below. Log in at **https://answers.uillinois.edu/illinois/anyware** with your NetID.

Use AnyWare if:

- **Your antivirus blocks the installer or interrupts `pip`.**
- **You are not an administrator** on your computer — a family machine set up under someone else's account, for example.
- **Your Mac is too old** for Python 3.12. Check **Apple menu → About This Mac**.
- **You only have a Chromebook or an iPad.** PyAnalytica needs Windows or macOS, so AnyWare is the answer.

### Setting up on AnyWare

Everything happens *inside* the AnyWare desktop, in your browser.

**Python is already installed there, so skip Step 1.** Follow the **Windows** section from **Step 2** onwards — open the Command Prompt, create the environment, install, and make the launcher in Step 7. It takes about 15 minutes.

### Every session after that

**Double-click `start-pyanalytica.bat`** in your `Documents\pyanalytica` folder. That's the whole routine — this is exactly why Step 7 is worth doing.

### If PyAnalytica is missing when you come back

AnyWare gives you a fresh machine each time. Your Documents folder normally follows you, but if the folder, the launcher, or the installation is gone, redo Steps 4–7 — a few minutes, and nothing you have saved is lost.

**If this happens every single time, email us.** Reinstalling weekly is not something you should put up with, and we will find you a better arrangement.

### Where to save your work on AnyWare

This matters more than the installation, because losing an assignment is worse than losing an install.

- **Save data files and downloads to your Documents folder, OneDrive, or your U: drive** — never to the AnyWare Desktop, and never to `C:\Temp`.
- When PyAnalytica downloads a file — an exported CSV, or your homework submission — **it lands on the AnyWare machine, not on your own computer.**
- **Upload to Canvas from inside AnyWare.** Open a browser tab in the AnyWare desktop, go to Canvas, and upload from there. That's the simplest route and avoids moving files between machines.
- If you want a file on your own computer, put it in OneDrive from inside AnyWare, then open OneDrive on your own machine.

### AnyWare tips

- **Press Ctrl+C in the black window before closing the browser tab**, or the app keeps running in a session you have left.
- AnyWare sessions time out if you leave them idle. Save your work.

---

## Getting help

**Email the course address: uiucbadm576@gmail.com**

Include all four of these — with them, most problems are solved in one reply; without them, the first reply is just us asking for them:

1. Windows, Mac, or AnyWare
2. Which step you were on
3. The command you typed
4. The **complete** error message, copied as text rather than a screenshot

To copy the error: select it in the window, press Ctrl+C (Cmd+C on a Mac), and paste it into the email.

General discussion happens in the course **Microsoft Teams** channel; installation problems go to the email address above so they don't get lost in the chat.
