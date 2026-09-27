export const meta = {
  name: 'uno-persona-games-A',
  description: 'AI players with personalities play full UNO No Mercy games (no turn cap), one decision at a time',
  phases: [{ title: 'Play', detail: 'each decision is made by the persona whose turn it is, seeing only their own view' }],
}

// args.games: [{ id, status, endRule?, noMercy?, maxDecisions? }]
//   id      game directory under GAMES, created with engine.py new (use the same rule flags there:
//           endRule 'last' <-> --end-rule last, noMercy true <-> --mercy 0)
//   status  the JSON printed by engine.py new (or status, to resume a game from an earlier run)
//   endRule 'last': house rule "play until one player is left" (RULES.md section 7)
//   noMercy true: no 25-card Mercy rule, nobody is ever knocked out
// A game with endRule or noMercy gets a decision budget of at least 3,000 (maxDecisions), logs
// progress every 50 decisions, and if it is not over when the budget runs out its result carries
// `resume`: an args.games entry that continues it in a later run (state is saved after every decision).
// One workflow run can make at most 1,000 agent calls in all, so such games stop cleanly before that
// cap (args.maxAgentCalls, default 990, shared by all games of the run) and are resumed in the next run.

const ENGINE = '/home/user/Claude-public/uno-no-mercy/humans/engine.py'
const GAMES = '/home/user/Claude-public/uno-no-mercy/humans/games'
const PERSONA = {
  Maya: 'Maya, "The Shark": plays to win and only to win. Keeps a rough count of what has been played. Hits whoever is closest to going out, stacks penalties whenever it helps her, uses a 7 to steal the smallest hand, names Roulette colors she thinks are common.',
  Joe: 'Grandpa Joe, "The Cautious Grandpa": hates drawing cards, hoards wild cards "for emergencies", avoids starting penalty wars, would rather take a small penalty than escalate, plays numbers before action cards, kind to people who are struggling.',
  Tyler: 'Tyler, "The Chaos Gremlin": wants maximum drama and laughs. Plays the loudest card he has (Draw 10s, Roulette, 0s and 7s), always stacks if he can just to watch the pile grow, happy to swap hands for fun. Winning is a bonus.',
  Priya: 'Priya, "The Grudge Holder": plays sensibly, but remembers exactly who hit her and makes them pay back, even at her own cost. Writes grudges into her private notes and acts on them.',
  Sam: 'Sam, "The Peacekeeper": wants everyone to have a good time, hates knocking friends out, will not pile penalties on anyone near 25 cards, prefers gentle plays and takes penalties rather than escalate. Still happy to win if it is easy.',
  Leo: 'Leo, "The Engineer": methodical and quietly competitive. Keeps his hand flexible (many colors), dumps the color he is long in, saves Draw cards to defend against stacks, names Roulette colors from what he has seen.',
  Zoe: 'Zoe, "The Never-Ending Story": loves this game and never wants it to end. Tries to keep EVERYONE in the game as long as possible: avoids emptying her own hand, avoids knocking anyone out, keeps small hands topped up with gentle penalties.',
}
const personaFor = n => PERSONA[n] || (n[0] === 'Z' ? PERSONA.Zoe.replace(/^Zoe/, n) : PERSONA.Maya)

// The same people at a table that plays until one player is left (endRule 'last'): emptying your hand
// means finishing and leaving with a place; the goal is to finish early, and above all not to be the
// last one holding cards. m = true when the table also plays WITHOUT the Mercy rule.
const PERSONA_LAST = {
  Maya: m => `Maya, "The Shark": plays to finish 1st, and above all never to be the last one left holding cards. Keeps a rough count of what has been played. Hits whoever is closest to finishing before they get out, stacks penalties whenever it helps her, uses a 7 to steal the smallest hand, names Roulette colors she thinks are common.${m ? ' Knows nobody gets knocked out here, so a player with a huge hand is no threat: she saves her ammunition for the small hands.' : ''}`,
  Joe: m => `Grandpa Joe, "The Cautious Grandpa": wants to get out of the game at a decent place and dreads being the last one left holding cards${m ? ' (with no Mercy rule a bad run can leave you with 80 cards)' : ''}. Hates drawing cards, hoards wild cards "for emergencies", avoids starting penalty wars, would rather take a small penalty than escalate, plays numbers before action cards, kind to people who are struggling.`,
  Tyler: m => `Tyler, "The Chaos Gremlin": wants maximum drama and laughs. Plays the loudest card he has (Draw 10s, Roulette, 0s and 7s), always stacks if he can just to watch the pile grow, happy to swap hands for fun${m ? ', and loves seeing someone buried under a gigantic hand' : ''}. Finishing early is a bonus, though he would hate to be the last one holding cards.`,
  Priya: m => `Priya, "The Grudge Holder": plays sensibly to finish early and not be the last one left, but remembers exactly who hit her and makes them pay back, even at her own cost. Writes grudges into her private notes and acts on them.`,
  Sam: m => m
    ? `Sam, "The Peacekeeper": wants everyone to have a good time and nobody to end up humiliated as the last one with a mountain of cards. Will not pile penalties on anyone who already holds a huge hand, prefers gentle plays and takes penalties rather than escalate. Happy to finish when it comes naturally.`
    : `Sam, "The Peacekeeper": wants everyone to have a good time, hates knocking friends out, will not pile penalties on anyone near 25 cards, prefers gentle plays and takes penalties rather than escalate. Happy to finish when it comes naturally, and doesn't want anyone to end up last.`,
  Leo: m => `Leo, "The Engineer": methodical and quietly competitive: aims to finish early and never be the last one holding cards. Keeps his hand flexible (many colors), dumps the color he is long in (Discard All is gold), saves Draw cards to defend against stacks, names Roulette colors from what he has seen.`,
  Zoe: m => `Zoe, "The Never-Ending Story": loves this game and never wants it to end. Wants the game to go on as long as possible and to keep EVERYONE in it: avoids emptying her own hand (she would rather not finish at all), keeps players who are close to finishing topped up with gentle penalties so they stay in${m ? '' : ', and avoids knocking anyone out'}. Doesn't care about her place.`,
}
const isHouse = g => g.endRule === 'last' || !!g.noMercy
const personaForGame = (n, g) => {
  if (g.endRule === 'last') {
    const z = n[0] === 'Z' && !PERSONA_LAST[n]
    const f = PERSONA_LAST[n] || (z ? PERSONA_LAST.Zoe : PERSONA_LAST.Maya)
    const s = f(!!g.noMercy)
    return z ? s.replace(/^Zoe/, n) : s
  }
  const s = personaFor(n)
  return g.noMercy ? `${s} (This table plays WITHOUT the Mercy rule: nobody is ever knocked out, so read any mention of knocking out as piling cards on someone.)` : s
}

const RULES = `Rules (official UNO Show 'Em No Mercy): match the top card's color, number or symbol; wilds can always be played. If you can play you MUST play (you choose which card). If you cannot, you draw until you get a playable card and must play it (the engine does that automatically). Draw cards: colored Draw 2 / Draw 4, Wild Reverse Draw 4 (reverses direction; with only 2 players it hits the player who played it unless they stack again), Wild Draw 6, Wild Draw 10. A pending penalty can be stacked with any Draw card of equal or higher value (any color); whoever doesn't stack draws the whole total and loses their turn. Skip; Skip Everyone (you go again); Reverse (2 players: you go again); Discard All (also dump every other card of that color from your hand); 0 = everyone passes their hand to the next player in play direction; 7 = swap hands with a player of your choice. Wild Color Roulette: the next player names a color and flips cards until that color appears, keeping all of them. MERCY RULE: reaching 25 cards knocks you out. You win by playing your last card, or by being the last player left.`

const RULES_CORE = `Rules (UNO Show 'Em No Mercy, with this table's house rules below): match the top card's color, number or symbol; wilds can always be played. If you can play you MUST play (you choose which card). If you cannot, you draw until you get a playable card and must play it (the engine does that automatically). Draw cards: colored Draw 2 / Draw 4, Wild Reverse Draw 4 (reverses direction; when only 2 players are in the game it hits the player who played it unless they stack again), Wild Draw 6, Wild Draw 10. A pending penalty can be stacked with any Draw card of equal or higher value (any color); whoever doesn't stack draws the whole total and loses their turn. Skip; Skip Everyone (you go again); Reverse (2 players in the game: you go again); Discard All (also dump every other card of that color from your hand); 0 = everyone passes their hand to the next player in play direction; 7 = swap hands with a player of your choice. Wild Color Roulette: the next player names a color and flips cards until that color appears, keeping all of them.`
const RULES_LAST = `HOW THIS TABLE ENDS THE GAME: play until one player is left. When you play your last card you FINISH: you leave the game with a place (the 1st to finish is the winner, then 2nd, 3rd, ...). Your finishing card still takes effect on the players still in: a Draw card's penalty goes to the next player, Skip skips them, Reverse reverses, a Wild Color Roulette hits the next player, a 0 makes the players still in pass their hands on; a 7 does nothing and Skip Everyone just passes the turn on. Play goes on until only one player still holds cards: that player LOSES.`
const RULES_FIRST = `The first player to play their last card wins and the game ends.`
const RULES_NO_MERCY = `NO MERCY RULE at this table: nobody is ever knocked out, however many cards they hold, so hands can grow to 50, 80, 100+ cards. If the draw pile and the discard pile both run out, you draw what there is; a player who can neither play nor draw passes.`
const RULES_MERCY_LAST = `MERCY RULE: reaching 25 cards knocks you out of the game (placed below everyone who finished).`
const RULES_MERCY_FIRST = `MERCY RULE: reaching 25 cards knocks you out; the last player left also wins.`
const rulesFor = g => !isHouse(g) ? RULES : [RULES_CORE, g.endRule === 'last' ? RULES_LAST : RULES_FIRST,
  g.noMercy ? RULES_NO_MERCY : (g.endRule === 'last' ? RULES_MERCY_LAST : RULES_MERCY_FIRST)].join(' ')

const DECISION = {
  type: 'object',
  properties: {
    acted: { type: 'boolean', description: 'true if you ran act successfully' },
    choice: { type: 'integer' },
    reason: { type: 'string', description: 'one short in-character sentence' },
    game_over: { type: 'boolean' },
    next_player: { type: 'string', description: 'next_player from the JSON printed by act (or by status); empty if game over' },
    turns: { type: 'integer' },
    winner: { type: 'string' },
  },
  required: ['acted', 'game_over', 'next_player', 'turns'],
}
const DECISION_HOUSE = {
  type: 'object',
  properties: {
    ...DECISION.properties,
    decisions: { type: 'integer', description: 'decisions from the JSON (total so far in this game)' },
    finished: { type: 'array', items: { type: 'string' }, description: 'names from "finished" in the JSON, in order; empty if none' },
    loser: { type: 'string', description: 'loser from the JSON, if the game is over' },
    end_reason: { type: 'string', description: 'end_reason from the JSON, if the game is over' },
  },
  required: DECISION.required,
}
let calls = 0 // agent calls made by house-rule games in this run (the runtime caps a run at 1,000 in all)
const CALL_CAP = (args && args.maxAgentCalls) || 990
const houseGames = ((args && args.games) || []).filter(isHouse).length
const STATUS = { type: 'object', properties: { json: { type: 'string', description: 'the JSON line printed by the command, verbatim' } }, required: ['json'] }

async function playGame(g) {
  const house = isHouse(g)
  const rules = rulesFor(g)
  let st = g.status
  let n = 0, miss = 0
  const MAX = house ? Math.max(3000, g.maxDecisions || 0) : 700
  const EVERY = house ? 50 : 20
  let stop = ''
  while (!st.game_over && n < MAX) {
    const who = st.next_player
    if (house && calls >= CALL_CAP - houseGames) { stop = 'agent-call cap of this run reached'; break }
    if (house) calls++
    let r
    try {
      r = await agent(`You are playing a card game at a table of friends, fully in character as:
${house ? personaForGame(who, g) : personaFor(who)}

${rules}

Game directory: ${GAMES}/${g.id}
1. Run exactly: python3 ${ENGINE} view --game ${GAMES}/${g.id}
   It shows only what ${who} can see: your hand, the table, recent events, your private notes, and your numbered options.
   If it says "You are" someone other than ${who}, do NOT act: run python3 ${ENGINE} status --game ${GAMES}/${g.id} and return acted=false with next_player from that JSON.
2. Pick the option ${who} would choose, staying in character (a real person with this personality, playing to their own goals).
3. Run exactly: python3 ${ENGINE} act --game ${GAMES}/${g.id} --player ${who} --choice <number> --note "<optional short private note to your future self, e.g. a grudge or a plan; omit if nothing>"
4. Return the fields from the JSON that act prints (game_over, next_player, turns, ${house ? 'decisions, the names in finished, winner, loser and end_reason if any' : 'winner if any'}).
Do not open or read any other file (the game state file holds other players' hidden cards), and run no other commands.`,
      { label: `${g.id} d${n} ${who}`, phase: 'Play', model: 'sonnet', effort: 'low', schema: house ? DECISION_HOUSE : DECISION })
    } catch (e) {
      if (!house) throw e
      stop = `agent call failed: ${e && e.message ? e.message : e}`
      break
    }
    if (!r || !r.next_player && !r.game_over) {
      miss++
      if (miss > 5) break
      continue
    }
    if (house) {
      if (!r.acted) {
        if (++miss > 5) { stop = 'the agents kept declining to act'; break }
        st = { ...st, next_player: r.next_player, game_over: r.game_over }
        continue
      }
      miss = 0
      n++
      st = { game_over: r.game_over, next_player: r.next_player, turns: r.turns, winner: r.winner, loser: r.loser,
        finished: r.finished || st.finished || [], decisions: r.decisions, end_reason: r.end_reason }
      if (n % EVERY === 0) log(`${g.id}: ${n} decisions this run${st.decisions ? ` (${st.decisions} in all)` : ''}, turn ${st.turns}${st.finished.length ? `, finished: ${st.finished.join(', ')}` : ''}`)
      continue
    }
    miss = 0
    if (r.acted) n++
    st = { game_over: r.game_over, next_player: r.next_player, turns: r.turns, winner: r.winner }
    if (n % EVERY === 0) log(`${g.id}: ${n} decisions, turn ${st.turns}`)
  }
  if (!house) {
    log(`${g.id}: ${st.game_over ? 'GAME OVER, winner ' + st.winner : 'paused'} after ${st.turns} turns and ${n} decisions`)
    return { id: g.id, decisions: n, final: st }
  }
  if (st.game_over) {
    log(`${g.id}: GAME OVER after ${st.turns} turns and ${n} decisions this run: ${st.end_reason || ''}${st.winner ? `; winner ${st.winner}` : ''}${st.loser ? `; last place: ${st.loser}${g.noMercy && g.endRule === 'last' ? ' (left holding cards)' : ''}` : ''}`)
    return { id: g.id, decisions: n, final: st }
  }
  // not over: fetch the full status so the game can be resumed in a later run (state is saved after every decision)
  let full = null
  try {
    calls++
    const s = await agent(`Run exactly: python3 ${ENGINE} status --game ${GAMES}/${g.id}
Return the JSON line it prints, verbatim, in the field json. Run no other command and read no file.`,
      { label: `${g.id} status`, phase: 'Play', model: 'sonnet', effort: 'low', schema: STATUS })
    full = JSON.parse(s && s.json)
  } catch (e) { full = null }
  const status = full && full.next_player ? full : st
  if (!stop) stop = miss > 5 ? 'repeated agent failures' : `decision budget of ${MAX} used up`
  const resume = { id: g.id, status, endRule: g.endRule, noMercy: g.noMercy, maxDecisions: g.maxDecisions }
  log(`${g.id}: NOT FINISHED after ${n} decisions this run (turn ${status.turns}; ${stop}). Resume it with the returned resume entry as an args.games item`)
  return { id: g.id, decisions: n, final: status, unfinished: true, stopped: stop, resume }
}

phase('Play')
const results = await parallel(args.games.map(g => () => playGame(g)))
return results
