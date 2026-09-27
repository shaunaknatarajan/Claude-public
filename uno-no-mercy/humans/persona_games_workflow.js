export const meta = {
  name: 'uno-persona-games-A',
  description: 'AI players with personalities play full UNO No Mercy games (no turn cap), one decision at a time',
  phases: [{ title: 'Play', detail: 'each decision is made by the persona whose turn it is, seeing only their own view' }],
}

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
const personaFor = n => PERSONA[n] || PERSONA[n === 'Zara' || n === 'Zed' || n === 'Zia' ? 'Zoe' : n].replace(/^Zoe/, n)

const RULES = `Rules (official UNO Show 'Em No Mercy): match the top card's color, number or symbol; wilds can always be played. If you can play you MUST play (you choose which card). If you cannot, you draw until you get a playable card and must play it (the engine does that automatically). Draw cards: colored Draw 2 / Draw 4, Wild Reverse Draw 4 (reverses direction; with only 2 players it hits the player who played it unless they stack again), Wild Draw 6, Wild Draw 10. A pending penalty can be stacked with any Draw card of equal or higher value (any color); whoever doesn't stack draws the whole total and loses their turn. Skip; Skip Everyone (you go again); Reverse (2 players: you go again); Discard All (also dump every other card of that color from your hand); 0 = everyone passes their hand to the next player in play direction; 7 = swap hands with a player of your choice. Wild Color Roulette: the next player names a color and flips cards until that color appears, keeping all of them. MERCY RULE: reaching 25 cards knocks you out. You win by playing your last card, or by being the last player left.`

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

async function playGame(g) {
  let st = g.status
  let n = 0, miss = 0
  const MAX = 700
  while (!st.game_over && n < MAX) {
    const who = st.next_player
    const r = await agent(`You are playing a card game at a table of friends, fully in character as:
${personaFor(who)}

${RULES}

Game directory: ${GAMES}/${g.id}
1. Run exactly: python3 ${ENGINE} view --game ${GAMES}/${g.id}
   It shows only what ${who} can see: your hand, the table, recent events, your private notes, and your numbered options.
   If it says "You are" someone other than ${who}, do NOT act: run python3 ${ENGINE} status --game ${GAMES}/${g.id} and return acted=false with next_player from that JSON.
2. Pick the option ${who} would choose, staying in character (a real person with this personality, playing to their own goals).
3. Run exactly: python3 ${ENGINE} act --game ${GAMES}/${g.id} --player ${who} --choice <number> --note "<optional short private note to your future self, e.g. a grudge or a plan; omit if nothing>"
4. Return the fields from the JSON that act prints (game_over, next_player, turns, winner if any).
Do not open or read any other file (the game state file holds other players' hidden cards), and run no other commands.`,
      { label: `${g.id} d${n} ${who}`, phase: 'Play', model: 'sonnet', effort: 'low', schema: DECISION })
    if (!r || !r.next_player && !r.game_over) {
      miss++
      if (miss > 5) break
      continue
    }
    miss = 0
    if (r.acted) n++
    st = { game_over: r.game_over, next_player: r.next_player, turns: r.turns, winner: r.winner }
    if (n % 20 === 0) log(`${g.id}: ${n} decisions, turn ${st.turns}`)
  }
  log(`${g.id}: ${st.game_over ? 'GAME OVER, winner ' + st.winner : 'paused'} after ${st.turns} turns and ${n} decisions`)
  return { id: g.id, decisions: n, final: st }
}

phase('Play')
const results = await parallel(args.games.map(g => () => playGame(g)))
return results
