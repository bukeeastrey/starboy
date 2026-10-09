# Telegram, part 1: sign-up, main menu, magic link

A transcript from the test run, with Telegram faked. `👤` is a player, `🤖` is the bot, `[ ]` are buttons, `✔` is a check the test made.

```
### A new player signs up without leaving Telegram

👤 Tunde: /start
🤖 Welcome to Star Boy ⭐
   Pickup football at your pitch: who's in, when's kickoff, and who really scored.
   
   I'll put you down as Tunde Bello.
   [Use this ✅] [Change ✏️]
   [✖️ Cancel]
      ✔ offers the Telegram name

👤 Tunde taps [Use this ✅]
🤖 (edits its message) Nice one, Tunde Bello.
   
   Wetin dem dey call you for pitch? Type your nickname, or skip.
   [Skip]
   [⬅️ Back] [✖️ Cancel]

👤 Tunde: TB
🤖 Where do you like to play?
   [GK] [DEF] [MID] [FWD]
   [Anywhere]
   [⬅️ Back] [✖️ Cancel]
      ✔ asks position with buttons

👤 Tunde taps [FWD]
🤖 (edits its message) Position: FWD
🤖 Last one. Share your number so friends who have it can find you here. It stays private: other players never see it. Or skip.
   ⌨ under the chat box: Share my number 📱 | Skip | ⬅️ Back · ✖️ Cancel

👤 Tunde: [shares their phone number]
🤖 You're in, TB! ⚽
   
   Start with 🏟 Pitches to find where your people play, or ⚽ New game to set one up. The buttons below do everything.
   ⌨ under the chat box: ⚽ New game · 📅 My games | 🏟 Pitches · 🏆 Leaderboards | 📋 Report a game · ⚖️ Settle it | 👤 My card · 🌐 Open Star Boy
      ✔ account created and linked, no PIN
      ✔ main menu is under the chat box

### Changing the name, skipping the rest, using Back

👤 Ada: hello
🤖 Welcome to Star Boy ⭐
   Pickup football at your pitch: who's in, when's kickoff, and who really scored.
   
   I'll put you down as Ada.
   [Use this ✅] [Change ✏️]
   [✖️ Cancel]

👤 Ada taps [Change ✏️]
🤖 (edits its message) No wahala. Type your name.
   [⬅️ Back] [✖️ Cancel]

👤 Ada: Adaeze Nwosu
🤖 Nice one, Adaeze Nwosu.
   
   Wetin dem dey call you for pitch? Type your nickname, or skip.
   [Skip]
   [⬅️ Back] [✖️ Cancel]

👤 Ada taps [⬅️ Back]
🤖 (edits its message) No wahala. Type your name.
   [⬅️ Back] [✖️ Cancel]
      ✔ Back returns to the name question

👤 Ada: Adaeze N
🤖 Nice one, Adaeze N.
   
   Wetin dem dey call you for pitch? Type your nickname, or skip.
   [Skip]
   [⬅️ Back] [✖️ Cancel]

👤 Ada taps [Skip]
🤖 (edits its message) Where do you like to play?
   [GK] [DEF] [MID] [FWD]
   [Anywhere]
   [⬅️ Back] [✖️ Cancel]

👤 Ada taps [Anywhere]
🤖 (edits its message) Position: Anywhere
🤖 Last one. Share your number so friends who have it can find you here. It stays private: other players never see it. Or skip.
   ⌨ under the chat box: Share my number 📱 | Skip | ⬅️ Back · ✖️ Cancel

👤 Ada: [shares their phone number]
🤖 Use the Share my number 📱 button to share your own number.
      ✔ someone else's contact is refused

👤 Ada taps ⌨ [Skip]
🤖 You're in, Adaeze! ⚽
   
   Start with 🏟 Pitches to find where your people play, or ⚽ New game to set one up. The buttons below do everything.
   ⌨ under the chat box: ⚽ New game · 📅 My games | 🏟 Pitches · 🏆 Leaderboards | 📋 Report a game · ⚖️ Settle it | 👤 My card · 🌐 Open Star Boy
      ✔ account without a phone number

👤 Kemi: /start
🤖 Welcome to Star Boy ⭐
   Pickup football at your pitch: who's in, when's kickoff, and who really scored.
   
   I'll put you down as Kemi Ojo.
   [Use this ✅] [Change ✏️]
   [✖️ Cancel]

👤 Kemi taps [Use this ✅]
🤖 (edits its message) Nice one, Kemi Ojo.
   
   Wetin dem dey call you for pitch? Type your nickname, or skip.
   [Skip]
   [⬅️ Back] [✖️ Cancel]

👤 Kemi taps [Skip]
🤖 (edits its message) Where do you like to play?
   [GK] [DEF] [MID] [FWD]
   [Anywhere]
   [⬅️ Back] [✖️ Cancel]

👤 Kemi taps [MID]
🤖 (edits its message) Position: MID
🤖 Last one. Share your number so friends who have it can find you here. It stays private: other players never see it. Or skip.
   ⌨ under the chat box: Share my number 📱 | Skip | ⬅️ Back · ✖️ Cancel

👤 Kemi taps ⌨ [Skip]
🤖 You're in, Kemi! ⚽
   
   Start with 🏟 Pitches to find where your people play, or ⚽ New game to set one up. The buttons below do everything.
   ⌨ under the chat box: ⚽ New game · 📅 My games | 🏟 Pitches · 🏆 Leaderboards | 📋 Report a game · ⚖️ Settle it | 👤 My card · 🌐 Open Star Boy
      ✔ a second phone-less account is fine too

### Someone who already joined on the website shares the same number

👤 Bukee: /start
🤖 Welcome to Star Boy ⭐
   Pickup football at your pitch: who's in, when's kickoff, and who really scored.
   
   I'll put you down as Bukee.
   [Use this ✅] [Change ✏️]
   [✖️ Cancel]

👤 Bukee taps [Use this ✅]
🤖 (edits its message) Nice one, Bukee.
   
   Wetin dem dey call you for pitch? Type your nickname, or skip.
   [Skip]
   [⬅️ Back] [✖️ Cancel]

👤 Bukee taps [Skip]
🤖 (edits its message) Where do you like to play?
   [GK] [DEF] [MID] [FWD]
   [Anywhere]
   [⬅️ Back] [✖️ Cancel]

👤 Bukee taps [DEF]
🤖 (edits its message) Position: DEF
🤖 Last one. Share your number so friends who have it can find you here. It stays private: other players never see it. Or skip.
   ⌨ under the chat box: Share my number 📱 | Skip | ⬅️ Back · ✖️ Cancel

👤 Bukee: [shares their phone number]
🤖 Welcome back, Bukee! I found your Star Boy account and connected it. The buttons below do everything. ⚽
   ⌨ under the chat box: ⚽ New game · 📅 My games | 🏟 Pitches · 🏆 Leaderboards | 📋 Report a game · ⚖️ Settle it | 👤 My card · 🌐 Open Star Boy
      ✔ the web account is connected, not duplicated

### The menu, and the one-time link into the website

👤 Tunde taps ⌨ [🌐 Open Star Boy]
🤖 Your door into Star Boy, TB. It opens once and closes in 10 minutes.
   [🌐 Open Star Boy]

👤 Tunde taps [🌐 Open Star Boy]
   (opens https://starboy.example/api/auth/magic?token=pe2wuGPWtWiRCwAZz4qwi07rq)
      ✔ magic link: for this player, 10 minutes

👤 Tunde: /menu
🤖 Here's the menu. 👇
   ⌨ under the chat box: ⚽ New game · 📅 My games | 🏟 Pitches · 🏆 Leaderboards | 📋 Report a game · ⚖️ Settle it | 👤 My card · 🌐 Open Star Boy

👤 Tunde: /help
🤖 Star Boy ⭐ gets you out of your room and onto the pitch.
   
   Use the buttons under the chat box:
   ⚽ set up a game · 📅 your games
   🏟 pitches · 🏆 leaderboards
   📋 report a game · ⚖️ settle an argument
   👤 your player card · 🌐 the full app
   
   After a game, send me a voice note about how you played, or a photo for the match gallery.
   ⌨ under the chat box: ⚽ New game · 📅 My games | 🏟 Pitches · 🏆 Leaderboards | 📋 Report a game · ⚖️ Settle it | 👤 My card · 🌐 Open Star Boy
      ✔ help lists the buttons

### Cancel, and a flow left for more than 30 minutes

👤 Late: /start
🤖 Welcome to Star Boy ⭐
   Pickup football at your pitch: who's in, when's kickoff, and who really scored.
   
   I'll put you down as Late Comer.
   [Use this ✅] [Change ✏️]
   [✖️ Cancel]

👤 Late taps [✖️ Cancel]
🤖 (edits its message) Cancelled. 👍
      ✔ cancel leaves cleanly

👤 Late: /start
🤖 Welcome to Star Boy ⭐
   Pickup football at your pitch: who's in, when's kickoff, and who really scored.
   
   I'll put you down as Late Comer.
   [Use this ✅] [Change ✏️]
   [✖️ Cancel]

👤 Late taps [Use this ✅]
🤖 (edits its message) ⌛ That one sat for a while, so I closed it. Tap a menu button to start again.
   Send /start to begin.
      ✔ an expired sign-up says so kindly
      ✔ magic link signs in and redirects
      ✔ signed in as Tunde
      ✔ the link works only once
      ✔ a Telegram account can't sign in with a PIN

```
