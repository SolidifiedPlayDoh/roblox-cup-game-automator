# Cup Guard

i made an entire desktop application for one roblox mini-game.

that's it. that's the project.

<p align="center">
  <a href="https://www.roblox.com/games/127017819698509/Dont-Ring-the-Bell">
    <img src="docs/roblox-game.png" alt="Don't Ring the Bell on Roblox" width="180">
  </a>
  <br>
  <strong><a href="https://www.roblox.com/games/127017819698509/Dont-Ring-the-Bell">[☀️] Don't Ring the Bell! 🔔</a></strong>
  <br>
  <sub>by Screaming Chicken Studios · click to play</sub>
</p>

you sit at a table. there's a red cup. sometimes it moves. if you react too slow you lose. i wanted to cheat because i can :3

<p align="center">
  <img src="docs/hero.png" alt="cup guard running over roblox" width="100%">
</p>

## demo

one full round with cup guard running.

<p align="center">
  <video src="https://github.com/SolidifiedPlayDoh/roblox-cup-game-automator/releases/download/demo-v1/demo.mp4" controls playsinline width="100%">
    <a href="https://github.com/SolidifiedPlayDoh/roblox-cup-game-automator/releases/download/demo-v1/demo.mp4">watch the demo</a>
  </video>
</p>

## what it does

- watches a tiny strip of pixels on the red cup rim (not the whole screen that would be slow)
- when the cup leaves your spot, it presses **E** (the don't ring button)
- then presses Q after a random 2.5–4 second delay.if the timing were 0 or a fixed amount of time after E. the other player starts waiting for that. random delay makes you harder to sit on. (i swear people mentally anchor around like ~6 seconds in this game when they're trying to predict you. might just be me. might be all of us.. idk)
- little overlay in the top right so you can see it and stuff

## how to use

1. open [the game](https://www.roblox.com/games/127017819698509/Dont-Ring-the-Bell)
2. run cup guard so its ready
3. sit at the table in the game with another player
5. put your mouse on the **bottom rim** of the red cup (press "Need Help?" in the app if confused)
6. press **`0`**
7. green box in the preview = you're locked on. status says CUP ON. now you can sit back and watch yourself win without actualy doing anything! congrats. you are now watching a video game. great use of time (do the dishes) :3

press **`0`** again anytime to recalibrate. moved seats? (the lighting in the game requires you to recalibrate every time you move seats). camera weird? press 0. it's fine.

stuck? hit **Need help?** in the overlay. i included screenshots because i care about u <3

## permissions (sorry)

| platform | what it needs | why |
|----------|---------------|-----|
| macOS | Screen Recording | to look at the cup |
| macOS | Accessibility | to fake key presses |
| Windows | screen capture privacy | same deal |

give permissions to Cup Guard, or Terminal/Cursor if you're running from source. restart after. macOS will fight you on this because apple hates fun.

## download! (simple :3)

one click:

- [macOS](https://github.com/SolidifiedPlayDoh/roblox-cup-game-automator/releases/download/v1.1.0/CupGuard-macOS-arm64.zip) — `CupGuard.app` in a zip
- [Windows](https://github.com/SolidifiedPlayDoh/roblox-cup-game-automator/releases/download/v1.1.0/CupGuard.exe)

more releases on [GitHub](https://github.com/SolidifiedPlayDoh/roblox-cup-game-automator/releases) if you want older builds or whatever (not like they are gonna be more than a day old if that)

## faq

### is this against roblox TOS?

not in the "hacking" sense. it doesn't inject into roblox, read memory, or modify the client. it literally just looks at your screen and presses keys like your fingers would.

is it automation? yes. could roblox hypothetically have feelings about that? also yes. (rarely though. youll be fine) their rules are vague idk.

### will i get banned

it's not an exploit. it's not a cheat engine. it's a python script that learned what red pixels look like.

nobody can promise you zero risk with any third party tool ever. but this is the same category as "macro keyboard" not "Roblox Executor"

### does it work against skilled players

that was the whole point. high level players are fast. i am... not. cup guard watches every frame and hits E before my brain finishes forming a thought. (rare occasion)

the Q delay is randomized on purpose so you don't press Q at the exact same millisecond every time like a robot. because you aren't a robot. cup guard is, but we don't talk about that.

### why does it sample above the cursor

because if you hover ON the red rim your mouse covers the red. then the app thinks the cup is gone. then it spams E. then you lose anyway. learned that one the hard way.

so it samples 12px above your cursor. hover the bottom rim, press 0, trust the process.

### what if screen capture is blank/white on mac

screen recording permission. system settings → privacy → screen recording → enable the app. restart cup guard :3

### does this work on other games

no. please no. this is tuned for a red cup in one roblox game. if you point this at league of legends i don't want to know what happens. 

### can i turn off auto E or auto Q

yes. toggles in the overlay. you can also just use it as a fancy red pixel detector and press keys yourself like a caveman.

## overlay controls

| thing | does what |
|-------|-----------|
| Arm (0) | calibrate + start |
| Monitoring | pause/resume |
| Auto-press E | yeet E when cup moves |
| Auto-press Q | Q after E, with delay |
| Sensitivity | lower = triggers sooner |
| Need help? | pictures for confused people (me) |

## install (from source) (elite nerd mode (epic))

you need python 3.11+ and [uv](https://docs.astral.sh/uv/) because i have standards (barely).

```bash
git clone https://github.com/SolidifiedPlayDoh/roblox-cup-game-automator.git
cd roblox-cup-game-automator
uv venv
uv pip install -e .
./run.sh
```

cli mode if you hate GUIs:

```bash
uv run cup-guard start
```
## build it yourself

```bash
uv pip install pyinstaller
uv run pyinstaller CupGuard.spec --noconfirm      # macOS
uv run pyinstaller CupGuard-win.spec --noconfirm  # Windows
```

output in `dist/`. config saves to:

- macOS: `~/Library/Application Support/CupGuard/`
- Windows: `%APPDATA%\CupGuard\`

## cli commands

```bash
cup-guard              # overlay (default)
cup-guard start        # terminal mode
cup-guard calibrate    # countdown calibrate
cup-guard preview      # stats in terminal
cup-guard test-capture # "is macOS blocking me" diagnostic
```

## license

[MIT](LICENSE). it is what it is.

no warranty. no support. no promises. the software is provided "as is" and if something breaks, that's life. (but i might fix it in new release)

if roblox (or anyone else) bans you, or sends you to gamer jail for using this, that's your fault not mine. you chose to automate a cup game. i can't stop you from making decisions. you can give a horse to a drink but you cant make it water

if this gets you to champion rank. nice. but tell noone. 
