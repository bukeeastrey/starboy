# Telegram, part 2: setting up and managing games

A transcript from the test run, with Telegram faked. `👤` is a player, `🤖` is the bot, `[ ]` are buttons, `✔` is a check the test made.

```
### Ada sets up a game with buttons

👤 Ada taps ⌨ [⚽ New game]
🤖 ⚽ New game
   Which pitch?
   [Parklane 425921]
   [Other pitch…]
   [✖️ Cancel]
      ✔ asks which pitch

👤 Ada taps [Parklane 425921]
🤖 (edits its message) ⚽ New game
   🏟 Parklane 425921
   
   Which day?
   [Today] [Tomorrow]
   [Sat 10 Oct] [Sun 11 Oct]
   [📆 Pick a date]
   [⬅️ Back] [✖️ Cancel]
      ✔ date choices

👤 Ada taps [📆 Pick a date]
🤖 (edits its message) ⚽ New game
   🏟 Parklane 425921
   
   Pick a date.
   [ ] [October 2026] [›]
   [Mo] [Tu] [We] [Th] [Fr] [Sa] [Su]
   [ ] [ ] [ ] [·] [·] [·] [·]
   [·] [·] [·] [·] [9] [10] [11]
   [12] [13] [14] [15] [16] [17] [18]
   [19] [20] [21] [22] [23] [24] [25]
   [26] [27] [28] [29] [30] [31] [ ]
   [⬅️ Back] [✖️ Cancel]
      ✔ an inline calendar

👤 Ada taps [›]
🤖 (edits its message) ⚽ New game
   🏟 Parklane 425921
   
   Pick a date.
   [‹] [November 2026] [›]
   [Mo] [Tu] [We] [Th] [Fr] [Sa] [Su]
   [ ] [ ] [ ] [ ] [ ] [ ] [1]
   [2] [3] [4] [5] [6] [7] [8]
   [9] [10] [11] [12] [13] [14] [15]
   [16] [17] [18] [19] [20] [21] [22]
   [23] [24] [25] [26] [27] [28] [29]
   [30] [ ] [ ] [ ] [ ] [ ] [ ]
   [⬅️ Back] [✖️ Cancel]

👤 Ada taps [15]
🤖 (edits its message) ⚽ New game
   🏟 Parklane 425921
   🗓 Sun 15 Nov
   
   Kickoff time?
   [7am] [8am] [4pm]
   [5pm] [6pm] [7pm]
   [⌨️ Type a time]
   [⬅️ Back] [✖️ Cancel]
      ✔ time slots

### Meanwhile Bola starts his own game: the two don't mix

👤 Bola taps ⌨ [⚽ New game]
🤖 ⚽ New game
   Which pitch?
   [Parklane 425921]
   [Other pitch…]
   [✖️ Cancel]

👤 Bola taps [Parklane 425921]
🤖 (edits its message) ⚽ New game
   🏟 Parklane 425921
   
   Which day?
   [Today] [Tomorrow]
   [Sat 10 Oct] [Sun 11 Oct]
   [📆 Pick a date]
   [⬅️ Back] [✖️ Cancel]

👤 Bola taps [Tomorrow]
🤖 (edits its message) ⚽ New game
   🏟 Parklane 425921
   🗓 Sat 10 Oct
   
   Kickoff time?
   [7am] [8am] [4pm]
   [5pm] [6pm] [7pm]
   [⌨️ Type a time]
   [⬅️ Back] [✖️ Cancel]

👤 Ada taps [⌨️ Type a time]
🤖 (edits its message) ⚽ New game
   🏟 Parklane 425921
   🗓 Sun 15 Nov
   
   Type the kickoff time, like 5pm, 7:30am or 17:30.
   [⬅️ Back] [✖️ Cancel]

👤 Ada: evening
🤖 I didn't get that time. Try 5pm, 7:30am or 17:30.
   [⬅️ Back] [✖️ Cancel]
      ✔ a bad time is explained

👤 Ada: 5:30pm
🤖 ⚽ New game
   🏟 Parklane 425921
   🗓 Sun 15 Nov, 5:30 pm
   
   How long?
   [60 min] [90 min] [120 min]
   [⬅️ Back] [✖️ Cancel]
      ✔ Ada's wizard kept her own date and time
      ✔ Bola's wizard is still at his time step

👤 Ada taps [90 min]
🤖 (edits its message) ⚽ New game
   🏟 Parklane 425921
   🗓 Sun 15 Nov, 5:30 pm
   ⏱ 90 min
   
   Any note for the crew? Type it (e.g. “Bring white and dark shirts”), or skip.
   [Skip]
   [⬅️ Back] [✖️ Cancel]

👤 Ada: Bring white and dark shirts
🤖 ⚽ New game
   🏟 Parklane 425921
   🗓 Sun 15 Nov, 5:30 pm
   ⏱ 90 min
   📝 Bring white and dark shirts
   
   Who are you inviting? Tap to tick. (0 of 2)
   [⬜ Bola] [⬜ Chidi]
   [Select all] [Done ➡️]
   [⬅️ Back] [✖️ Cancel]
      ✔ invite checklist of the pitch's players

👤 Ada taps [⬜ Bola]
🤖 (edits its message) ⚽ New game
   🏟 Parklane 425921
   🗓 Sun 15 Nov, 5:30 pm
   ⏱ 90 min
   📝 Bring white and dark shirts
   
   Who are you inviting? Tap to tick. (1 of 2)
   [✅ Bola] [⬜ Chidi]
   [Select all] [Done ➡️]
   [⬅️ Back] [✖️ Cancel]
      ✔ tapping ticks

👤 Ada taps [Select all]
🤖 (edits its message) ⚽ New game
   🏟 Parklane 425921
   🗓 Sun 15 Nov, 5:30 pm
   ⏱ 90 min
   📝 Bring white and dark shirts
   
   Who are you inviting? Tap to tick. (2 of 2)
   [✅ Bola] [✅ Chidi]
   [Select all] [Done ➡️]
   [⬅️ Back] [✖️ Cancel]

👤 Ada taps [Done ➡️]
🤖 (edits its message) ⚽ New game
   🏟 Parklane 425921
   🗓 Sun 15 Nov, 5:30 pm
   ⏱ 90 min
   📝 Bring white and dark shirts
   
   Inviting 2 players.
   
   All correct?
   [Create ✅] [Start over ↩️]
   [⬅️ Back] [✖️ Cancel]
      ✔ summary

👤 Ada taps [⬅️ Back]
🤖 (edits its message) ⚽ New game
   🏟 Parklane 425921
   🗓 Sun 15 Nov, 5:30 pm
   ⏱ 90 min
   📝 Bring white and dark shirts
   
   Who are you inviting? Tap to tick. (2 of 2)
   [✅ Bola] [✅ Chidi]
   [Select all] [Done ➡️]
   [⬅️ Back] [✖️ Cancel]
      ✔ Back returns to the checklist

👤 Ada taps [Done ➡️]
🤖 (edits its message) ⚽ New game
   🏟 Parklane 425921
   🗓 Sun 15 Nov, 5:30 pm
   ⏱ 90 min
   📝 Bring white and dark shirts
   
   Inviting 2 players.
   
   All correct?
   [Create ✅] [Start over ↩️]
   [⬅️ Back] [✖️ Cancel]

👤 Ada taps [Create ✅]
🤖 (edits its message) ✅ Game set!
   🏟 Parklane 425921
   🗓 Sun 15 Nov, 5:30 pm
   
   Invites sent to 2 players. Now tell the crew.
   [📲 Share in the WhatsApp group]
   [Open game]
   [📅 Manage this game]
🤖 [sends a picture] Your matchday poster. Post it on your Status. 📣
   (pop-up: Game set ✅)
🤖 ⚽ Ada invited you to football at Parklane 425921, Sun 15 Nov, 5:30 pm.
   📝 Bring white and dark shirts
   
   You dey come?
   [I'm in ✅] [Can't make it ❌]
   [Open game]
🤖 ⚽ Ada invited you to football at Parklane 425921, Sun 15 Nov, 5:30 pm.
   📝 Bring white and dark shirts
   
   You dey come?
   [I'm in ✅] [Can't make it ❌]
   [Open game]
      ✔ game created with the right details
      ✔ share link + manage button
      ✔ the matchday poster arrives as a picture
      ✔ Bola and Chidi got the invite
      ✔ the wizard is over

### A menu button always leaves a flow

👤 Bola taps ⌨ [📅 My games]
🤖 📅 My games
   ✅ you're in · ❓ not answered · 🏁 played
   Tap a game.
   [❓ Sun 15 Nov, 5:30 pm · Parklane 425921]
   [⚽ New game]
      ✔ Bola's half-made game is dropped

### My games: answer, invite more, cancel
      ✔ the invite shows as not answered

👤 Bola taps [❓ Sun 15 Nov, 5:30 pm · Parklane 425921]
🤖 (edits its message) 🏟 Parklane 425921
   🗓 Sun 15 Nov, 5:30 pm · 90 min
   📝 Bring white and dark shirts
   
   ✅ In (1) Ada
   ❌ Out (0) nobody
   ❓ No answer (2) Bola, Chidi
   [I'm in ✅] [Can't make it ❌]
   [➕ Invite more]
   [Open game]
   [⬅️ My games]
      ✔ game view lists in / out / no answer

👤 Bola taps [I'm in ✅]
🤖 (edits its message) 🏟 Parklane 425921
   🗓 Sun 15 Nov, 5:30 pm · 90 min
   📝 Bring white and dark shirts
   
   ✅ In (2) Ada, Bola
   ❌ Out (0) nobody
   ❓ No answer (1) Chidi
   [I'm in ✅ ·] [Can't make it ❌]
   [➕ Invite more]
   [Open game]
   [⬅️ My games]
   (pop-up: You're in ✅)
      ✔ RSVP from the game view

👤 Ada taps [📅 Manage this game]
🤖 (edits its message) 🏟 Parklane 425921
   🗓 Sun 15 Nov, 5:30 pm · 90 min
   📝 Bring white and dark shirts
   
   ✅ In (2) Ada, Bola
   ❌ Out (0) nobody
   ❓ No answer (1) Chidi
   [I'm in ✅ ·] [Can't make it ❌]
   [➕ Invite more]
   [🗑 Cancel game]
   [Open game]
   [⬅️ My games]

👤 Ada taps [➕ Invite more]
🤖 (edits its message) ➕ Invite more
   Tap to tick. (0 chosen)
   [⬜ Dele]
   [Send invites ➡️]
   [⬅️ Back] [✖️ Cancel]
      ✔ only players not yet invited are offered

👤 Ada taps [⬜ Dele]
🤖 (edits its message) ➕ Invite more
   Tap to tick. (1 chosen)
   [✅ Dele]
   [Send invites ➡️]
   [⬅️ Back] [✖️ Cancel]

👤 Ada taps [Send invites ➡️]
🤖 ⚽ Ada invited you to football at Parklane 425921, Sun 15 Nov, 5:30 pm.
   📝 Bring white and dark shirts
   
   You dey come?
   [I'm in ✅] [Can't make it ❌]
   [Open game]
🤖 (edits its message) 🏟 Parklane 425921
   🗓 Sun 15 Nov, 5:30 pm · 90 min
   📝 Bring white and dark shirts
   
   ✅ In (2) Ada, Bola
   ❌ Out (0) nobody
   ❓ No answer (2) Chidi, Dele
   
   📨 Invited 1 more player.
   [I'm in ✅ ·] [Can't make it ❌]
   [➕ Invite more]
   [🗑 Cancel game]
   [Open game]
   [⬅️ My games]
   (pop-up: Invites sent ✅)
      ✔ Dele is invited

👤 Bola taps [⬅️ My games]
🤖 (edits its message) 📅 My games
   ✅ you're in · ❓ not answered · 🏁 played
   Tap a game.
   [✅ Sun 15 Nov, 5:30 pm · Parklane 425921]
   [⚽ New game]
      ✔ Bola can't cancel someone else's game

👤 Ada taps [🗑 Cancel game]
🤖 (edits its message) Cancel the game at Parklane 425921, Sun 15 Nov, 5:30 pm?
   Everyone who is in will be told.
   [Yes, cancel it 🗑]
   [No, keep it]
      ✔ cancelling asks first

👤 Ada taps [No, keep it]
🤖 (edits its message) 🏟 Parklane 425921
   🗓 Sun 15 Nov, 5:30 pm · 90 min
   📝 Bring white and dark shirts
   
   ✅ In (2) Ada, Bola
   ❌ Out (0) nobody
   ❓ No answer (2) Chidi, Dele
   [I'm in ✅ ·] [Can't make it ❌]
   [➕ Invite more]
   [🗑 Cancel game]
   [Open game]
   [⬅️ My games]
      ✔ No keeps it

👤 Ada taps [🗑 Cancel game]
🤖 (edits its message) Cancel the game at Parklane 425921, Sun 15 Nov, 5:30 pm?
   Everyone who is in will be told.
   [Yes, cancel it 🗑]
   [No, keep it]

👤 Ada taps [Yes, cancel it 🗑]
🤖 ❌ The game at Parklane 425921 on Sun 15 Nov, 5:30 pm was cancelled.
🤖 ❌ The game at Parklane 425921 on Sun 15 Nov, 5:30 pm was cancelled.
🤖 (edits its message) 🏟 Parklane 425921
   🗓 Sun 15 Nov, 5:30 pm · 90 min
   📝 Bring white and dark shirts
   
   ✖️ This game was cancelled.
   
   ✅ In (2) Ada, Bola
   ❌ Out (0) nobody
   ❓ No answer (2) Chidi, Dele
   [Open game]
   [⬅️ My games]
   (pop-up: Game cancelled.)
      ✔ cancelled, and Bola (who was in) is told

### After a game: score, stats and photos from My games

👤 Ada taps ⌨ [📅 My games]
🤖 📅 My games
   ✅ you're in · ❓ not answered · 🏁 played
   Tap a game.
   [🏁 Fri 9 Oct, 12:11 pm · Parklane 425921]
   [⚽ New game]

👤 Ada taps [🏁 Fri 9 Oct, 12:11 pm · Parklane 425921]
🤖 (edits its message) 🏟 Parklane 425921
   🗓 Fri 9 Oct, 12:11 pm · 90 min
   
   🏁 Full time. Score not in yet.
   
   ✅ In (3) Ada, Bola, Chidi
   ❌ Out (0) nobody
   ❓ No answer (0) nobody
   [📋 Report my stats] [📸 Add photos]
   [🏁 Enter final score + sides]
   [Open game]
   [⬅️ My games]
      ✔ a played game offers score, stats, photos

👤 Ada taps [🏁 Enter final score + sides]
🤖 What was the final score at Parklane 425921?
   Reply like 5-3, your side first. Then I'll ask who was on your side.
   [✖️ Cancel]

👤 Ada: 5-3
🤖 Final score: 5–3 (your side first).
   Who was on your side? Tap to tick, then Done.
   [☐ Bola] [☐ Chidi]
   [Done ✅]

👤 Ada taps [☐ Bola]
🤖 (edits its message) Final score: 5–3 (your side first).
   Who was on your side? Tap to tick, then Done.
   [☑ Bola] [☐ Chidi]
   [Done ✅]

👤 Ada taps [Done ✅]
🤖 (edits its message) Final score saved: 5–3 ✅
   [Open game]
   (pop-up: Saved ✅)
      ✔ final score and sides saved

👤 Ada taps ⌨ [📅 My games]
🤖 📅 My games
   ✅ you're in · ❓ not answered · 🏁 played
   Tap a game.
   [🏁 Fri 9 Oct, 12:11 pm · Parklane 425921]
   [⚽ New game]

👤 Ada taps [🏁 Fri 9 Oct, 12:11 pm · Parklane 425921]
🤖 (edits its message) 🏟 Parklane 425921
   🗓 Fri 9 Oct, 12:11 pm · 90 min
   
   🏁 Final score: 5–3
   
   ✅ In (3) Ada, Bola, Chidi
   ❌ Out (0) nobody
   ❓ No answer (0) nobody
   [📋 Report my stats] [📸 Add photos]
   [🏁 Enter final score + sides]
   [Open game]
   [⬅️ My games]

👤 Ada taps [📸 Add photos]
🤖 📸 Send me your photos from Parklane 425921 now. They go straight into that game's gallery.
   [Done]

👤 Ada: [sends a photo]
🤖 Added to the gallery for Parklane 425921, Fri 9 Oct, 12:11 pm.
   [Open game]
      ✔ the photo goes into that game's gallery

👤 Ada taps [Done]
🤖 (edits its message) Done. 👍

👤 Ada taps ⌨ [📅 My games]
🤖 📅 My games
   ✅ you're in · ❓ not answered · 🏁 played
   Tap a game.
   [🏁 Fri 9 Oct, 12:11 pm · Parklane 425921]
   [⚽ New game]

👤 Ada taps [🏁 Fri 9 Oct, 12:11 pm · Parklane 425921]
🤖 (edits its message) 🏟 Parklane 425921
   🗓 Fri 9 Oct, 12:11 pm · 90 min
   
   🏁 Final score: 5–3
   
   ✅ In (3) Ada, Bola, Chidi
   ❌ Out (0) nobody
   ❓ No answer (0) nobody
   [📋 Report my stats] [📸 Add photos]
   [🏁 Enter final score + sides]
   [Open game]
   [⬅️ My games]

👤 Ada taps [📋 Report my stats]
🤖 How was your game at Parklane 425921 today? ⚽
   [Tap my stats 📋]
   [Send a voice note 🎙️]
      ✔ report offers tap or voice

### A wizard left for 30 minutes

👤 Chidi taps ⌨ [⚽ New game]
🤖 ⚽ New game
   Which pitch?
   [Parklane 425921]
   [Other pitch…]
   [✖️ Cancel]

👤 Chidi taps [Parklane 425921]
🤖 (edits its message) ⌛ That one sat for a while, so I closed it. Tap a menu button to start again.
      ✔ expired wizard says so kindly

```
