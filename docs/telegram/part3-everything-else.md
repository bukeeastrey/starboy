# Telegram, part 3: pitches, leaderboards, Settle it, the card, reporting

A transcript from the test run, with Telegram faked (and Gemma faked for the verdict). `👤` is a player, `🤖` is the bot, `[ ]` are buttons, `✔` is a check the test made.

```
Gemma's text failed the checks (attempt 1). Invented numbers: [5.0]
Gemma's text failed the checks (attempt 2). Invented numbers: [5.0]
### Adding a pitch, with a shared location

👤 Ada taps ⌨ [🏟 Pitches]
🤖 🏟 Pitches
   ✓ = you're registered there. Tap one.
   [Estate Field]
   [M2 Pitch 7333]
   [M3 Pitch 4314]
   [M3 Pitch 4837]
   [M3 Pitch 4997]
   [M4 Pitch 5574]
   [Open Test Pitch 30778]
   [Open Test Pitch 3876]
   [Open Test Pitch 47815]
   [P1W Pitch 7060]
   [P2 Pitch 1297]
   [Parklane 967825]
   [Parklane Football Pitch]
   [Photo Pitch 1346]
   [Photo Pitch 6635]
   [School Pitch]
   [Star Boy Demo Pitch]
   [Test Pitch]
   [Unity Field 254641]
   [Unity Field 747336]
   [➕ Add a pitch]

👤 Ada taps [➕ Add a pitch]
🤖 (edits its message) ➕ Add a pitch
   What do people call it? Type the name.
   [✖️ Cancel]

👤 Ada: ab
🤖 Give it a name of at least 3 letters.
      ✔ too-short name is refused

👤 Ada: Unity Field 160286
🤖 ➕ Unity Field 160286
   Where is it? Type the area or a landmark, or skip.
   [Skip]
   [⬅️ Back] [✖️ Cancel]

👤 Ada: Behind the big mango tree
🤖 ➕ Unity Field 160286
   Are you at the pitch now? Share your location so people can find it. Or skip.
   ⌨ under the chat box: Share location 📍 | Skip | ⬅️ Back · ✖️ Cancel

👤 Ada taps [⬅️ Back]
🤖 (edits its message) ➕ Unity Field 160286
   Where is it? Type the area or a landmark, or skip.
   [Skip]
   [⬅️ Back] [✖️ Cancel]
      ✔ Back returns to the area question

👤 Ada: Behind the mango tree
🤖 ➕ Unity Field 160286
   Are you at the pitch now? Share your location so people can find it. Or skip.
   ⌨ under the chat box: Share location 📍 | Skip | ⬅️ Back · ✖️ Cancel

👤 Ada: [shares a location]
🤖 ✅ Unity Field 160286 is on Star Boy, and you're registered there.
   ⌨ under the chat box: ⚽ New game · 📅 My games | 🏟 Pitches · 🏆 Leaderboards | 📋 Report a game · ⚖️ Settle it | 👤 My card · 🌐 Open Star Boy
🤖 [sends a picture] 🏟 Unity Field 160286
   Behind the mango tree
   1 player · you're registered ✓
   
   ⚽ No game set yet.
   [👥 Players] [🏆 Leaderboards]
   [⚽ New game here]
   [📍 Map]
   [Open on web]
   [⬅️ All pitches]
      ✔ pitch created with a map link, creator registered
      ✔ pitch view is a picture with buttons
      ✔ the main menu is back under the chat box

### Bola finds the pitch and registers

👤 Bola taps ⌨ [🏟 Pitches]
🤖 🏟 Pitches
   ✓ = you're registered there. Tap one.
   [Estate Field]
   [M2 Pitch 7333]
   [M3 Pitch 4314]
   [M3 Pitch 4837]
   [M3 Pitch 4997]
   [M4 Pitch 5574]
   [Open Test Pitch 30778]
   [Open Test Pitch 3876]
   [Open Test Pitch 47815]
   [P1W Pitch 7060]
   [P2 Pitch 1297]
   [Parklane 967825]
   [Parklane Football Pitch]
   [Photo Pitch 1346]
   [Photo Pitch 6635]
   [School Pitch]
   [Star Boy Demo Pitch]
   [Test Pitch]
   [Unity Field 160286]
   [Unity Field 254641]
   [➕ Add a pitch]

👤 Bola taps [Unity Field 160286]
🤖 [sends a picture] 🏟 Unity Field 160286
   Behind the mango tree
   1 player
   
   ⚽ No game set yet.
   [✅ Register here]
   [👥 Players] [🏆 Leaderboards]
   [⚽ New game here]
   [📍 Map]
   [Open on web]
   [⬅️ All pitches]

👤 Bola taps [✅ Register here]
🤖 [sends a picture] 🏟 Unity Field 160286
   Behind the mango tree
   2 players · you're registered ✓
   
   ⚽ No game set yet.
   [👥 Players] [🏆 Leaderboards]
   [⚽ New game here]
   [📍 Map]
   [Open on web]
   [⬅️ All pitches]
   (pop-up: You're registered at Unity Field 160286 ✅)
      ✔ registered from the pitch view

👤 Bola taps [⚽ New game here]
🤖 ⚽ New game
   🏟 Unity Field 160286
   
   Which day?
   [Today] [Tomorrow]
   [Sat 10 Oct] [Sun 11 Oct]
   [📆 Pick a date]
   [⬅️ Back] [✖️ Cancel]
      ✔ New game here skips the pitch question

👤 Bola taps [✖️ Cancel]
🤖 (edits its message) Cancelled. 👍

### Leaderboards as a table

👤 Ada taps [🏆 Leaderboards]
🤖 (edits its message) 🏆 Golden Boot · Unity Field 160286
    #  Player             Goals
    1  Ada Eze                5
    2  Bola Ojo               3
   Confirmed stats only.
   [• Golden Boot] [Playmaker]
   [Most Consistent] [Most Wins]
   [Most MOTM] [The Wall]
   [📲 Share to WhatsApp]
      ✔ one pitch: straight to Golden Boot, as a table
      ✔ all six boards offered

👤 Ada taps [The Wall]
🤖 (edits its message) 🏆 The Wall · Unity Field 160286
    #  Player            Blocks
    1  Chidi Obi             14
   Confirmed stats only.
   [Golden Boot] [Playmaker]
   [Most Consistent] [Most Wins]
   [Most MOTM] [• The Wall]
   [📲 Share to WhatsApp]
      ✔ The Wall board

👤 Ada taps [Most MOTM]
🤖 (edits its message) 🏆 Most MOTM · Unity Field 160286
    #  Player              MOTM
    1  Ada Eze                2
   Confirmed stats only.
   [Golden Boot] [Playmaker]
   [Most Consistent] [Most Wins]
   [• Most MOTM] [The Wall]
   [📲 Share to WhatsApp]
      ✔ Most MOTM board

### Settle it

👤 Bola taps ⌨ [⚖️ Settle it]
🤖 ⚖️ Settle it
   Who is Player A?
   [Bola Ojo] [Ada Eze]
   [Chidi Obi]
   [✖️ Cancel]
      ✔ one pitch: asks for Player A, you first

👤 Bola taps [Ada Eze]
🤖 (edits its message) ⚖️ Settle it
   Ada versus who?
   [Bola Ojo] [Chidi Obi]
   [⬅️ Back] [✖️ Cancel]
      ✔ Player A is no longer offered as B

👤 Bola taps [⬅️ Back]
🤖 (edits its message) ⚖️ Settle it
   Who is Player A?
   [Bola Ojo] [Ada Eze]
   [Chidi Obi]
   [✖️ Cancel]

👤 Bola taps [Ada Eze]
🤖 (edits its message) ⚖️ Settle it
   Ada versus who?
   [Bola Ojo] [Chidi Obi]
   [⬅️ Back] [✖️ Cancel]

👤 Bola taps [Bola Ojo]
🤖 (edits its message) ⚖️ Settle it
   Ada vs Bola
   Based on what?
   [All time at this pitch]
   [Only Wed 7 Oct, 3:18 pm]
   [Only Sat 3 Oct, 3:18 pm]
   [⬅️ Back] [✖️ Cancel]
      ✔ scope: all time or one game

👤 Bola taps [All time at this pitch]
🤖 (edits its message) ⚖️ Ada vs Bola
   Unity Field 160286, all time
         Ada                   Bola     
           2  Games played     2        
           2  Wins             0        
           5  Goals            3        
           0  Assists          0        
         2.5  Goals per game   1.5      
           0  Assists per game 0        
        100%  Win rate         0%       
           2  Current win stre 0        
           2  Games both playe 2        
           2  Wins against eac 0        
   🤔 Star Boy is thinking it over…
      ✔ the table comes at once
🤖 🏆 Ada takes it.
   
   Ada takes it, no argument. Ada has 5 goals to show for it. Bola, keep pushing, your day dey come.
   [📲 Share to WhatsApp]
   [⚖️ Settle another]
      ✔ then the verdict, with a share button

👤 Bola taps [⚖️ Settle another]
🤖 ⚖️ Settle it
   Who is Player A?
   [Bola Ojo] [Ada Eze]
   [Chidi Obi]
   [✖️ Cancel]

👤 Bola taps [Chidi Obi]
🤖 (edits its message) ⚖️ Settle it
   Chidi versus who?
   [Bola Ojo] [Ada Eze]
   [⬅️ Back] [✖️ Cancel]

👤 Bola taps [Bola Ojo]
🤖 (edits its message) ⚖️ Settle it
   Chidi vs Bola
   Based on what?
   [All time at this pitch]
   [Only Wed 7 Oct, 3:18 pm]
   [Only Sat 3 Oct, 3:18 pm]
   [⬅️ Back] [✖️ Cancel]

👤 Bola taps [Only Wed 7 Oct, 3:18 pm]
🤖 (edits its message) ⚖️ Chidi vs Bola
   Unity Field 160286, Wed 7 Oct, 3:18 pm
       Chidi                   Bola     
           1  Games played     1        
           1  Wins             0        
           0  Goals            2        
           1  Assists          0        
   🤔 Star Boy is thinking it over…
      ✔ one game scope works too
🤖 🏆 Chidi takes it.
   
   Chidi takes it on the numbers. Chidi: 0 goals, 1 assists and 1 wins in 1 game. Bola: 2 goals, 0 assists and 0 wins in 1 game. Bola, the pitch is waiting for your reply. ⚽
   [📲 Share to WhatsApp]
   [⚖️ Settle another]

### My card

👤 Ada taps ⌨ [👤 My card]
🤖 [sends a picture] 👤 Ada Eze
   🔥 2 wins in a row
   Played like: Rashidi Yekini
   [⚖️ Settle it with…]
   [Open on web]
      ✔ the card arrives as a picture
      ✔ with Settle it and Open on web

👤 Ada taps [⚖️ Settle it with…]
🤖 ⚖️ Settle it
   Ada versus who?
   [Bola Ojo] [Chidi Obi]
   [✖️ Cancel]
      ✔ Settle it from the card starts with you as Player A

👤 Ada taps ⌨ [📅 My games]
🤖 📅 My games
   ✅ you're in · ❓ not answered · 🏁 played
   Tap a game.
   [🏁 Wed 7 Oct, 3:18 pm · Unity Field 160286]
   [🏁 Sat 3 Oct, 3:18 pm · Unity Field 160286]
   [⚽ New game]
      ✔ left the Settle it flow

### Report a game: pick the game first when there are several

👤 Bola taps ⌨ [📋 Report a game]
🤖 Which game?
   [Unity Field 160286 · Wed 7 Oct, 3:18 pm]
   [Unity Field 160286 · Sat 3 Oct, 3:18 pm]
      ✔ asks which game

👤 Bola taps [Unity Field 160286 · Wed 7 Oct, 3:18 pm]
🤖 (edits its message) How was your game at Unity Field 160286 · Wed 7 Oct, 3:18 pm? ⚽
   [Tap my stats 📋]
   [Send a voice note 🎙️]
      ✔ then tap or voice

👤 Bola taps [Tap my stats 📋]
🤖 (edits its message) Unity Field 160286
   Goals?
   [0] [1] [2] [3] [4+]
      ✔ the tap flow starts

```
