# Before you start (participants)

You do **not** need to know how to program. You need:

1. A **Windows laptop**
2. **Cursor** (free editor with AI built in) — [cursor.com](https://cursor.com), or any chat AI that can edit files in a folder
3. This **`robot`** folder on your computer (from the host)
4. Optional: a **Coralboard** with **Sensor HAT** plugged in (camera, mic, buzzer, colored lights)

## What you are building

A small robot personality named **Gemy** on a Synaptics Coralboard:

- Say **“Gemy”** → special hello beep and lights  
- Say **hello** or **wave** → friendly double beep  
- Say something **funny** → rainbow + silly beeps  
- Say something **nice** → happy green/blue lights  
- Say something **mean** → sad beep + red light  
- Say anything else → one short beep + blue light  

## Words you will hear (simple meanings)

| Word | Meaning |
|------|---------|
| **Board** | The Coralboard computer (Linux inside, no screen required) |
| **HAT** | The add-on with camera, microphone, buzzer, and LEDs |
| **ADB** | A cable tool that lets your laptop talk to the board |
| **Script / file** | Instructions the board or PC runs — the AI will write these for you |
| **Prompt** | The sentence you paste into the AI to ask for the next step |
| **Push** | Send a file from your laptop to the board |

## Open the project in Cursor

1. Install Cursor if you have not already.  
2. **File → Open Folder** → choose the `robot` folder.  
3. Open the AI chat (usually on the right).  
4. Tell the AI: *“Read docs/lab/ai-prompt-walkthrough/02-prompt-journey.md and help me do Step 1.”*

Or follow the host and paste each prompt from [02-prompt-journey.md](02-prompt-journey.md).

## If you do not have a board

You can still do **early steps** on your laptop (folder structure, reading prompts). Steps that say **Try it on the board** need hardware — pair with someone who has a board or watch the demo screen.

## Safety / annoyance

- The **buzzer can be loud**. The host will show how to turn it off.  
- If the buzzer will not stop: ask the AI to run `python3 /home/root/hat.py buzzer off` on the board, or press **STOP** in the HAT test window.

Ready? Go to [02-prompt-journey.md](02-prompt-journey.md) **Step 1**.
