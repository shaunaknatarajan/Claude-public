// nomercy.c -- high-throughput simulator for UNO Show 'Em No Mercy (Mattel, 2023).
//
// Every rules ambiguity is a command-line flag (see usage()). Defaults follow the
// official instruction sheet as documented in ../RULES.md.
//
// Build:  gcc -O3 -march=native -pthread -o nomercy nomercy.c -lm
// Run:    ./nomercy -p 4 -n 1000000 -policy random -threads 4 -seed 1
//
// Output is a single JSON object on stdout (summary statistics + a turn-count
// histogram), suitable for the analysis scripts in ../analysis/.

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <pthread.h>

// ----------------------------------------------------------------------------
// Cards
// ----------------------------------------------------------------------------
// A card "type" is an integer in [0, NT). Colored types are color*16 + kind,
// kind in [0,16). Wild types are 64..67.
enum { K_D2 = 10, K_D4 = 11, K_SKIP = 12, K_SKIPALL = 13, K_REV = 14, K_DISCALL = 15,
       K_WRD4 = 16, K_WD6 = 17, K_WD10 = 18, K_ROUL = 19, K_WILD = 20 };
#define NT 69
#define WILD 4
#define MAXP 10
#define DECK 168

// Deck compositions. The official sheet only says "168 cards"; see RULES.md section 1.
//   deck 0 (default): fan-wiki breakdown, 36 per colour + 24 wilds (8 WRD4, 4 WD6, 4 WD10, 8 Roulette)
//   deck 1: rajatghate5/no-mercy breakdown, 38 per colour (3 colored Draw 4, 3 Skip Everyone) + 4 of each wild
//   deck 2: open-mercy.com breakdown, one 0 per colour, 3 of each colored action, 4 of each wild + 4 plain Wilds
static const int DECKS_COLORED[3][16] = {
    {2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 2, 3, 2, 3, 3},
    {2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3},
    {1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3},
};
static const int DECKS_WILD[3][5] = {{8, 4, 4, 8, 0}, {4, 4, 4, 4, 0}, {4, 4, 4, 4, 4}};
static int COLORED_COUNT[16];
static int WILD_COUNT[5];
static int PER_COLOR;
static void select_deck(int d) {
    PER_COLOR = 0;
    for (int k = 0; k < 16; k++) { COLORED_COUNT[k] = DECKS_COLORED[d][k]; PER_COLOR += COLORED_COUNT[k]; }
    int tot = 4 * PER_COLOR;
    for (int w = 0; w < 5; w++) { WILD_COUNT[w] = DECKS_WILD[d][w]; tot += WILD_COUNT[w]; }
    if (tot != 168) { fprintf(stderr, "deck %d has %d cards\n", d, tot); exit(2); }
}

static inline int ccolor(int t) { return t < 64 ? (t >> 4) : WILD; }
static inline int ckind(int t) { return t < 64 ? (t & 15) : 16 + (t - 64); }
static inline int drawval_kind(int k) {
    switch (k) {
    case K_D2: return 2;
    case K_D4: return 4;
    case K_WRD4: return 4;
    case K_WD6: return 6;
    case K_WD10: return 10;
    default: return 0;
    }
}
static inline int drawval(int t) { return drawval_kind(ckind(t)); }

static const char *KIND_NAME[21] = {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "D2", "D4", "Skip",
                                    "SkipAll", "Rev", "DiscardAll", "WRD4", "WD6", "WD10", "Roulette", "Wild"};
static const char *COLOR_NAME[5] = {"R", "Y", "G", "B", "W"};

// ----------------------------------------------------------------------------
// RNG: xoshiro256** seeded by splitmix64
// ----------------------------------------------------------------------------
typedef struct { uint64_t s[4]; } Rng;
static inline uint64_t rotl(uint64_t x, int k) { return (x << k) | (x >> (64 - k)); }
static uint64_t splitmix64(uint64_t *x) {
    uint64_t z = (*x += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}
static void rng_seed(Rng *r, uint64_t seed) {
    for (int i = 0; i < 4; i++) r->s[i] = splitmix64(&seed);
}
static inline uint64_t rng_next(Rng *r) {
    uint64_t *s = r->s;
    uint64_t res = rotl(s[1] * 5, 7) * 9, t = s[1] << 17;
    s[2] ^= s[0]; s[3] ^= s[1]; s[1] ^= s[2]; s[0] ^= s[3]; s[2] ^= t; s[3] = rotl(s[3], 45);
    return res;
}
// unbiased integer in [0, n) (Lemire)
static inline uint32_t rng_below(Rng *r, uint32_t n) {
    uint64_t m = (uint64_t)(uint32_t)(rng_next(r) >> 32) * n;
    uint32_t l = (uint32_t)m;
    if (l < n) {
        uint32_t th = -n % n;
        while (l < th) { m = (uint64_t)(uint32_t)(rng_next(r) >> 32) * n; l = (uint32_t)m; }
    }
    return (uint32_t)(m >> 32);
}
static inline double rng_unif(Rng *r) { return (rng_next(r) >> 11) * 0x1.0p-53; }

// ----------------------------------------------------------------------------
// Rules (every ambiguity is a flag)
// ----------------------------------------------------------------------------
typedef struct {
    int hand_size;        // cards dealt to each player (7)
    int mercy;            // eliminated at >= mercy cards (25)
    int mercy_immediate;  // 1: checked after every single card drawn; 0: at end of the drawing action
    int voluntary_draw;   // 1: a player holding a playable card may draw instead
    int after_draw;       // 0: must play the playable card that ended draw-until-playable
                          // 1: may play it or keep it (turn ends)
                          // 2: keeps it, turn ends (never plays it this turn)
    int stack_rule;       // 0: any draw card of >= value of the last draw card (color irrelevant)
                          // 1: >= value AND (same color as active color, or same kind, or wild)
                          // 2: no stacking at all (victim draws immediately)
    int roulette_chooser; // 0: victim names the color; 1: the player who played it names it
    int elim_cards;       // 0: shuffled into the draw pile; 1: bottom of draw pile; 2: into discard pile
    int zero_seven;       // 1: 0 = pass hands in direction of play, 7 = swap with chosen player
    int reverse2p_skip;   // 1: Reverse with 2 players acts as Skip
    int wrd4_victim;      // 0: next player in the NEW direction draws; 1: next player in OLD direction draws
    int wrd4_2p_self;     // 1: with exactly 2 players, Wild Reverse Draw 4 makes its PLAYER face the +4
                          //    (official sheet: "skips the other player and makes YOU draw 4 cards!")
    int stack_mandatory;  // 1: a player holding a legal stacking card must stack
} Rules;

static void rules_default(Rules *R) {
    memset(R, 0, sizeof *R);
    R->hand_size = 7;
    R->mercy = 25;
    R->mercy_immediate = 1;
    R->voluntary_draw = 0;
    R->after_draw = 0;
    R->stack_rule = 0;
    R->roulette_chooser = 0;
    R->elim_cards = 2; // official: "Set aside their hand of cards until the deck runs out and needs to be reshuffled"
    R->zero_seven = 1;
    R->reverse2p_skip = 1;
    R->wrd4_victim = 0;
    R->wrd4_2p_self = 1;
    R->stack_mandatory = 0;
}

// ----------------------------------------------------------------------------
// Policies
// ----------------------------------------------------------------------------
// random : uniform over distinct playable card types, colours, targets, stack-or-accept
// randomv: as random, plus "decline and draw" as one more option when -voluntary_draw 1
// greedy : a sensible competitive heuristic (attack small hands, dump colours, stack, ...)
// collude: ALL players cooperate to make the game last as long as possible (depth-limited
//          search over forced continuations; full knowledge of hands, never of pile order)
// mcwin  : competitive Monte-Carlo player (determinized greedy rollouts, maximizes own wins)
// shark, grandpa, gremlin, grudge, peace, engineer, staller: rule-based "personality" players
//          (see ../humans/personas.md); cheap stand-ins for the AI players with personalities
enum { POL_RANDOM = 0, POL_RANDOMV = 1, POL_GREEDY = 2, POL_COLLUDE = 3, POL_MCWIN = 4,
       POL_SHARK = 5, POL_GRANDPA = 6, POL_GREMLIN = 7, POL_GRUDGE = 8, POL_PEACE = 9, POL_ENGINEER = 10,
       POL_STALLER = 11 };
#define NPOL 12
static const char *POL_NAME[] = {"random", "randomv", "greedy", "collude", "mcwin", "shark", "grandpa",
                                 "gremlin", "grudge", "peace", "engineer", "staller"};
#define IS_PERSONA(pol) ((pol) >= POL_SHARK)
typedef struct {
    double attack;    // liking for Draw cards / skips aimed at the next player
    double leader;    // extra attack when that player is close to going out (<= 3 cards)
    double stack_p;   // probability of stacking when able (otherwise take the penalty)
    double wild_keep; // reluctance to spend a wild while other options exist
    double chaos;     // liking for loud cards (Wild Draw 10, Roulette, 0, 7, Skip Everyone)
    double mercy;     // reluctance to hit a player who might be knocked out
    double grudge;    // extra attack on whoever last made me draw
    int stall;        // 1: never go out if avoidable, never knock anyone out, top up small hands
    double noise;     // human inconsistency: uniform noise added to every score
    int smart;        // 1: count cards for Roulette colours
} Persona;
static const Persona PERSONAS[] = {
    /* shark    */ {12, 80, 1.00, 25, 0, 0, 0, 0, 5, 1},
    /* grandpa  */ {2, 20, 0.35, 60, -20, 40, 0, 0, 8, 0},
    /* gremlin  */ {6, 0, 1.00, -20, 60, 0, 0, 0, 25, 0},
    /* grudge   */ {5, 30, 0.80, 25, 0, 0, 80, 0, 8, 0},
    /* peace    */ {-10, 10, 0.20, 20, -10, 200, 0, 0, 8, 0},
    /* engineer */ {8, 60, 0.90, 40, 0, 0, 0, 0, 3, 1},
    /* staller  */ {0, 0, 0.50, 10, -10, 400, 0, 1, 5, 0},
};
static const Persona *persona_of(int pol) { return &PERSONAS[pol - POL_SHARK]; }

// ----------------------------------------------------------------------------
// Game state
// ----------------------------------------------------------------------------
typedef struct {
    const Rules *R;
    Rng *rng;
    int np;
    int pol[MAXP];
    int alive[MAXP];
    int nalive;
    uint8_t hand[MAXP][NT];
    int hsize[MAXP];
    uint8_t pile[DECK + 8];
    int pn;
    uint8_t disc[NT]; // discard pile contents EXCLUDING the top card
    int dn;
    int top, color;
    int cur, dir;
    int stack, stackv;
    int over;
    int winner;
    int endcause; // 1 = emptied hand, 2 = last player standing, 3 = turn cap,
                  // 4 = stuck (nobody can play or draw), 5 = proven deterministic cycle
    // counters
    long long turns, plays, draws, reshuffles, elims, zeros, sevens, roulettes, stacks_accepted;
    long long dup_draw_turns;
    int max_stack;
    int max_hand_seen;
    int elim_turn[MAXP];
    long long turn_cap;
    int debug;
    int draw_ctx;     // what kind of draw is in progress: 1 = draw-until-playable, 2 = penalty, 3 = roulette
    long long elim_ctx[4];
    int stuck_run;    // consecutive "cannot play, cannot draw" passes
    int stack_last;   // who played the last Draw card onto the pending stack
    int last_hitter[MAXP]; // who last made each player draw (for grudges)
    long long nchoices; // number of decisions taken with >= 2 options (for cycle detection)
    uint64_t hring[64]; long long cring[64]; int hn;
    int force_color;  // >=0: next choose_color returns this (used by look-ahead policies)
    int force_target; // >=0: next choose_swap returns this
} Game;

static void check_invariants(Game *G, const char *where);

static inline int next_alive(const Game *G, int p, int dir) {
    int q = p;
    do { q = (q + dir + G->np) % G->np; } while (!G->alive[q]);
    return q;
}

static void shuffle_u8(Rng *r, uint8_t *a, int n) {
    for (int i = n - 1; i > 0; i--) {
        int j = (int)rng_below(r, (uint32_t)(i + 1));
        uint8_t t = a[i]; a[i] = a[j]; a[j] = t;
    }
}

static void end_game(Game *G, int winner, int cause) {
    if (G->over) return;
    G->over = 1;
    G->winner = winner;
    G->endcause = cause;
}

static void reshuffle(Game *G) {
    int n = 0;
    for (int t = 0; t < NT; t++) {
        for (int c = 0; c < G->disc[t]; c++) G->pile[G->pn + n++] = (uint8_t)t;
        G->disc[t] = 0;
    }
    G->dn = 0;
    // the pile is empty whenever we reshuffle, so shuffling everything is exact
    G->pn += n;
    shuffle_u8(G->rng, G->pile, G->pn);
    G->reshuffles++;
    if (G->pn >= 2) G->nchoices++; // a genuinely random event (for deterministic-cycle detection)
}

static void eliminate(Game *G, int p) {
    G->alive[p] = 0;
    G->nalive--;
    G->elims++;
    G->elim_ctx[G->draw_ctx & 3]++;
    G->elim_turn[p] = (int)G->turns;
    // return cards
    int n = 0;
    uint8_t tmp[DECK];
    for (int t = 0; t < NT; t++) {
        for (int c = 0; c < G->hand[p][t]; c++) tmp[n++] = (uint8_t)t;
        G->hand[p][t] = 0;
    }
    G->hsize[p] = 0;
    if (G->R->elim_cards == 0) {
        memcpy(G->pile + G->pn, tmp, n);
        G->pn += n;
        shuffle_u8(G->rng, G->pile, G->pn);
    } else if (G->R->elim_cards == 1) {
        shuffle_u8(G->rng, tmp, n);
        memmove(G->pile + n, G->pile, G->pn);
        memcpy(G->pile, tmp, n);
        G->pn += n;
    } else {
        for (int i = 0; i < n; i++) G->disc[tmp[i]]++;
        G->dn += n;
    }
    if (G->nalive == 1) {
        for (int q = 0; q < G->np; q++)
            if (G->alive[q]) end_game(G, q, 2);
    }
}

// Draw one card for player p. Returns the card type, -1 if nothing can be drawn,
// -2 if the player was eliminated by the mercy rule.
// ---- Adversarial nature (stress test only; the real game draws uniformly) ------------
// Instead of the next card of a uniformly shuffled pile, "nature" picks the drawn card
// greedily to end the game: flood draw-until-playable / Roulette victims with non-stopping
// cards when that can knock them out, otherwise force the nastiest playable card
// (Roulette, Wild Draw 10, ...) onto the table, and fill penalty draws with poison.
static int adv_nature = 0;
static inline int playable_now(const Game *G, int t) {
    int c = ccolor(t);
    if (c == WILD || c == G->color) return 1;
    int tk = ckind(G->top);
    return tk < 16 && ckind(t) == tk;
}
static int nature_rank(int t) { // higher = nastier card to force onto the table / into a hand
    switch (ckind(t)) {
    case K_ROUL: return 9;
    case K_WD10: return 8;
    case K_WD6: return 7;
    case K_D4: return 6;
    case K_WRD4: return 5;
    case K_D2: return 4;
    case K_DISCALL: return 3;
    default: return 1;
    }
}
static int nature_pick(const Game *G, int p) {
    int h = G->hsize[p];
    int need = G->R->mercy - h - 1; // non-final cards that must be "bad" to knock p out
    int n = G->pn;
    int bad_idx = -1, good_idx = -1, good_rank = -1, bad_rank = 1 << 30, nbad = 0;
    for (int i = 0; i < n; i++) {
        int t = G->pile[i];
        int stops;
        if (G->draw_ctx == 1) stops = playable_now(G, t);
        else if (G->draw_ctx == 3) stops = ccolor(t) == G->color;
        else stops = 0;
        int r = nature_rank(t);
        if (!stops) {
            nbad++;
            // among non-stopping cards prefer poison for the hand (Roulettes) but never ammo
            int key = (ckind(t) == K_ROUL) ? -10 : (drawval(t) ? 10 + drawval(t) : 0);
            if (bad_idx < 0 || key < bad_rank) { bad_rank = key; bad_idx = i; }
        } else if (r > good_rank) { good_rank = r; good_idx = i; }
    }
    if (G->draw_ctx == 2) return bad_idx >= 0 ? bad_idx : n - 1;
    if (good_idx < 0) return bad_idx >= 0 ? bad_idx : n - 1;       // nothing stops the draw
    if (bad_idx >= 0 && nbad >= need) return bad_idx;               // a knockout is available
    if (G->draw_ctx == 3 && bad_idx >= 0) return bad_idx;           // Roulette: bloat the hand
    return good_idx;                                                // force the nastiest card
}

static int draw_one(Game *G, int p) {
    if (G->pn == 0) reshuffle(G);
    if (G->pn == 0) return -1;
    if (adv_nature && G->pn > 1 && G->draw_ctx) {
        int i = nature_pick(G, p);
        uint8_t tmp = G->pile[i]; G->pile[i] = G->pile[G->pn - 1]; G->pile[G->pn - 1] = tmp;
    }
    int t = G->pile[--G->pn];
    G->hand[p][t]++;
    G->hsize[p]++;
    G->draws++;
    G->stuck_run = 0;
    if (G->hsize[p] > G->max_hand_seen) G->max_hand_seen = G->hsize[p];
    if (G->R->mercy_immediate && G->hsize[p] >= G->R->mercy) {
        eliminate(G, p);
        return -2;
    }
    return t;
}

static int end_of_action_mercy(Game *G, int p) {
    if (!G->R->mercy_immediate && G->alive[p] && G->hsize[p] >= G->R->mercy) {
        eliminate(G, p);
        return 1;
    }
    return 0;
}

// Draw n cards (penalty). Returns 1 if the player was eliminated.
static int draw_n(Game *G, int p, int n) {
    for (int i = 0; i < n; i++) {
        int r = draw_one(G, p);
        if (r == -2) return 1;
        if (r == -1) break; // nothing left anywhere
    }
    return end_of_action_mercy(G, p);
}

static inline int playable(const Game *G, int t) {
    int c = ccolor(t);
    if (c == WILD) return 1;
    if (c == G->color) return 1;
    int tk = ckind(G->top);
    if (tk < 16 && ckind(t) == tk) return 1;
    return 0;
}

static inline int stackable(const Game *G, int t) {
    int v = drawval(t);
    if (v == 0 || v < G->stackv) return 0;
    if (G->R->stack_rule == 1) {
        int c = ccolor(t);
        if (c == WILD) return 1;
        if (c == G->color) return 1;
        if (ckind(G->top) < 16 && ckind(t) == ckind(G->top)) return 1;
        return 0;
    }
    return 1;
}

// ----------------------------------------------------------------------------
// Policy helpers
// ----------------------------------------------------------------------------
static void play_card(Game *G, int p, int t);
static int collude_play(Game *G, int p, const int *opts, int n);
static int collude_stack(Game *G, int p, const int *opts, int n);
static int mcwin_play(Game *G, int p, const int *opts, int n);
static int mcwin_stack(Game *G, int p, const int *opts, int n);
static int collude_roulette_color(Game *G, int victim);
static int persona_play(Game *G, int p, const int *opts, int n);
static int persona_stack(Game *G, int p, const int *opts, int n);
static int color_counts(const Game *G, int p, int cc[4]) {
    cc[0] = cc[1] = cc[2] = cc[3] = 0;
    for (int t = 0; t < 64; t++) cc[t >> 4] += G->hand[p][t];
    return cc[0] + cc[1] + cc[2] + cc[3];
}

static int argmax4_rand(Rng *r, const int v[4]) {
    int best = v[0];
    for (int i = 1; i < 4; i++) if (v[i] > best) best = v[i];
    int idx[4], n = 0;
    for (int i = 0; i < 4; i++) if (v[i] == best) idx[n++] = i;
    return idx[rng_below(r, n)];
}
static int argmin4_rand(Rng *r, const int v[4]) {
    int best = v[0];
    for (int i = 1; i < 4; i++) if (v[i] < best) best = v[i];
    int idx[4], n = 0;
    for (int i = 0; i < 4; i++) if (v[i] == best) idx[n++] = i;
    return idx[rng_below(r, n)];
}

// Count of each color among cards this player cannot see (draw pile + other hands).
static void unseen_color_counts(const Game *G, int p, int cc[4]) {
    int tot[4] = {PER_COLOR, PER_COLOR, PER_COLOR, PER_COLOR};
    for (int t = 0; t < 64; t++) tot[t >> 4] -= G->hand[p][t] + G->disc[t];
    if (G->top < 64) tot[G->top >> 4]--;
    for (int i = 0; i < 4; i++) cc[i] = tot[i];
}

// ---- color choice after playing a wild --------------------------------------
static int choose_color(Game *G, int p) {
    G->nchoices++;
    if (G->force_color >= 0) { int c = G->force_color; G->force_color = -1; return c; }
    int pol = G->pol[p];
    if (pol == POL_RANDOM || pol == POL_RANDOMV || pol == POL_GREMLIN) return (int)rng_below(G->rng, 4);
    int cc[4];
    color_counts(G, p, cc);
    return argmax4_rand(G->rng, cc);
}

// ---- 7: swap target ---------------------------------------------------------
static int choose_swap(Game *G, int p) {
    if (G->nalive > 2) G->nchoices++;
    if (G->force_target >= 0) { int q = G->force_target; G->force_target = -1; return q; }
    int opts[MAXP], n = 0;
    for (int q = 0; q < G->np; q++) if (q != p && G->alive[q]) opts[n++] = q;
    int pol = G->pol[p];
    if (pol == POL_RANDOM || pol == POL_RANDOMV) return opts[rng_below(G->rng, n)];
    if (n == 0) return p; // unreachable: at least two players are alive during play
    if (pol == POL_GREMLIN) return opts[rng_below(G->rng, n)];
    if (pol == POL_GRUDGE) {
        int g = G->last_hitter[p];
        if (g >= 0 && g != p && G->alive[g]) return g;
    }
    if (pol == POL_PEACE || pol == POL_STALLER) { // take on the biggest burden / even things out
        int best = opts[0];
        for (int i = 1; i < n; i++) if (G->hsize[opts[i]] > G->hsize[best]) best = opts[i];
        if (pol == POL_PEACE) return best;
        int bd = 1 << 30;
        for (int i = 0; i < n; i++) {
            int d = abs(G->hsize[opts[i]] - G->hsize[p]);
            if (d < bd) { bd = d; best = opts[i]; }
        }
        return best;
    }
    // greedy (and the look-ahead policies when not forced): take the smallest hand
    int best = opts[0], nties = 1;
    for (int i = 1; i < n; i++) {
        if (G->hsize[opts[i]] < G->hsize[best]) { best = opts[i]; nties = 1; }
        else if (G->hsize[opts[i]] == G->hsize[best] && rng_below(G->rng, (uint32_t)++nties) == 0) best = opts[i];
    }
    return best;
}

// ---- Color Roulette color -----------------------------------------------------
static int choose_roulette_color(Game *G, int chooser, int victim) {
    G->nchoices++;
    int pol = G->pol[chooser];
    if (pol == POL_COLLUDE && chooser == victim) return collude_roulette_color(G, victim);
    if (pol == POL_RANDOM || pol == POL_RANDOMV) return (int)rng_below(G->rng, 4);
    if (IS_PERSONA(pol) && !persona_of(pol)->smart) {
        int cc[4];
        color_counts(G, chooser, cc); // a casual player names the colour they hold most of
        return argmax4_rand(G->rng, cc);
    }
    int uc[4];
    unseen_color_counts(G, chooser, uc);
    if (chooser == victim) return argmax4_rand(G->rng, uc); // fewest flips
    return argmin4_rand(G->rng, uc);                                               // most flips
}

// With exactly 2 players, is playing Wild Reverse Draw 4 card t a pure self-penalty for p
// (no other Draw Card of value >= 4 left in hand to pass the total back)?
static int wrd4_selfish(const Game *G, int p, int t) {
    if (ckind(t) != K_WRD4 || G->nalive != 2 || !G->R->wrd4_2p_self) return 0;
    for (int u = 0; u < NT; u++) {
        int m = G->hand[p][u] - (u == t);
        if (m > 0 && drawval(u) >= 4) return 0;
    }
    return 1;
}

// ---- facing a stack: returns card type to stack, or -1 to accept -------------
static int choose_stack(Game *G, int p, const int *opts, int n) {
    if (n >= 1) G->nchoices++;
    int pol = G->pol[p];
    if (n == 0) return -1;
    if (pol == POL_COLLUDE) return collude_stack(G, p, opts, n);
    if (pol == POL_MCWIN) return mcwin_stack(G, p, opts, n);
    if (IS_PERSONA(pol)) return persona_stack(G, p, opts, n);
    if (pol == POL_RANDOM || pol == POL_RANDOMV) {
        int k = (int)rng_below(G->rng, (uint32_t)(n + 1));
        return k == n ? -1 : opts[k];
    }
    // greedy: always stack, using the smallest sufficient draw card (prefer colored over wild).
    // With 2 players a Wild Reverse Draw 4 comes straight back to its player, so it is only used
    // when another +4-or-better card is left to send the total on.
    int best = -1;
    for (int i = 0; i < n; i++) {
        if (wrd4_selfish(G, p, opts[i])) continue;
        if (best < 0) { best = opts[i]; continue; }
        int a = drawval(opts[i]), b = drawval(best);
        if (a < b || (a == b && ccolor(best) == WILD && ccolor(opts[i]) != WILD)) best = opts[i];
    }
    return best;
}

// ---- normal play: returns card type, or -1 to (voluntarily) draw ------------
static int greedy_score(Game *G, int p, int t) {
    int k = ckind(t), c = ccolor(t);
    int h = G->hsize[p];
    int nxt = next_alive(G, p, G->dir);
    int nh = G->hsize[nxt];
    int s = 0;
    if (h == 1) return 1000000; // winning play
    if (k == K_DISCALL) {
        int cnt = 0;
        for (int kk = 0; kk < 16; kk++) cnt += G->hand[p][c * 16 + kk];
        if (cnt == h) return 900000; // discards whole hand: win
        s += 40 * cnt;
    }
    int cc[4];
    color_counts(G, p, cc);
    if (c != WILD) s += 5 * cc[c]; // keep the color we are long in
    int v = drawval_kind(k);
    if (wrd4_selfish(G, p, t)) s -= 200;          // 2 players: it would hit ourselves
    else if (v) s += 10 * v + (nh <= 3 ? 60 : 0);
    if (k == K_SKIP || k == K_SKIPALL) s += (nh <= 3 ? 50 : 15);
    if (k == K_REV) s += 10;
    if (c == WILD) s -= 30 + (v ? 0 : 0); // save wilds for when needed
    if (k == 7 && G->R->zero_seven) {
        int mn = 1 << 30;
        for (int q = 0; q < G->np; q++) if (q != p && G->alive[q] && G->hsize[q] < mn) mn = G->hsize[q];
        s += (mn < h - 1) ? 20 * (h - 1 - mn) : -40;
    }
    if (k == 0 && G->R->zero_seven) {
        int prv = next_alive(G, p, -G->dir);
        s += (G->hsize[prv] < h - 1) ? 15 * (h - 1 - G->hsize[prv]) : -30;
    }
    return s;
}

// ---- personality players ------------------------------------------------------
static double persona_score(Game *G, int p, int t, const Persona *P) {
    int k = ckind(t), c = ccolor(t);
    int h = G->hsize[p];
    int nxt = next_alive(G, p, G->dir);
    int nh = G->hsize[nxt];
    double s = 0.0;
    if (h == 1) return P->stall ? -1e6 : 1e6; // playing the last card wins
    if (k == K_DISCALL) {
        int cnt = 0;
        for (int kk = 0; kk < 16; kk++) cnt += G->hand[p][c * 16 + kk];
        if (cnt == h) return P->stall ? -1e6 : 9e5;
        s += (P->stall ? -30.0 : 40.0) * cnt;
    }
    int cc[4];
    color_counts(G, p, cc);
    if (c != WILD) s += 5.0 * cc[c];
    int v = drawval_kind(k);
    int target = nxt;
    if (k == K_WRD4) target = G->nalive == 2 ? p : next_alive(G, p, -G->dir);
    int th = G->hsize[target];
    if (wrd4_selfish(G, p, t)) s -= 200;
    else if (v) {
        s += P->attack * v + (th <= 3 ? P->leader : 0.0);
        if (G->last_hitter[p] == target) s += P->grudge;
        if (th + v >= G->R->mercy - 4) s -= P->mercy;            // might knock them out
        if (P->stall) s += (th <= 3 ? 60.0 : -20.0 * v);          // top up small hands only
    }
    if (k == K_SKIP || k == K_SKIPALL) {
        s += (nh <= 3 ? P->leader * 0.6 : 0.0) + P->attack;
        if (G->last_hitter[p] == nxt) s += P->grudge * 0.5;
    }
    if (c == WILD) s -= P->wild_keep;
    if (k == K_WD10 || k == K_ROUL || k == 0 || k == 7 || k == K_SKIPALL) s += P->chaos;
    if (k == K_ROUL) {
        s += (nh <= 3 ? P->leader : 0.0) + (G->last_hitter[p] == nxt ? P->grudge : 0.0);
        if (nh >= 15) s -= P->mercy;
        if (P->stall) s += nh <= 3 ? 20.0 : -300.0;
    }
    if (k == 7 && G->R->zero_seven) {
        int mn = 1 << 30;
        for (int q = 0; q < G->np; q++) if (q != p && G->alive[q] && G->hsize[q] < mn) mn = G->hsize[q];
        if (!P->stall) s += (mn < h - 1) ? 20.0 * (h - 1 - mn) : -40.0;
    }
    if (k == 0 && G->R->zero_seven && !P->stall) {
        int prv = next_alive(G, p, -G->dir);
        s += (G->hsize[prv] < h - 1) ? 15.0 * (h - 1 - G->hsize[prv]) : -30.0;
    }
    if (P->stall && h <= 3) s -= 50.0 * (4 - h); // keep own hand from shrinking to nothing
    return s + P->noise * rng_unif(G->rng);
}

static int persona_play(Game *G, int p, const int *opts, int n) {
    const Persona *P = persona_of(G->pol[p]);
    int best = opts[0];
    double bs = -1e300;
    for (int i = 0; i < n; i++) {
        double sc = persona_score(G, p, opts[i], P);
        if (sc > bs) { bs = sc; best = opts[i]; }
    }
    return best;
}

static int persona_stack(Game *G, int p, const int *opts, int n) {
    const Persona *P = persona_of(G->pol[p]);
    int total = G->stack;
    int dies = G->hsize[p] + total >= G->R->mercy;
    int cand[NT], m = 0;
    for (int i = 0; i < n; i++) if (!wrd4_selfish(G, p, opts[i])) cand[m++] = opts[i];
    if (m == 0) return -1;
    if (!dies) {
        if (P->stall && G->hsize[p] + total <= 20) return -1;   // happy to absorb it
        if (rng_unif(G->rng) >= P->stack_p) return -1;
    }
    int best = cand[0];
    for (int i = 1; i < m; i++) {
        int a = drawval(cand[i]), b = drawval(best);
        if (G->pol[p] == POL_GREMLIN ? a > b : a < b) best = cand[i]; // the gremlin goes big
    }
    return best;
}

static int choose_play(Game *G, int p, const int *opts, int n, int allow_draw) {
    if (n + (allow_draw ? 1 : 0) >= 2) G->nchoices++;
    int pol = G->pol[p];
    if (pol == POL_COLLUDE) return collude_play(G, p, opts, n);
    if (pol == POL_MCWIN) return mcwin_play(G, p, opts, n);
    if (IS_PERSONA(pol)) return persona_play(G, p, opts, n);
    if (pol == POL_RANDOM) return opts[rng_below(G->rng, n)];
    if (pol == POL_RANDOMV) {
        if (allow_draw) {
            int k = (int)rng_below(G->rng, (uint32_t)(n + 1));
            return k == n ? -1 : opts[k];
        }
        return opts[rng_below(G->rng, n)];
    }
    // highest score; ties broken uniformly (reservoir sampling)
    int best = -1, bs = 0, nties = 0;
    for (int i = 0; i < n; i++) {
        int s = greedy_score(G, p, opts[i]);
        if (best < 0 || s > bs) { bs = s; best = opts[i]; nties = 1; }
        else if (s == bs && rng_below(G->rng, (uint32_t)++nties) == 0) best = opts[i];
    }
    return best;
}

static int choose_after_draw(Game *G, int p, int t) {
    int pol = G->pol[p];
    if (G->R->after_draw == 0) return 1;
    if (G->R->after_draw == 2) return 0;
    if (pol == POL_RANDOM || pol == POL_RANDOMV) return (int)rng_below(G->rng, 2);
    (void)t;
    return 1;
}

// ----------------------------------------------------------------------------
// Playing a card
// ----------------------------------------------------------------------------
static void rotate_hands(Game *G, int p) {
    // every alive player passes their hand to the next alive player in the direction of play
    static __thread uint8_t tmp[MAXP][NT];
    static __thread int ts[MAXP];
    for (int q = 0; q < G->np; q++) if (G->alive[q]) {
        int r = next_alive(G, q, G->dir);
        memcpy(tmp[r], G->hand[q], NT);
        ts[r] = G->hsize[q];
    }
    for (int q = 0; q < G->np; q++) if (G->alive[q]) {
        memcpy(G->hand[q], tmp[q], NT);
        G->hsize[q] = ts[q];
    }
    (void)p;
}

static void swap_hands(Game *G, int a, int b) {
    uint8_t tmp[NT];
    memcpy(tmp, G->hand[a], NT);
    memcpy(G->hand[a], G->hand[b], NT);
    memcpy(G->hand[b], tmp, NT);
    int s = G->hsize[a]; G->hsize[a] = G->hsize[b]; G->hsize[b] = s;
}

// Player p plays card t (already verified legal). Sets G->cur to whoever moves next.
static void play_card(Game *G, int p, int t) {
    G->stuck_run = 0;
    G->hand[p][t]--;
    G->hsize[p]--;
    G->disc[G->top]++;
    G->dn++;
    G->top = t;
    G->plays++;
    int k = ckind(t), c = ccolor(t);
    if (c == WILD) {
        if (k != K_ROUL) G->color = choose_color(G, p); // Roulette's colour is named below
    } else {
        G->color = c;
    }
    if (k == K_DISCALL) {
        for (int kk = 0; kk < 16; kk++) {
            int tt = c * 16 + kk;
            int m = G->hand[p][tt];
            if (m) {
                G->hand[p][tt] = 0;
                G->hsize[p] -= m;
                G->disc[tt] += m;
                G->dn += m;
            }
        }
    }
    if (G->hsize[p] == 0) { // "When a player plays their final card, they win." (effects not applied)
        end_game(G, p, 1);
        return;
    }
    int v = drawval_kind(k);
    switch (k) {
    case K_D2: case K_D4: case K_WD6: case K_WD10:
        G->stack_last = p;
        G->stack += v;
        G->stackv = v;
        if (G->stack > G->max_stack) G->max_stack = G->stack;
        G->cur = next_alive(G, p, G->dir);
        break;
    case K_WRD4:
        G->stack_last = p;
        G->stack += v;
        G->stackv = v;
        if (G->stack > G->max_stack) G->max_stack = G->stack;
        if (G->nalive == 2 && G->R->wrd4_2p_self) {
            // reverse acts as a skip with two players, so the "next player in the new direction" is p
            G->dir = -G->dir;
            G->cur = p;
            break;
        }
        if (G->R->wrd4_victim == 0) G->dir = -G->dir;
        G->cur = next_alive(G, p, G->dir);
        if (G->R->wrd4_victim == 1) G->dir = -G->dir;
        break;
    case K_SKIP:
        G->cur = next_alive(G, next_alive(G, p, G->dir), G->dir);
        break;
    case K_SKIPALL:
        G->cur = p;
        break;
    case K_REV:
        G->dir = -G->dir;
        if (G->nalive == 2 && G->R->reverse2p_skip) G->cur = p;
        else G->cur = next_alive(G, p, G->dir);
        break;
    case K_ROUL: {
        int victim = next_alive(G, p, G->dir);
        G->last_hitter[victim] = p;
        G->turns++; // the victim's (lost) turn: they name a colour and reveal cards
        int chooser = G->R->roulette_chooser == 0 ? victim : p;
        int col = choose_roulette_color(G, chooser, victim);
        G->color = col;
        G->roulettes++;
        int elim = 0;
        for (;;) {
            G->draw_ctx = 3;
            int d = draw_one(G, victim);
            G->draw_ctx = 0;
            if (d == -2) { elim = 1; break; }
            if (d == -1) break; // no cards anywhere: stop flipping
            if (ccolor(d) == col) break;
        }
        if (!elim) elim = end_of_action_mercy(G, victim);
        if (G->over) return;
        // victim's turn is over
        G->cur = next_alive(G, victim, G->dir);
        break;
    }
    case 0:
        if (G->R->zero_seven) { rotate_hands(G, p); G->zeros++; }
        G->cur = next_alive(G, p, G->dir);
        break;
    case 7:
        if (G->R->zero_seven) {
            int q = choose_swap(G, p);
            swap_hands(G, p, q);
            G->sevens++;
        }
        G->cur = next_alive(G, p, G->dir);
        break;
    default:
        G->cur = next_alive(G, p, G->dir);
        break;
    }
}

// ----------------------------------------------------------------------------
// Colluding "prolonger" policy (all players cooperate to make the game last).
// Full information about every hand and about the draw-pile COMPOSITION (never its order).
// ----------------------------------------------------------------------------
static inline int playable_on(int t, int top, int col) {
    int c = ccolor(t);
    if (c == WILD) return 1;
    if (c == col) return 1;
    int tk = ckind(top);
    if (tk < 16 && ckind(t) == tk) return 1;
    return 0;
}

// P(the first m cards of a uniformly shuffled n-card pile are all "bad"), bad cards = 'bad'
static int worst_case = 0; // colluders assume nature picks the worst card (adversarial risk model)
static double p_first_bad(int bad, int n, int m) {
    if (m <= 0) return 1.0;
    if (bad < m) return 0.0;
    if (worst_case) return 1.0;
    double pr = 1.0;
    for (int i = 0; i < m; i++) pr *= (double)(bad - i) / (double)(n - i);
    return pr;
}

// A player with h cards draws one card at a time until a "good" card; the k-th card drawn
// (k = mercy - h) knocks them out even if it is good. good_pile/pn: good cards / size of the
// draw pile; good_disc/dn: same for the discard pile that is reshuffled when the pile runs out.
static double seq_death(const Game *G, int h, int good_pile, int pn, int good_disc, int dn) {
    int k = G->R->mercy - h;
    if (k <= 1) return 1.0;
    if (pn > 0 && good_pile > 0) return p_first_bad(pn - good_pile, pn, k - 1);
    if (pn >= k - 1) return 1.0;
    if (good_disc > 0) return p_first_bad(dn - good_disc, dn, k - 1 - pn);
    return 1.0;
}

// expected number of bad cards drawn before the first good one (pile only; approximation)
static double seq_expected_bad(int good_pile, int pn) {
    if (good_pile <= 0) return (double)pn;
    return (double)(pn - good_pile) / (double)(good_pile + 1);
}

static double dup_death_G(const Game *G, int q) {
    int gp = 0, gd = 0;
    for (int i = 0; i < G->pn; i++) gp += playable_on(G->pile[i], G->top, G->color);
    for (int t = 0; t < NT; t++) if (G->disc[t] && playable_on(t, G->top, G->color)) gd += G->disc[t];
    return seq_death(G, G->hsize[q], gp, G->pn, gd, G->dn);
}
static double dup_growth_G(const Game *G) {
    int gp = 0;
    for (int i = 0; i < G->pn; i++) gp += playable_on(G->pile[i], G->top, G->color);
    return seq_expected_bad(gp, G->pn);
}

static void roul_stats(const Game *G, int q, int c, double *death, double *growth) {
    int gp = 0, gd = 0;
    for (int i = 0; i < G->pn; i++) gp += (ccolor(G->pile[i]) == c);
    for (int k = 0; k < 16; k++) gd += G->disc[c * 16 + k];
    *death = seq_death(G, G->hsize[q], gp, G->pn, gd, G->dn);
    *growth = seq_expected_bad(gp, G->pn) + 1.0;
}

static int collude_roulette_color(Game *G, int victim) {
    double best = 1e18;
    int bc = 0;
    int h = G->hsize[victim];
    for (int c = 0; c < 4; c++) {
        double d, g;
        roul_stats(G, victim, c, &d, &g);
        // small hands like a few extra cards; big hands want as few as possible
        double target = h <= 4 ? 5.0 : 0.0;
        double sc = d * 1e6 + fabs(h + g - (h + target)) + rng_unif(G->rng) * 1e-3;
        if (sc < best) { best = sc; bc = c; }
    }
    return bc;
}

// Risk that the pending stack (already on G) kills someone, assuming colluding responses.
static double stack_risk(const Game *G, int q, int dir, int S, int v, int depth) {
    int mercy = G->R->mercy;
    double acc = (G->hsize[q] + S >= mercy) ? 1.0 : 0.0;
    if (acc == 0.0 || depth >= 5 || G->R->stack_rule == 2) return acc;
    double best = acc;
    for (int t = 0; t < NT && best > 0.0; t++) {
        if (!G->hand[q][t]) continue;
        int w = drawval(t);
        if (!w || w < v) continue;
        if (G->hsize[q] == 1) continue; // stacking the last card would win the game
        int ndir = dir, nq;
        if (ckind(t) == K_WRD4) {
            ndir = -dir;
            nq = (G->nalive == 2 && G->R->wrd4_2p_self) ? q : next_alive(G, q, ndir);
        } else {
            nq = next_alive(G, q, dir);
        }
        double r = stack_risk(G, nq, ndir, S + w, w, depth + 1);
        if (r < best) best = r;
    }
    return best;
}

// Hand-size comfort: colluders dislike tiny hands (forced wins) and huge hands (mercy).
static int band_lo = 4, band_hi = 14;
static double hand_pen(int h) {
    if (h <= 0) return 1e5;
    if (h == 1) return 400;
    if (h == 2) return 120;
    if (h < band_lo) return 30.0 * (band_lo - h);
    if (h <= band_hi) return 0;
    if (h <= band_hi + 4) return (h - band_hi) * 15.0;
    return 60.0 + (h - band_hi - 4) * 60.0;
}

static double poison_w_roul = 40, poison_w_d10 = 25, poison_w_d6 = 12, poison_w_wrd4 = 4;
// Colluders dislike holding cards that may later be FORCED onto a neighbour.
static double insure_w = 0.0;
static double poison_pen(const Game *G, int p) {
    const uint8_t *h = G->hand[p];
    double w = poison_w_roul * h[64 + 3] + poison_w_d10 * h[64 + 2] + poison_w_d6 * h[64 + 1] + poison_w_wrd4 * h[64 + 0];
    int plain = G->hsize[p] - h[64] - h[65] - h[66] - h[67];
    if (plain <= 3) w *= 2.0;
    // "insurance": a non-Roulette wild in hand guarantees a playable card (no forced draw-until-playable)
    if (insure_w > 0.0 && h[64] + h[65] + h[66] + h[68] == 0) w += insure_w;
    return w;
}

// Evaluate the position G (the move has been made; G->cur is about to act).
// depth > 0: the player to act (a colluder) picks its least risky reply, searched recursively
// through deterministic plays; random events (draws) end the search with their exact risk.
static int search_depth = 1;
static double risk_w = 1e6;
static int phantom_search = 1;
#define MAXD 4
static void eval_pos(const Game *G, int depth, double *risk, double *comfort);

static void eval_leaf(const Game *G, double *risk, double *comfort) {
    double c = 0.0;
    if (G->over) { *risk = 1.0; *comfort = -1e6; return; }
    int q = G->cur;
    double r = 0.0;
    double grow_q = 0.0;
    if (G->stack > 0) {
        r = stack_risk(G, q, G->dir, G->stack, G->stackv, 0);
        if (G->hsize[q] + G->stack < G->R->mercy) grow_q = G->stack; // colluder q usually accepts small stacks
    } else {
        int any = 0;
        for (int t = 0; t < NT; t++) if (G->hand[q][t] && playable_on(t, G->top, G->color)) { any = 1; break; }
        if (any) {
            if (G->hsize[q] == 1) r = 1.0; // forced to play the last card
        } else {
            r = dup_death_G(G, q);
            grow_q = dup_growth_G(G);
        }
    }
    for (int p = 0; p < G->np; p++) {
        if (!G->alive[p]) continue;
        double h = G->hsize[p] + (p == q ? grow_q : 0.0);
        int hi = (int)(h + 0.5);
        if (hi > 24) hi = 24;
        c -= hand_pen(hi) + poison_pen(G, p);
    }
    *risk = r;
    *comfort = c;
}

static void eval_pos(const Game *G, int depth, double *risk, double *comfort) {
    static __thread Game buf[MAXD + 1];
    if (G->over) { *risk = 1.0; *comfort = -1e6; return; }
    if (depth <= 0) { eval_leaf(G, risk, comfort); return; }
    int q = G->cur;
    int opts[NT], n = 0;
    double best_r = 2.0, best_c = -1e300;
    Game *B = &buf[depth];
    if (G->stack > 0) {
        // accept: the drawn cards are unknown, so they are added as "phantom" cards that
        // count toward the hand size but can never be played (pessimistic), and the search
        // continues with the next player.
        if (G->hsize[q] + G->stack < G->R->mercy) {
            if (phantom_search) {
                *B = *G;
                B->hsize[q] += B->stack;
                B->stack = 0;
                B->stackv = 0;
                B->cur = next_alive(B, q, B->dir);
                eval_pos(B, depth - 1, &best_r, &best_c);
            } else {
                double c = 0.0;
                for (int p = 0; p < G->np; p++) if (G->alive[p]) {
                    int h = G->hsize[p] + (p == q ? G->stack : 0);
                    c -= hand_pen(h > 24 ? 24 : h) + poison_pen(G, p);
                }
                best_r = 0.0; best_c = c;
            }
        } else best_r = 1.0;
        if (G->R->stack_rule != 2)
            for (int t = 0; t < NT; t++) if (G->hand[q][t] && drawval(t) && drawval(t) >= G->stackv) opts[n++] = t;
    } else {
        for (int t = 0; t < NT; t++) if (G->hand[q][t] && playable_on(t, G->top, G->color)) opts[n++] = t;
        if (n == 0) { eval_leaf(G, risk, comfort); return; } // draw-until-playable: random
        if (G->hsize[q] == 1) { *risk = 1.0; *comfort = -1e6; return; }
    }
    int others[MAXP], no = 0;
    for (int p = 0; p < G->np; p++) if (p != q && G->alive[p]) others[no++] = p;
    for (int i = 0; i < n; i++) {
        int t = opts[i], k = ckind(t);
        if (k == K_ROUL) {
            int vq = next_alive(G, q, G->dir);
            double bd = 1.0, bg = 0.0;
            for (int c = 0; c < 4; c++) { double d, g; roul_stats(G, vq, c, &d, &g); if (d < bd) { bd = d; bg = g; } }
            double c = 0.0;
            for (int p = 0; p < G->np; p++) if (G->alive[p]) {
                int h = G->hsize[p] - (p == q) + (p == vq ? (int)(bg + 0.5) : 0);
                c -= hand_pen(h > 24 ? 24 : h);
            }
            if (bd < best_r || (bd == best_r && c > best_c)) { best_r = bd; best_c = c; }
            continue;
        }
        int ncol = ccolor(t) == WILD ? 4 : 1;
        int ntg = (k == 7 && G->R->zero_seven && G->stack == 0) ? no : 1;
        for (int ci = 0; ci < ncol; ci++)
            for (int ti = 0; ti < ntg; ti++) {
                *B = *G;
                B->force_color = ncol == 4 ? ci : -1;
                B->force_target = ntg > 1 ? others[ti] : -1;
                play_card(B, q, t);
                double r, c;
                eval_pos(B, depth - 1, &r, &c);
                if (r < best_r || (r == best_r && c > best_c)) { best_r = r; best_c = c; }
                if (best_r == 0.0 && depth > 1) { /* good enough at inner levels */ }
            }
    }
    *risk = best_r > 1.0 ? 1.0 : best_r;
    *comfort = best_c;
}

static void eval_after(const Game *G, double *risk, double *comfort) { eval_pos(G, search_depth, risk, comfort); }

typedef struct { int t, col, tgt; double score; } Macro;

// Score every macro-action (card, wild colour, 7-target) with the one-step risk model.
static int collude_enumerate(Game *G, int p, const int *opts, int n, Macro *out) {
    static __thread Game G2;
    int nm = 0;
    int others[MAXP], no = 0;
    for (int q = 0; q < G->np; q++) if (q != p && G->alive[q]) others[no++] = q;
    for (int i = 0; i < n; i++) {
        int t = opts[i];
        int k = ckind(t);
        int ncol = ccolor(t) == WILD && k != K_ROUL ? 4 : 1;
        int ntg = (k == 7 && G->R->zero_seven) ? no : 1;
        for (int ci = 0; ci < ncol; ci++) {
            for (int ti = 0; ti < ntg; ti++) {
                double risk, comfort;
                if (k == K_ROUL) {
                    int vq = next_alive(G, p, G->dir);
                    double bd = 1.0, bg = 0.0;
                    for (int c = 0; c < 4; c++) {
                        double d, g;
                        roul_stats(G, vq, c, &d, &g);
                        if (d < bd) { bd = d; bg = g; }
                    }
                    risk = bd;
                    comfort = 0.0;
                    for (int q = 0; q < G->np; q++) if (G->alive[q]) {
                        int h = G->hsize[q] - (q == p) + (q == vq ? (int)(bg + 0.5) : 0);
                        if (h > 24) h = 24;
                        comfort -= hand_pen(h);
                    }
                    if (G->hsize[p] == 1) risk = 1.0;
                } else {
                    G2 = *G;
                    G2.force_color = ncol == 4 ? ci : -1;
                    G2.force_target = ntg > 1 ? others[ti] : -1;
                    play_card(&G2, p, t);
                    eval_after(&G2, &risk, &comfort);
                }
                Macro m = {t, ncol == 4 ? ci : -1, ntg > 1 ? others[ti] : -1, -risk * risk_w + comfort};
                out[nm++] = m;
            }
        }
    }
    return nm;
}

static int collude_play(Game *G, int p, const int *opts, int n) {
    static __thread Macro ms[NT * 4 * MAXP];
    int nm = collude_enumerate(G, p, opts, n, ms);
    double best = -1e300;
    int bi = 0;
    for (int i = 0; i < nm; i++) {
        double sc = ms[i].score + rng_unif(G->rng) * 1e-3;
        if (sc > best) { best = sc; bi = i; }
    }
    G->force_color = ms[bi].col;
    G->force_target = ms[bi].tgt;
    return ms[bi].t;
}

static int collude_stack_enumerate(Game *G, int p, const int *opts, int n, Macro *out) {
    static __thread Game G2;
    double risk, comfort;
    int nm = 0;
    {
        int total = G->stack;
        double sc;
        if (G->hsize[p] + total >= G->R->mercy) sc = -risk_w;
        else if (phantom_search) {
            G2 = *G;
            G2.hsize[p] += total;
            G2.stack = 0;
            G2.stackv = 0;
            G2.cur = next_alive(&G2, p, G2.dir);
            eval_pos(&G2, search_depth, &risk, &comfort);
            sc = -risk * risk_w + comfort;
        } else {
            comfort = 0.0;
            for (int q = 0; q < G->np; q++) if (G->alive[q]) {
                int h = G->hsize[q] + (q == p ? total : 0);
                comfort -= hand_pen(h > 24 ? 24 : h);
            }
            sc = comfort;
        }
        Macro m = {-1, -1, -1, sc};
        out[nm++] = m;
    }
    for (int i = 0; i < n; i++) {
        int t = opts[i];
        int ncol = ccolor(t) == WILD ? 4 : 1;
        for (int ci = 0; ci < ncol; ci++) {
            G2 = *G;
            G2.force_color = ncol == 4 ? ci : -1;
            play_card(&G2, p, t);
            eval_after(&G2, &risk, &comfort);
            Macro m = {t, ncol == 4 ? ci : -1, -1, -risk * risk_w + comfort};
            out[nm++] = m;
        }
    }
    return nm;
}

static int collude_stack(Game *G, int p, const int *opts, int n) {
    static __thread Macro ms[NT * 4 + 1];
    int nm = collude_stack_enumerate(G, p, opts, n, ms);
    double best = -1e300;
    int bi = 0;
    for (int i = 0; i < nm; i++) {
        double sc = ms[i].score + rng_unif(G->rng) * 1e-3;
        if (sc > best) { best = sc; bi = i; }
    }
    G->force_color = ms[bi].col;
    return ms[bi].t;
}

static void take_turn(Game *G);

// ---- Competitive Monte-Carlo player ("mcwin") ----------------------------------
// Determinized rollouts: the unseen cards (draw pile + opponents' hands) are re-dealt at
// random consistent with the known hand sizes, the candidate move is applied, and the game is
// played out with every seat using the greedy policy. The move with the most wins is chosen.
// Common random numbers: rollout r uses the same determinization for every candidate.
static int mcw_R = 48;
static void determinize(Game *G2, int p) {
    uint8_t pool[DECK];
    int n = 0;
    for (int i = 0; i < G2->pn; i++) pool[n++] = G2->pile[i];
    for (int q = 0; q < G2->np; q++) {
        if (q == p || !G2->alive[q]) continue;
        for (int t = 0; t < NT; t++) { for (int c = 0; c < G2->hand[q][t]; c++) pool[n++] = (uint8_t)t; G2->hand[q][t] = 0; }
    }
    shuffle_u8(G2->rng, pool, n);
    int k = 0;
    for (int q = 0; q < G2->np; q++) {
        if (q == p || !G2->alive[q]) continue;
        for (int c = 0; c < G2->hsize[q]; c++) G2->hand[q][pool[k++]]++;
    }
    G2->pn = 0;
    while (k < n) G2->pile[G2->pn++] = pool[k++];
}

static int mcw_rollout(Game *G, int p, int t, int col, int tgt, uint64_t seed) {
    static __thread Game G2;
    Rng r;
    rng_seed(&r, seed);
    G2 = *G;
    G2.rng = &r;
    determinize(&G2, p);
    for (int q = 0; q < G2.np; q++) G2.pol[q] = POL_GREEDY;
    G2.debug = 0;
    G2.turn_cap = 0;
    if (t < 0) {
        int total = G2.stack;
        G2.stack = 0;
        G2.stackv = 0;
        draw_n(&G2, p, total);
        if (!G2.over) G2.cur = next_alive(&G2, p, G2.dir);
    } else {
        G2.force_color = col;
        G2.force_target = tgt;
        play_card(&G2, p, t);
    }
    long long t0 = G2.turns;
    while (!G2.over && G2.turns - t0 < 20000) take_turn(&G2);
    return G2.over && G2.winner == p;
}

static int mcw_choose(Game *G, int p, Macro *ms, int nm) {
    if (nm == 1) return 0;
    uint64_t base = rng_next(G->rng);
    int best = 0, bw = -1;
    for (int i = 0; i < nm; i++) {
        int w = 0;
        for (int r = 0; r < mcw_R; r++) w += mcw_rollout(G, p, ms[i].t, ms[i].col, ms[i].tgt, base + (uint64_t)r * 0x9E3779B97F4A7C15ULL);
        if (w > bw || (w == bw && ms[i].score > ms[best].score)) { bw = w; best = i; }
    }
    return best;
}

static int mcwin_play(Game *G, int p, const int *opts, int n) {
    static __thread Macro ms[NT * 4 * MAXP];
    int nm = 0;
    int others[MAXP], no = 0;
    for (int q = 0; q < G->np; q++) if (q != p && G->alive[q]) others[no++] = q;
    for (int i = 0; i < n; i++) {
        int t = opts[i], k = ckind(t);
        int ncol = ccolor(t) == WILD && k != K_ROUL ? 4 : 1;
        int ntg = (k == 7 && G->R->zero_seven) ? no : 1;
        for (int ci = 0; ci < ncol; ci++)
            for (int ti = 0; ti < ntg; ti++) {
                Macro m = {t, ncol == 4 ? ci : -1, ntg > 1 ? others[ti] : -1, (double)greedy_score(G, p, t)};
                ms[nm++] = m;
            }
    }
    int bi = mcw_choose(G, p, ms, nm);
    G->force_color = ms[bi].col;
    G->force_target = ms[bi].tgt;
    return ms[bi].t;
}

static int mcwin_stack(Game *G, int p, const int *opts, int n) {
    static __thread Macro ms[NT * 4 + 1];
    int nm = 0;
    Macro acc = {-1, -1, -1, 0.0};
    ms[nm++] = acc;
    for (int i = 0; i < n; i++) {
        int t = opts[i];
        int ncol = ccolor(t) == WILD ? 4 : 1;
        for (int ci = 0; ci < ncol; ci++) { Macro m = {t, ncol == 4 ? ci : -1, -1, 1.0}; ms[nm++] = m; }
    }
    int bi = mcw_choose(G, p, ms, nm);
    G->force_color = ms[bi].col;
    return ms[bi].t;
}

// ----------------------------------------------------------------------------
// One turn
// ----------------------------------------------------------------------------
static void take_turn(Game *G) {
    int p = G->cur;
    int opts[NT] = {0};
    int n = 0;
    G->turns++;
    if (G->stack > 0) {
        if (G->R->stack_rule != 2)
            for (int t = 0; t < NT; t++) if (G->hand[p][t] && stackable(G, t)) opts[n++] = t;
        int t = choose_stack(G, p, opts, n);
        if (t < 0 && n > 0 && G->R->stack_mandatory) t = opts[rng_below(G->rng, n)];
        if (t >= 0) {
            play_card(G, p, t);
            return;
        }
        int total = G->stack;
        G->stack = 0;
        G->stackv = 0;
        G->stacks_accepted++;
        G->last_hitter[p] = G->stack_last;
        G->draw_ctx = 2;
        draw_n(G, p, total);
        G->draw_ctx = 0;
        if (G->over) return;
        G->cur = next_alive(G, p, G->dir); // works whether or not p survived
        return;
    }
    for (int t = 0; t < NT; t++) if (G->hand[p][t] && playable(G, t)) opts[n++] = t;
    int choice = -1;
    if (n > 0) choice = choose_play(G, p, opts, n, G->R->voluntary_draw);
    if (choice >= 0) {
        play_card(G, p, choice);
        return;
    }
    // draw until playable
    G->dup_draw_turns++;
    int d;
    for (;;) {
        G->draw_ctx = 1;
        d = draw_one(G, p);
        G->draw_ctx = 0;
        if (d == -2) { // eliminated
            if (!G->over) G->cur = next_alive(G, p, G->dir);
            return;
        }
        if (d == -1) { // nothing to draw at all (only possible in non-official variants, e.g. no Mercy rule)
            if (end_of_action_mercy(G, p)) { if (!G->over) G->cur = next_alive(G, p, G->dir); return; }
            // the player can neither play nor draw: they pass. If every active player passes twice
            // in a row with nothing changing, the game is stuck forever (a genuinely infinite game).
            if (++G->stuck_run >= 2 * G->nalive) { G->over = 1; G->endcause = 4; G->winner = -1; return; }
            G->cur = next_alive(G, p, G->dir);
            return;
        }
        if (playable(G, d)) break;
    }
    if (end_of_action_mercy(G, p)) { if (!G->over) G->cur = next_alive(G, p, G->dir); return; }
    if (choose_after_draw(G, p, d)) {
        play_card(G, p, d);
        return;
    }
    G->cur = next_alive(G, p, G->dir);
}

static void game_init(Game *G, const Rules *R, Rng *rng, int np, const int *pol) {
    memset(G, 0, sizeof *G);
    G->R = R;
    G->rng = rng;
    G->np = np;
    for (int p = 0; p < np; p++) { G->pol[p] = pol[p]; G->alive[p] = 1; G->elim_turn[p] = -1; }
    G->nalive = np;
    G->force_color = -1;
    G->force_target = -1;
    G->stack_last = -1;
    for (int q = 0; q < MAXP; q++) G->last_hitter[q] = -1;
    int n = 0;
    for (int c = 0; c < 4; c++)
        for (int k = 0; k < 16; k++)
            for (int i = 0; i < COLORED_COUNT[k]; i++) G->pile[n++] = (uint8_t)(c * 16 + k);
    for (int w = 0; w < 5; w++)
        for (int i = 0; i < WILD_COUNT[w]; i++) G->pile[n++] = (uint8_t)(64 + w);
    G->pn = n;
    shuffle_u8(rng, G->pile, n);
    for (int i = 0; i < R->hand_size; i++)
        for (int p = 0; p < np; p++) {
            int t = G->pile[--G->pn];
            G->hand[p][t]++;
            G->hsize[p]++;
        }
    G->dir = 1;
    int dealer = (int)rng_below(rng, np);
    // starting card. Official: "If this card is an Action Card, ignore it and flip over the next card."
    // The ignored cards (wilds included) stay in the discard pile under the new top card.
    for (;;) {
        int t = G->pile[--G->pn];
        if (ckind(t) <= 9) { G->top = t; G->color = ccolor(t); break; }
        G->disc[t]++;
        G->dn++;
    }
    G->cur = next_alive(G, dealer, 1);
    G->max_hand_seen = R->hand_size;
}

static long long card_total(const Game *G) {
    long long s = G->pn + G->dn + 1;
    for (int p = 0; p < G->np; p++) s += G->hsize[p];
    return s;
}

static void check_invariants(Game *G, const char *where) {
    int cnt[NT];
    memset(cnt, 0, sizeof cnt);
    for (int i = 0; i < G->pn; i++) cnt[G->pile[i]]++;
    int dn = 0;
    for (int t = 0; t < NT; t++) { cnt[t] += G->disc[t]; dn += G->disc[t]; }
    cnt[G->top]++;
    for (int p = 0; p < G->np; p++) {
        int hs = 0;
        for (int t = 0; t < NT; t++) { cnt[t] += G->hand[p][t]; hs += G->hand[p][t]; }
        if (hs != G->hsize[p]) { fprintf(stderr, "[%s] hsize mismatch p%d %d vs %d\n", where, p, hs, G->hsize[p]); abort(); }
        if (!G->alive[p] && hs) { fprintf(stderr, "[%s] dead player holds cards\n", where); abort(); }
        if (G->alive[p] && G->R->mercy_immediate && hs >= G->R->mercy) { fprintf(stderr, "[%s] mercy violated\n", where); abort(); }
    }
    if (dn != G->dn) { fprintf(stderr, "[%s] dn mismatch\n", where); abort(); }
    for (int t = 0; t < NT; t++) {
        int want = t < 64 ? COLORED_COUNT[t & 15] : WILD_COUNT[t - 64];
        if (cnt[t] != want) { fprintf(stderr, "[%s] conservation violated for type %d: %d vs %d\n", where, t, cnt[t], want); abort(); }
    }
    if (G->color < 0 || G->color > 3) { fprintf(stderr, "[%s] bad color\n", where); abort(); }
    if (!G->over && !G->alive[G->cur]) { fprintf(stderr, "[%s] current player dead\n", where); abort(); }
    if (card_total(G) != DECK) { fprintf(stderr, "[%s] card total\n", where); abort(); }
}

static void print_state(const Game *G, FILE *f) {
    fprintf(f, "turn %lld cur=%d dir=%d top=%s%s color=%s stack=%d/%d pile=%d disc=%d\n", G->turns, G->cur, G->dir,
            COLOR_NAME[ccolor(G->top)], KIND_NAME[ckind(G->top)], COLOR_NAME[G->color], G->stack, G->stackv, G->pn, G->dn);
    for (int p = 0; p < G->np; p++) {
        fprintf(f, "  p%d%s (%2d):", p, G->alive[p] ? " " : "X", G->hsize[p]);
        for (int t = 0; t < NT; t++)
            for (int c = 0; c < G->hand[p][t]; c++) fprintf(f, " %s%s", COLOR_NAME[ccolor(t)], KIND_NAME[ckind(t)]);
        fprintf(f, "\n");
    }
}

static int dump_cap = 0;
static int detect_cycles = 0;
// Hash of the complete state; used only when the draw pile + discard hold <= 2 cards, where
// draws are (almost) forced. A repeated state with no free decision in between is a
// deterministic cycle: the game provably never ends.
static uint64_t state_hash(const Game *G) {
    uint64_t h = 1469598103934665603ULL;
#define MIX(x) do { h ^= (uint64_t)(x); h *= 1099511628211ULL; } while (0)
    for (int p = 0; p < G->np; p++) { MIX(G->alive[p]); for (int t = 0; t < NT; t++) MIX(G->hand[p][t]); }
    for (int t = 0; t < NT; t++) MIX(G->disc[t]);
    for (int i = 0; i < G->pn; i++) MIX(G->pile[i]);
    MIX(G->top); MIX(G->color); MIX(G->cur); MIX(G->dir + 2); MIX(G->stack); MIX(G->stackv); MIX(G->pn); MIX(G->dn);
#undef MIX
    return h;
}
static void play_game(Game *G) {
    if (G->debug) check_invariants(G, "init");
    while (!G->over) {
        if (G->debug >= 2) print_state(G, stderr);
        take_turn(G);
        if (G->debug) check_invariants(G, "turn");
        if (detect_cycles && !G->over && G->pn + G->dn <= 2) {
            uint64_t h = state_hash(G);
            for (int i = 0; i < G->hn && i < 64; i++)
                if (G->hring[i] == h && G->cring[i] == G->nchoices) { G->over = 1; G->endcause = 5; G->winner = -1; break; }
            G->hring[G->hn % 64] = h;
            G->cring[G->hn % 64] = G->nchoices;
            G->hn++;
        }
        if (G->turn_cap && G->turns >= G->turn_cap && !G->over) {
            G->over = 1; G->endcause = 3; G->winner = -1;
            if (dump_cap) {
                flockfile(stderr);
                fprintf(stderr, "=== capped game: pile=%d disc=%d stack=%d draws=%lld plays=%lld\n", G->pn, G->dn, G->stack, G->draws, G->plays);
                print_state(G, stderr);
                for (int k = 0; k < 12 && !0; k++) { G->over = 0; take_turn(G); print_state(G, stderr); }
                G->over = 1;
                funlockfile(stderr);
            }
        }
    }
}

// ----------------------------------------------------------------------------
// Batch driver
// ----------------------------------------------------------------------------
#define HMAX (1 << 20)
static void *xcalloc(size_t n, size_t sz) {
    void *p = calloc(n, sz);
    if (!p) { fprintf(stderr, "out of memory\n"); exit(1); }
    return p;
}
typedef struct {
    // config
    const Rules *R;
    int np;
    int pol[MAXP];
    long long ngames;
    uint64_t seed;
    long long turn_cap;
    int debug;
    // results
    long long *hist; // turns histogram, index = turns (capped at HMAX-1 => overflow)
    long long overflow;
    double sum_t, sum_t2, sum_plays, sum_draws, sum_resh, sum_elims, sum_maxstack, sum_maxhand;
    long long max_t;
    long long endcause[6];
    long long wins_by_seat[MAXP];
    long long wins_by_policy[NPOL];
    long long games_with_elim;
    long long capped;
    double sum_zero, sum_seven, sum_roul, sum_dup;
    long long *overflow_vals;
    long long noverflow_vals;
    long long elim_ctx[4];
} Job;

static void *run_job(void *arg) {
    Job *J = (Job *)arg;
    Rng rng;
    rng_seed(&rng, J->seed);
    J->hist = xcalloc(HMAX, sizeof(long long));
    J->overflow_vals = xcalloc(1 << 16, sizeof(long long));
    Game G;
    for (long long g = 0; g < J->ngames; g++) {
        // no seat rotation is needed: the dealer (and so the first player) is uniformly random
        int pol[MAXP];
        for (int p = 0; p < J->np; p++) pol[p] = J->pol[p];
        game_init(&G, J->R, &rng, J->np, pol);
        G.turn_cap = J->turn_cap;
        G.debug = J->debug;
        play_game(&G);
        long long t = G.turns;
        if (t < HMAX) J->hist[t]++;
        else {
            J->overflow++;
            if (J->noverflow_vals < (1 << 16)) J->overflow_vals[J->noverflow_vals++] = t;
        }
        J->sum_t += (double)t;
        J->sum_t2 += (double)t * (double)t;
        if (t > J->max_t) J->max_t = t;
        J->sum_plays += (double)G.plays;
        J->sum_draws += (double)G.draws;
        J->sum_resh += (double)G.reshuffles;
        J->sum_elims += (double)G.elims;
        J->sum_maxstack += G.max_stack;
        J->sum_maxhand += G.max_hand_seen;
        J->sum_zero += (double)G.zeros;
        J->sum_seven += (double)G.sevens;
        J->sum_roul += (double)G.roulettes;
        J->sum_dup += (double)G.dup_draw_turns;
        J->endcause[G.endcause]++;
        for (int e = 0; e < 4; e++) J->elim_ctx[e] += G.elim_ctx[e];
        if (G.elims) J->games_with_elim++;
        if (G.endcause == 3) J->capped++;
        if (G.winner >= 0) { J->wins_by_seat[G.winner]++; J->wins_by_policy[G.pol[G.winner]]++; }
    }
    return NULL;
}

static int parse_policy(const char *s) {
    for (int i = 0; i < NPOL; i++) if (!strcmp(s, POL_NAME[i])) return i;
    fprintf(stderr, "unknown policy %s\n", s);
    exit(2);
}

static void usage(void) {
    fprintf(stderr,
            "usage: nomercy [options]\n"
            "  -p N              players (2..6)\n"
            "  -n N              games\n"
            "  -threads N        worker threads (results depend on seed AND thread count)\n"
            "  -seed S           base seed\n"
            "  -policy NAME      random|randomv|greedy|collude|mcwin|shark|grandpa|gremlin|grudge|peace|\n"
            "                    engineer|staller (all seats)\n"
            "  -seatpol a,b,...  per-seat policies (one name per player)\n"
            "  -cap N            turn cap (0 = none, the default)\n"
            "  -debug N          1 = invariant checks every turn, 2 = also print every state\n"
            "rules (defaults = official reading, see RULES.md):\n"
            "  -deck 0|1|2 [0] -hand N [7] -mercy N [25] -mercy_immediate 0|1 [1]\n"
            "  -voluntary_draw 0|1 [0] -after_draw 0|1|2 [0] -stack_rule 0|1|2 [0] -stack_mandatory 0|1 [0]\n"
            "  -roulette_chooser 0|1 [0] -elim_cards 0|1|2 [2] -zero_seven 0|1 [1] -reverse2p_skip 0|1 [1]\n"
            "  -wrd4_victim 0|1 [0] -wrd4_2p_self 0|1 [1]\n"
            "colluder search (policy collude): -depth N [1] -phantom 0|1 [1] -worst 0|1 [0] -riskw X [1e6]\n"
            "  -band lo,hi [4,14] -pw roul,d10,d6,wrd4 [40,25,12,4] -insure X [0]\n"
            "competitive Monte-Carlo player (policy mcwin): -mcwR N [48]\n"
            "stress tests: -adv_nature 1 (adversarial card order), -detect_cycles 1 (prove infinite loops),\n"
            "  -dumpcap 1 (print games that hit -cap)\n");
    exit(2);
}

int main(int argc, char **argv) {
    Rules R;
    rules_default(&R);
    int deck = 0, nseatpol = 0;
    int np = 4, threads = 4, debug = 0;
    long long ngames = 100000, cap = 0;
    uint64_t seed = 12345;
    int pol[MAXP];
    for (int i = 0; i < MAXP; i++) pol[i] = POL_RANDOM;
    for (int i = 1; i < argc; i++) {
        const char *a = argv[i];
        const char *v = i + 1 < argc ? argv[i + 1] : NULL;
#define OPT(name) (!strcmp(a, name) && v && (i++, 1))
        if (OPT("-p")) np = atoi(v);
        else if (OPT("-n")) ngames = atoll(v);
        else if (OPT("-threads")) threads = atoi(v);
        else if (OPT("-seed")) seed = strtoull(v, NULL, 10);
        else if (OPT("-cap")) cap = atoll(v);
        else if (OPT("-debug")) debug = atoi(v);
        else if (OPT("-policy")) { int q = parse_policy(v); for (int k = 0; k < MAXP; k++) pol[k] = q; }
        else if (OPT("-seatpol")) {
            char buf[256]; strncpy(buf, v, 255); buf[255] = 0;
            int k = 0; for (char *tok = strtok(buf, ","); tok && k < MAXP; tok = strtok(NULL, ",")) pol[k++] = parse_policy(tok);
            nseatpol = k;
        }
        else if (OPT("-pw")) sscanf(v, "%lf,%lf,%lf,%lf", &poison_w_roul, &poison_w_d10, &poison_w_d6, &poison_w_wrd4);
        else if (OPT("-depth")) search_depth = atoi(v);
        else if (OPT("-phantom")) phantom_search = atoi(v);
        else if (OPT("-adv_nature")) adv_nature = atoi(v);
        else if (OPT("-worst")) worst_case = atoi(v);
        else if (OPT("-dumpcap")) dump_cap = atoi(v);
        else if (OPT("-detect_cycles")) detect_cycles = atoi(v);
        else if (OPT("-riskw")) risk_w = atof(v);
        else if (OPT("-insure")) insure_w = atof(v);
        else if (OPT("-band")) sscanf(v, "%d,%d", &band_lo, &band_hi);
        else if (OPT("-mcwR")) mcw_R = atoi(v);
        else if (OPT("-deck")) deck = atoi(v);
        else if (OPT("-hand")) R.hand_size = atoi(v);
        else if (OPT("-mercy")) R.mercy = atoi(v);
        else if (OPT("-mercy_immediate")) R.mercy_immediate = atoi(v);
        else if (OPT("-voluntary_draw")) R.voluntary_draw = atoi(v);
        else if (OPT("-after_draw")) R.after_draw = atoi(v);
        else if (OPT("-stack_rule")) R.stack_rule = atoi(v);
        else if (OPT("-roulette_chooser")) R.roulette_chooser = atoi(v);
        else if (OPT("-elim_cards")) R.elim_cards = atoi(v);
        else if (OPT("-zero_seven")) R.zero_seven = atoi(v);
        else if (OPT("-reverse2p_skip")) R.reverse2p_skip = atoi(v);
        else if (OPT("-wrd4_victim")) R.wrd4_victim = atoi(v);
        else if (OPT("-wrd4_2p_self")) R.wrd4_2p_self = atoi(v);
        else if (OPT("-stack_mandatory")) R.stack_mandatory = atoi(v);
        else usage();
#undef OPT
    }
    // the official game is for 2-6 players; the flip for the opening card needs >= 89 undealt cards
    if (np < 2 || np > 6 || deck < 0 || deck > 2 || ngames < 1 || R.hand_size < 1 || DECK - np * R.hand_size < 89 ||
        R.mercy < 2 || R.after_draw < 0 || R.after_draw > 2 || R.stack_rule < 0 || R.stack_rule > 2 ||
        R.elim_cards < 0 || R.elim_cards > 2 || R.roulette_chooser < 0 || R.roulette_chooser > 1)
        usage();
    if (nseatpol && nseatpol != np) { fprintf(stderr, "-seatpol needs exactly one policy per player\n"); exit(2); }
    select_deck(deck);
    if (threads < 1) threads = 1;
    Job *jobs = xcalloc(threads, sizeof(Job));
    pthread_t *th = xcalloc(threads, sizeof(pthread_t));
    for (int k = 0; k < threads; k++) {
        Job *J = &jobs[k];
        J->R = &R;
        J->np = np;
        memcpy(J->pol, pol, sizeof pol);
        J->ngames = ngames / threads + (k < ngames % threads ? 1 : 0);
        J->seed = seed * 1000003ULL + (uint64_t)k * 7919ULL + 17;
        J->turn_cap = cap;
        J->debug = debug;
        pthread_create(&th[k], NULL, run_job, J);
    }
    Job T;
    memset(&T, 0, sizeof T);
    T.hist = xcalloc(HMAX, sizeof(long long));
    T.overflow_vals = xcalloc((size_t)threads << 16, sizeof(long long));
    for (int k = 0; k < threads; k++) {
        pthread_join(th[k], NULL);
        Job *J = &jobs[k];
        for (long long i = 0; i < HMAX; i++) T.hist[i] += J->hist[i];
        T.overflow += J->overflow;
        for (long long i = 0; i < J->noverflow_vals; i++) T.overflow_vals[T.noverflow_vals++] = J->overflow_vals[i];
        T.sum_t += J->sum_t; T.sum_t2 += J->sum_t2;
        T.sum_plays += J->sum_plays; T.sum_draws += J->sum_draws; T.sum_resh += J->sum_resh; T.sum_elims += J->sum_elims;
        T.sum_maxstack += J->sum_maxstack; T.sum_maxhand += J->sum_maxhand;
        T.sum_zero += J->sum_zero; T.sum_seven += J->sum_seven; T.sum_roul += J->sum_roul; T.sum_dup += J->sum_dup;
        if (J->max_t > T.max_t) T.max_t = J->max_t;
        for (int e = 0; e < 6; e++) T.endcause[e] += J->endcause[e];
        for (int p = 0; p < MAXP; p++) T.wins_by_seat[p] += J->wins_by_seat[p];
        for (int p = 0; p < NPOL; p++) T.wins_by_policy[p] += J->wins_by_policy[p];
        T.games_with_elim += J->games_with_elim;
        for (int e = 0; e < 4; e++) T.elim_ctx[e] += J->elim_ctx[e];
        T.capped += J->capped;
    }
    double N = (double)ngames;
    double mean = T.sum_t / N;
    double var = T.sum_t2 / N - mean * mean;
    // quantiles
    long long qs_idx[7];
    double qs[7] = {0.5, 0.9, 0.99, 0.999, 0.9999, 0.99999, 0.999999};
    for (int j = 0; j < 7; j++) {
        long long target = (long long)ceil(qs[j] * N), acc = 0, i;
        for (i = 0; i < HMAX; i++) { acc += T.hist[i]; if (acc >= target) break; }
        qs_idx[j] = i < HMAX ? i : -1;
    }
    printf("{\n");
    printf("  \"players\": %d, \"games\": %lld, \"seed\": %llu, \"deck\": %d,\n", np, ngames, (unsigned long long)seed, deck);
    printf("  \"policies\": [");
    for (int p = 0; p < np; p++) printf("%s\"%s\"", p ? "," : "", POL_NAME[pol[p]]);
    printf("],\n");
    printf("  \"rules\": {\"hand\":%d,\"mercy\":%d,\"mercy_immediate\":%d,\"voluntary_draw\":%d,\"after_draw\":%d,"
           "\"stack_rule\":%d,\"roulette_chooser\":%d,\"elim_cards\":%d,\"zero_seven\":%d,"
           "\"reverse2p_skip\":%d,\"wrd4_victim\":%d,\"wrd4_2p_self\":%d,\"stack_mandatory\":%d},\n",
           R.hand_size, R.mercy, R.mercy_immediate, R.voluntary_draw, R.after_draw, R.stack_rule, R.roulette_chooser,
           R.elim_cards, R.zero_seven, R.reverse2p_skip, R.wrd4_victim, R.wrd4_2p_self,
           R.stack_mandatory);
    printf("  \"mean_turns\": %.6f, \"sd_turns\": %.6f, \"sem_turns\": %.6f, \"max_turns\": %lld,\n", mean, sqrt(var),
           sqrt(var / N), T.max_t);
    printf("  \"quantiles\": {\"p50\":%lld,\"p90\":%lld,\"p99\":%lld,\"p999\":%lld,\"p9999\":%lld,\"p99999\":%lld,\"p999999\":%lld},\n",
           qs_idx[0], qs_idx[1], qs_idx[2], qs_idx[3], qs_idx[4], qs_idx[5], qs_idx[6]);
    printf("  \"mean_plays\": %.4f, \"mean_draws\": %.4f, \"mean_reshuffles\": %.4f, \"mean_eliminations\": %.4f,\n",
           T.sum_plays / N, T.sum_draws / N, T.sum_resh / N, T.sum_elims / N);
    printf("  \"mean_max_stack\": %.4f, \"mean_max_hand\": %.4f, \"mean_zeros\": %.4f, \"mean_sevens\": %.4f, \"mean_roulettes\": %.4f, \"mean_dup_turns\": %.4f,\n",
           T.sum_maxstack / N, T.sum_maxhand / N, T.sum_zero / N, T.sum_seven / N, T.sum_roul / N, T.sum_dup / N);
    printf("  \"end_emptied_hand\": %lld, \"end_last_standing\": %lld, \"end_capped\": %lld, \"end_stuck_forever\": %lld, \"end_proven_cycle\": %lld, \"games_with_elimination\": %lld,\n",
           T.endcause[1], T.endcause[2], T.endcause[3], T.endcause[4], T.endcause[5], T.games_with_elim);
    printf("  \"elims_by_cause\": {\"draw_until_playable\":%lld,\"penalty\":%lld,\"roulette\":%lld,\"other\":%lld},\n",
           T.elim_ctx[1], T.elim_ctx[2], T.elim_ctx[3], T.elim_ctx[0]);
    printf("  \"wins_by_seat\": [");
    for (int p = 0; p < np; p++) printf("%s%lld", p ? "," : "", T.wins_by_seat[p]);
    printf("],\n  \"wins_by_policy\": {");
    for (int p = 0; p < NPOL; p++) printf("%s\"%s\":%lld", p ? "," : "", POL_NAME[p], T.wins_by_policy[p]);
    printf("},\n");
    printf("  \"overflow\": %lld, \"overflow_values\": [", T.overflow);
    for (long long i = 0; i < T.noverflow_vals && i < 10000; i++) printf("%s%lld", i ? "," : "", T.overflow_vals[i]);
    printf("],\n");
    // sparse histogram
    printf("  \"hist\": {");
    int first = 1;
    for (long long i = 0; i < HMAX; i++)
        if (T.hist[i]) { printf("%s\"%lld\":%lld", first ? "" : ",", i, T.hist[i]); first = 0; }
    printf("}\n}\n");
    fflush(stdout);
    for (int k = 0; k < threads; k++) { free(jobs[k].hist); free(jobs[k].overflow_vals); }
    free(T.hist); free(T.overflow_vals); free(jobs); free(th);
    return 0;
}
