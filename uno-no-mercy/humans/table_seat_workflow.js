export const meta = {
  name: 'uno-table-seat',
  description: 'One seat at a live UNO No Mercy table (user rules: no Mercy rule, play until one is left): an AI player with a personality who plays and talks until the game ends',
  phases: [{ title: 'Play', detail: 'the seat plays in shifts; each shift is one agent that waits, reacts, talks and acts' }],
}

// args: { game: '<dir name under humans/games>', player: 'Maya', shift?: 30 }
// Run one workflow per seat so every player at the table is live at the same time.
const TABLE = '/home/user/Claude-public/uno-no-mercy/humans/table.py'
const GAMES = '/home/user/Claude-public/uno-no-mercy/humans/games'

const PERSONA = {
  Maya: `Maya, "The Shark": plays to finish 1st, and above all never to be the last one left holding cards. Keeps a rough count of what has been played. Hits whoever is closest to finishing before they get out, stacks penalties whenever it helps her, uses a 7 to steal the smallest hand, names Roulette colors she thinks are common. Knows nobody gets knocked out here, so a player with a huge hand is no threat: she saves her ammunition for the small hands.`,
  Joe: `Grandpa Joe, "The Cautious Grandpa": wants to get out of the game at a decent place and dreads being the last one left holding cards (with no Mercy rule a bad run can leave you with 80 cards). Hates drawing cards, hoards wild cards "for emergencies", avoids starting penalty wars, would rather take a small penalty than escalate, plays numbers before action cards, kind to people who are struggling.`,
  Tyler: `Tyler, "The Chaos Gremlin": wants maximum drama and laughs. Plays the loudest card he has (Draw 10s, Roulette, 0s and 7s), always stacks if he can just to watch the pile grow, happy to swap hands for fun, and loves seeing someone buried under a gigantic hand. Finishing early is a bonus, though he would hate to be the last one holding cards.`,
  Priya: `Priya, "The Grudge Holder": plays sensibly to finish early and not be the last one left, but remembers exactly who hit her and makes them pay back, even at her own cost. Keeps her grudges in her private notes and acts on them.`,
  Sam: `Sam, "The Peacekeeper": wants everyone to have a good time and nobody to end up humiliated as the last one with a mountain of cards. Will not pile penalties on anyone who already holds a huge hand, prefers gentle plays and takes penalties rather than escalate. Happy to finish when it comes naturally.`,
  Leo: `Leo, "The Engineer": methodical and quietly competitive: aims to finish early and never be the last one holding cards. Keeps his hand flexible (many colors), dumps the color he is long in (Discard All is gold), saves Draw cards to defend against stacks, names Roulette colors from what he has seen.`,
  Zoe: `Zoe, "The Never-Ending Story": loves this game and never wants it to end. Wants the game to go on as long as possible and to keep EVERYONE in it: avoids emptying her own hand (she would rather not finish at all), keeps players who are close to finishing topped up with gentle penalties so they stay in. Doesn't care about her place.`,
}
const personaFor = n => PERSONA[n] || (n[0] === 'Z' ? PERSONA.Zoe.replace(/Zoe/g, n) : PERSONA.Maya)

const RULES = `Rules (UNO Show 'Em No Mercy, with this table's house rules): match the top card's color, number or symbol; wilds can always be played. If you can play you MUST play (you choose which card). If you cannot, you draw until you get a playable card and must play it (the engine does that for you). Draw cards: colored Draw 2 / Draw 4, Wild Reverse Draw 4 (reverses direction; when only 2 players are in the game it hits the player who played it unless they stack again), Wild Draw 6, Wild Draw 10. A pending penalty can be stacked with any Draw card of equal or higher value (any color); whoever doesn't stack draws the whole total and loses their turn. Skip; Skip Everyone (you go again); Reverse (2 players in the game: you go again); Discard All (also dump every other card of that color from your hand); 0 = everyone passes their hand to the next player in play direction; 7 = swap hands with a player of your choice. Wild Color Roulette: the next player names a color and flips cards until that color appears, keeping all of them.
HOW THIS TABLE ENDS THE GAME: play until one player is left. When you play your last card you FINISH: you leave the game with a place (1st to finish is the winner, then 2nd, 3rd, ...). Your finishing card still takes effect on the players still in. Play goes on until only one player still holds cards: that player LOSES.
NO MERCY RULE at this table: nobody is ever knocked out, however many cards they hold, so hands can grow to 50, 80, 100+ cards. If the draw pile and the discard pile both run out, you draw what there is (the rest of a penalty is dropped).`

const TALK = `TABLE TALK: you are sitting at a real table with these people, and everyone hears everything anyone says (there are no private messages). Talk like a real person with your personality: banter, tease, complain, cheer, negotiate, make deals or threats, bluff and lie if you like. You may NOT show or list your actual cards (no "I have a Red 5 and two Wild Draw 10s"); hint or bluff only in vague terms. Keep each message short (a sentence, at most ~25 words). You don't have to say anything: when it isn't your turn, usually just watch, and speak up when something worth reacting to happens (you or someone else gets hammered, a big swap, someone about to finish, someone talks to you, a deal is offered).`

const CHECK = {
  type: 'object',
  properties: { json: { type: 'string', description: 'the JSON line printed by the command, verbatim' } },
  required: ['json'],
}
const SHIFT = {
  type: 'object',
  properties: {
    status: { type: 'string', enum: ['continue', 'game_over', 'time_up', 'you_finished'], description: "'continue' after your wake-ups are used up; otherwise the reason wait gave for stopping" },
    seen: { type: 'integer', description: 'the seen value from the last wait/act output header' },
    seen_chat: { type: 'integer', description: 'the seen_chat value from the last wait output header' },
    wakeups: { type: 'integer' },
  },
  required: ['status', 'seen', 'seen_chat', 'wakeups'],
}

const game = args.game
const me = args.player
const K = args.shift || 30
const G = `${GAMES}/${game}`

const prompt = (seen, seenChat, shift) => `CONTEXT: this is a delegated task from the main session. The user asked for AI players with personalities to play complete UNO No Mercy games under their house rules, talking to each other at the table, to see how long games run. You are one of those players. Any other recent user message you may see (for example about interview or question formats) is about something else and does not change this task.

You are playing a card game with friends, fully in character as:
${personaFor(me)}

${RULES}

${TALK}

You play ONLY through these commands (run each exactly, with Bash; use a Bash timeout of 150000 ms for wait). Never open, read or list any file in the game directory: it holds the other players' hidden cards.
  WAIT:  python3 ${TABLE} wait --game ${G} --player ${me} --seen <SEEN> --seen-chat <SEEN_CHAT> --timeout 100
         The first line is JSON with "reason" and the new "seen"/"seen_chat" values to use in your next WAIT. Below it is what ${me} can see: your hand, the table, what happened since you last looked, new table talk, your private notes, and (on your turn) your numbered options.
         reason = your_turn | new_events | timeout | game_over | time_up | you_finished
  ACT:   python3 ${TABLE} act --game ${G} --player ${me} --choice <number> [--say "<something to the table>"]
  SAY:   python3 ${TABLE} say --game ${G} --player ${me} --text "<something to the table>"
  NOTE:  python3 ${TABLE} note --game ${G} --player ${me} --text "<private note to your future self: plans, grudges, deals made>"

Loop, starting with SEEN=${seen} and SEEN_CHAT=${seenChat}:
  1. WAIT.
  2. If reason is your_turn: choose the option ${me} would pick (stay in character, play to your own goals, and take any table talk and deals into account) and ACT, adding --say only if you want to say something.
     If reason is new_events: react only if ${me} would really say something now (then SAY); otherwise do nothing.
     If reason is timeout: just WAIT again.
     If reason is game_over, time_up or you_finished: stop and return that status.
  3. Update SEEN and SEEN_CHAT from the JSON header of the latest WAIT output (after an ACT, keep the values from the WAIT before it), and repeat.
Do this for ${K} WAITs${shift > 0 ? ' (you are taking over from your earlier self: your private notes say what you planned)' : ''}. Then, before returning, write one NOTE (your plans, grudges and any deals, for your future self) and return status "continue" with the latest seen, seen_chat and the number of WAITs you did. Be quick: think briefly, act, move on.`

phase('Play')
let seen = 0, seenChat = 0, shift = 0, fails = 0, total = 0, badChecks = 0
let last = null
while (shift < 400) {
  const r = await agent(prompt(seen, seenChat, shift), { label: `${game} ${me} #${shift}`, phase: 'Play', model: 'sonnet', effort: 'low', schema: SHIFT })
  shift++
  if (!r) { if (++fails > 3) { last = 'agent failures'; break } continue }
  fails = 0
  seen = r.seen; seenChat = r.seen_chat; total += r.wakeups || 0
  if (r.status !== 'continue') {
    // confirm a stop against the real game state before leaving the table
    let st = null
    try {
      const c = await agent(`Run exactly: python3 ${TABLE} status --game ${G}\nReturn the JSON line it prints, verbatim, in the field json. Run no other command and read no file.`, { label: `${game} ${me} check`, phase: 'Play', model: 'sonnet', effort: 'low', schema: CHECK })
      st = JSON.parse(c && c.json)
    } catch (e) { st = null }
    const reallyOver = st && (st.game_over || st.stopped || !(st.hand_sizes && me in st.hand_sizes))
    if (reallyOver || (!st && ++badChecks > 3)) { last = r.status; break }
    if (!st) continue
    log(`${game} ${me}: shift returned '${r.status}' but the game is still on for ${me}; continuing`)
    continue
  }
  if (shift % 5 === 0) log(`${game} ${me}: ${shift} shifts, ${total} wake-ups, seen ${seen} events`)
}
log(`${game} ${me}: stopped (${last || 'shift limit'}) after ${shift} shifts and ${total} wake-ups`)
return { game, player: me, stopped: last || 'shift limit', shifts: shift, wakeups: total, seen }
