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
       K_WRD4 = 16, K_WD6 = 17, K_WD10 = 18, K_ROUL = 19 };
#define NT 68
#define WILD 4
#define MAXP 10
#define DECK 168

static const int COLORED_COUNT[16] = {2, 2, 2, 2, 2, 2, 2, 2, 2, 2, /* 0-9 */
                                      3, /* Draw 2 */ 2, /* Draw 4 */ 3, /* Skip */
                                      2, /* Skip Everyone */ 3, /* Reverse */ 3 /* Discard All */};
static const int WILD_COUNT[4] = {8, /* Wild Reverse Draw 4 */ 4, /* Wild Draw 6 */
                                  4, /* Wild Draw 10 */ 8 /* Wild Color Roulette */};

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

static const char *KIND_NAME[20] = {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "D2", "D4", "Skip",
                                    "SkipAll", "Rev", "DiscardAll", "WRD4", "WD6", "WD10", "Roulette"};
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
    int last_card_wins;   // 1: emptying your hand wins immediately (0/7/draw effects not applied)
    int start_rule;       // 0: flip until a number card for the start card; 1: flip once, apply as if played by dealer
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
    R->last_card_wins = 1;
    R->start_rule = 0;
    R->reverse2p_skip = 1;
    R->wrd4_victim = 0;
    R->wrd4_2p_self = 1;
    R->stack_mandatory = 0;
}

// ----------------------------------------------------------------------------
// Policies
// ----------------------------------------------------------------------------
enum { POL_RANDOM = 0, POL_RANDOMV = 1, POL_GREEDY = 2, POL_PROLONG = 3, POL_MIXED = 4 };
static const char *POL_NAME[] = {"random", "randomv", "greedy", "prolong", "mixed"};

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
    int endcause; // 1 = emptied hand, 2 = last player standing, 3 = turn cap, 4 = stuck
    // counters
    long long turns, plays, draws, reshuffles, elims, zeros, sevens, roulettes, stacks_accepted;
    long long dup_draw_turns;
    int max_stack;
    int max_hand_seen;
    int elim_turn[MAXP];
    long long turn_cap;
    int debug;
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
}

static void eliminate(Game *G, int p) {
    G->alive[p] = 0;
    G->nalive--;
    G->elims++;
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
static int draw_one(Game *G, int p) {
    if (G->pn == 0) reshuffle(G);
    if (G->pn == 0) return -1;
    int t = G->pile[--G->pn];
    G->hand[p][t]++;
    G->hsize[p]++;
    G->draws++;
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
    int tot[4] = {36, 36, 36, 36};
    for (int t = 0; t < 64; t++) tot[t >> 4] -= G->hand[p][t] + G->disc[t];
    if (G->top < 64) tot[G->top >> 4]--;
    for (int i = 0; i < 4; i++) cc[i] = tot[i];
}

// ---- color choice after playing a wild --------------------------------------
static int choose_color(Game *G, int p) {
    int pol = G->pol[p];
    if (pol == POL_RANDOM || pol == POL_RANDOMV) return (int)rng_below(G->rng, 4);
    int cc[4];
    color_counts(G, p, cc);
    if (pol == POL_PROLONG) {
        // colluders: pick a color the next player can follow (keeps everyone "in" the game)
        int q = next_alive(G, p, G->dir);
        int nc[4];
        color_counts(G, q, nc);
        for (int i = 0; i < 4; i++) nc[i] = nc[i] * 4 + cc[i];
        return argmax4_rand(G->rng, nc);
    }
    return argmax4_rand(G->rng, cc);
}

// ---- 7: swap target ---------------------------------------------------------
static int choose_swap(Game *G, int p) {
    int opts[MAXP], n = 0;
    for (int q = 0; q < G->np; q++) if (q != p && G->alive[q]) opts[n++] = q;
    int pol = G->pol[p];
    if (pol == POL_RANDOM || pol == POL_RANDOMV) return opts[rng_below(G->rng, n)];
    if (pol == POL_PROLONG) {
        // swap toward "balanced" hands: pick the target whose size is closest to our own
        int best = opts[0], bd = 1 << 30;
        for (int i = 0; i < n; i++) {
            int d = abs(G->hsize[opts[i]] - G->hsize[p]);
            if (d < bd) { bd = d; best = opts[i]; }
        }
        return best;
    }
    // greedy: take the smallest hand
    int best = opts[0];
    for (int i = 1; i < n; i++)
        if (G->hsize[opts[i]] < G->hsize[best] || (G->hsize[opts[i]] == G->hsize[best] && rng_below(G->rng, 2)))
            best = opts[i];
    return best;
}

// ---- Color Roulette color -----------------------------------------------------
static int choose_roulette_color(Game *G, int chooser, int victim) {
    int pol = G->pol[chooser];
    if (pol == POL_RANDOM || pol == POL_RANDOMV) return (int)rng_below(G->rng, 4);
    int uc[4];
    unseen_color_counts(G, chooser, uc);
    if (chooser == victim || pol == POL_PROLONG) return argmax4_rand(G->rng, uc); // fewest flips
    return argmin4_rand(G->rng, uc);                                               // most flips
}

// ---- facing a stack: returns card type to stack, or -1 to accept -------------
static int choose_stack(Game *G, int p, const int *opts, int n) {
    int pol = G->pol[p];
    if (n == 0) return -1;
    if (pol == POL_RANDOM || pol == POL_RANDOMV) {
        int k = (int)rng_below(G->rng, (uint32_t)(n + 1));
        return k == n ? -1 : opts[k];
    }
    if (pol == POL_PROLONG) {
        // colluders: pass the stack on only if the next victim can absorb it better
        int total = G->stack;
        if (G->hsize[p] + total < G->R->mercy - 1 && G->hsize[p] + total <= 14) return -1;
        // otherwise pass the smallest card
        int best = opts[0];
        for (int i = 1; i < n; i++) if (drawval(opts[i]) < drawval(best)) best = opts[i];
        return best;
    }
    // greedy: always stack, using the smallest sufficient draw card (prefer colored over wild)
    int best = opts[0];
    for (int i = 1; i < n; i++) {
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
    if (v) s += 10 * v + (nh <= 3 ? 60 : 0);
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

static int prolong_score(Game *G, int p, int t);

static int choose_play(Game *G, int p, const int *opts, int n, int allow_draw) {
    int pol = G->pol[p];
    if (pol == POL_RANDOM) return opts[rng_below(G->rng, n)];
    if (pol == POL_RANDOMV) {
        if (allow_draw) {
            int k = (int)rng_below(G->rng, (uint32_t)(n + 1));
            return k == n ? -1 : opts[k];
        }
        return opts[rng_below(G->rng, n)];
    }
    if (pol == POL_PROLONG) {
        int best = -1, bs = -(1 << 30);
        for (int i = 0; i < n; i++) {
            int s = prolong_score(G, p, opts[i]) * 8 + (int)rng_below(G->rng, 8);
            if (s > bs) { bs = s; best = opts[i]; }
        }
        if (allow_draw && bs < -100000 * 8) return -1;
        return best;
    }
    int best = -1, bs = -(1 << 30);
    for (int i = 0; i < n; i++) {
        int s = greedy_score(G, p, opts[i]) * 8 + (int)rng_below(G->rng, 8);
        if (s > bs) { bs = s; best = opts[i]; }
    }
    return best;
}

// Prolonger (all players collude to keep the game going).
static int prolong_score(Game *G, int p, int t) {
    int k = ckind(t), c = ccolor(t);
    int h = G->hsize[p];
    if (h == 1) return -200000; // never play last card if avoidable
    if (k == K_DISCALL) {
        int cnt = 0;
        for (int kk = 0; kk < 16; kk++) cnt += G->hand[p][c * 16 + kk];
        if (cnt == h) return -200000;
        return -50 * cnt;
    }
    int s = 0;
    int v = drawval_kind(k);
    if (v) s -= 30 * v;
    if (k == K_ROUL) s -= 500;
    if (c == WILD) s -= 20;
    // prefer plays that the next player can follow
    int nxt = next_alive(G, p, G->dir);
    if (c != WILD) {
        int follow = 0;
        for (int tt = 0; tt < NT; tt++) {
            if (!G->hand[nxt][tt]) continue;
            int tc = ccolor(tt);
            if (tc == WILD || tc == c || (ckind(tt) < 16 && ckind(tt) == k)) follow += G->hand[nxt][tt];
        }
        s += follow ? 10 + follow : -60;
    }
    s += 2 * h; // prefer playing from big hands... (only the current player's)
    return s;
}

static int choose_after_draw(Game *G, int p, int t) {
    int pol = G->pol[p];
    if (G->R->after_draw == 0) return 1;
    if (G->R->after_draw == 2) return 0;
    if (pol == POL_RANDOM || pol == POL_RANDOMV) return (int)rng_below(G->rng, 2);
    if (pol == POL_PROLONG) return G->hsize[p] > 1 ? 1 : 0;
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
    G->hand[p][t]--;
    G->hsize[p]--;
    G->disc[G->top]++;
    G->dn++;
    G->top = t;
    G->plays++;
    int k = ckind(t), c = ccolor(t);
    if (c == WILD) {
        if (k == K_ROUL && G->R->roulette_chooser == 0) {
            // the roulette victim names the color (see below); active color set then
            G->color = (int)rng_below(G->rng, 4); // provisional, overwritten below
        } else {
            G->color = choose_color(G, p);
        }
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
    if (G->hsize[p] == 0 && G->R->last_card_wins) {
        end_game(G, p, 1);
        return;
    }
    int v = drawval_kind(k);
    switch (k) {
    case K_D2: case K_D4: case K_WD6: case K_WD10:
        G->stack += v;
        G->stackv = v;
        if (G->stack > G->max_stack) G->max_stack = G->stack;
        G->cur = next_alive(G, p, G->dir);
        break;
    case K_WRD4:
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
        int chooser = G->R->roulette_chooser == 0 ? victim : p;
        int col = choose_roulette_color(G, chooser, victim);
        G->color = col;
        G->roulettes++;
        int elim = 0;
        for (;;) {
            int d = draw_one(G, victim);
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
    // with last_card_wins == 0 a player can be at 0 cards after 0/7 effects; they win at turn end
    if (!G->R->last_card_wins) {
        for (int q = 0; q < G->np; q++)
            if (G->alive[q] && G->hsize[q] == 0) { end_game(G, q, 1); return; }
    }
}

// ----------------------------------------------------------------------------
// One turn
// ----------------------------------------------------------------------------
static void take_turn(Game *G) {
    int p = G->cur;
    int opts[NT];
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
        draw_n(G, p, total);
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
        d = draw_one(G, p);
        if (d == -2) { // eliminated
            if (!G->over) G->cur = next_alive(G, p, G->dir);
            return;
        }
        if (d == -1) { // nothing to draw at all (can only happen in degenerate rule variants)
            if (end_of_action_mercy(G, p)) { if (!G->over) G->cur = next_alive(G, p, G->dir); return; }
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
    int n = 0;
    for (int c = 0; c < 4; c++)
        for (int k = 0; k < 16; k++)
            for (int i = 0; i < COLORED_COUNT[k]; i++) G->pile[n++] = (uint8_t)(c * 16 + k);
    for (int w = 0; w < 4; w++)
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
    // starting card
    if (R->start_rule == 0) {
        for (;;) {
            int t = G->pile[--G->pn];
            if (ckind(t) <= 9) { G->top = t; G->color = ccolor(t); break; }
            // official: "If this card is an Action Card, ignore it and flip over the next card."
            // (the ignored card stays in the discard pile, under the new top card)
            G->disc[t]++;
            G->dn++;
        }
        G->cur = next_alive(G, dealer, 1);
    } else {
        // flip once and apply it as if the dealer had played it (without removing from a hand)
        int t = G->pile[--G->pn];
        G->hand[dealer][t]++;
        G->hsize[dealer]++;
        G->top = 64 + 0; // dummy; play_card pushes it to discard -- avoid by setting top to t itself
        G->color = 0;
        // simple approach: treat as dealer's play
        G->top = t; // will be pushed to discard; remove that push afterwards
        play_card(G, dealer, t);
        G->disc[t]--; // undo the push of the dummy top (same type)
        G->dn--;
        G->plays--;
    }
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

static void play_game(Game *G) {
    if (G->debug) check_invariants(G, "init");
    while (!G->over) {
        if (G->debug >= 2) print_state(G, stderr);
        take_turn(G);
        if (G->debug) check_invariants(G, "turn");
        if (G->turn_cap && G->turns >= G->turn_cap && !G->over) { G->over = 1; G->endcause = 3; G->winner = -1; }
    }
}

// ----------------------------------------------------------------------------
// Batch driver
// ----------------------------------------------------------------------------
#define HMAX (1 << 20)
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
    long long endcause[5];
    long long wins_by_seat[MAXP];
    long long wins_by_policy[5];
    long long games_with_elim;
    long long capped;
    double sum_zero, sum_seven, sum_roul, sum_dup;
    long long *overflow_vals;
    long long noverflow_vals;
} Job;

static void *run_job(void *arg) {
    Job *J = (Job *)arg;
    Rng rng;
    rng_seed(&rng, J->seed);
    J->hist = calloc(HMAX, sizeof(long long));
    J->overflow_vals = calloc(1 << 16, sizeof(long long));
    Game G;
    for (long long g = 0; g < J->ngames; g++) {
        // rotate seats so seat effects average out when policies are mixed
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
        if (G.elims) J->games_with_elim++;
        if (G.endcause == 3) J->capped++;
        if (G.winner >= 0) { J->wins_by_seat[G.winner]++; J->wins_by_policy[G.pol[G.winner]]++; }
    }
    return NULL;
}

static int parse_policy(const char *s) {
    for (int i = 0; i < 5; i++) if (!strcmp(s, POL_NAME[i])) return i;
    fprintf(stderr, "unknown policy %s\n", s);
    exit(2);
}

static void usage(void) {
    fprintf(stderr,
            "usage: nomercy [options]\n"
            "  -p N              players (2..%d)\n"
            "  -n N              games\n"
            "  -threads N        worker threads\n"
            "  -seed S           base seed\n"
            "  -policy NAME      random|randomv|greedy|prolong  (all seats)\n"
            "  -seatpol a,b,...  per-seat policies\n"
            "  -cap N            turn cap (0 = none)\n"
            "  -debug N          1 = invariant checks each turn, 2 = also print states\n"
            "rules flags (defaults in brackets):\n"
            "  -hand N [7] -mercy N [25] -mercy_immediate 0|1 [1] -voluntary_draw 0|1 [0]\n"
            "  -after_draw 0|1|2 [0] -stack_rule 0|1|2 [0] -roulette_chooser 0|1 [0]\n"
            "  -elim_cards 0|1|2 [2] -zero_seven 0|1 [1] -last_card_wins 0|1 [1]\n"
            "  -start_rule 0|1 [0] -reverse2p_skip 0|1 [1] -wrd4_victim 0|1 [0]\n"
            "  -wrd4_2p_self 0|1 [1] -stack_mandatory 0|1 [0]\n",
            MAXP);
    exit(2);
}

int main(int argc, char **argv) {
    Rules R;
    rules_default(&R);
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
        }
        else if (OPT("-hand")) R.hand_size = atoi(v);
        else if (OPT("-mercy")) R.mercy = atoi(v);
        else if (OPT("-mercy_immediate")) R.mercy_immediate = atoi(v);
        else if (OPT("-voluntary_draw")) R.voluntary_draw = atoi(v);
        else if (OPT("-after_draw")) R.after_draw = atoi(v);
        else if (OPT("-stack_rule")) R.stack_rule = atoi(v);
        else if (OPT("-roulette_chooser")) R.roulette_chooser = atoi(v);
        else if (OPT("-elim_cards")) R.elim_cards = atoi(v);
        else if (OPT("-zero_seven")) R.zero_seven = atoi(v);
        else if (OPT("-last_card_wins")) R.last_card_wins = atoi(v);
        else if (OPT("-start_rule")) R.start_rule = atoi(v);
        else if (OPT("-reverse2p_skip")) R.reverse2p_skip = atoi(v);
        else if (OPT("-wrd4_victim")) R.wrd4_victim = atoi(v);
        else if (OPT("-wrd4_2p_self")) R.wrd4_2p_self = atoi(v);
        else if (OPT("-stack_mandatory")) R.stack_mandatory = atoi(v);
        else usage();
#undef OPT
    }
    if (np < 2 || np > MAXP || np * R.hand_size >= DECK - 1) usage();
    if (threads < 1) threads = 1;
    Job *jobs = calloc(threads, sizeof(Job));
    pthread_t *th = calloc(threads, sizeof(pthread_t));
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
    T.hist = calloc(HMAX, sizeof(long long));
    T.overflow_vals = calloc((size_t)threads << 16, sizeof(long long));
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
        for (int e = 0; e < 5; e++) T.endcause[e] += J->endcause[e];
        for (int p = 0; p < MAXP; p++) T.wins_by_seat[p] += J->wins_by_seat[p];
        for (int p = 0; p < 5; p++) T.wins_by_policy[p] += J->wins_by_policy[p];
        T.games_with_elim += J->games_with_elim;
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
    printf("  \"players\": %d, \"games\": %lld, \"seed\": %llu,\n", np, ngames, (unsigned long long)seed);
    printf("  \"policies\": [");
    for (int p = 0; p < np; p++) printf("%s\"%s\"", p ? "," : "", POL_NAME[pol[p]]);
    printf("],\n");
    printf("  \"rules\": {\"hand\":%d,\"mercy\":%d,\"mercy_immediate\":%d,\"voluntary_draw\":%d,\"after_draw\":%d,"
           "\"stack_rule\":%d,\"roulette_chooser\":%d,\"elim_cards\":%d,\"zero_seven\":%d,\"last_card_wins\":%d,"
           "\"start_rule\":%d,\"reverse2p_skip\":%d,\"wrd4_victim\":%d,\"wrd4_2p_self\":%d,\"stack_mandatory\":%d},\n",
           R.hand_size, R.mercy, R.mercy_immediate, R.voluntary_draw, R.after_draw, R.stack_rule, R.roulette_chooser,
           R.elim_cards, R.zero_seven, R.last_card_wins, R.start_rule, R.reverse2p_skip, R.wrd4_victim, R.wrd4_2p_self,
           R.stack_mandatory);
    printf("  \"mean_turns\": %.6f, \"sd_turns\": %.6f, \"sem_turns\": %.6f, \"max_turns\": %lld,\n", mean, sqrt(var),
           sqrt(var / N), T.max_t);
    printf("  \"quantiles\": {\"p50\":%lld,\"p90\":%lld,\"p99\":%lld,\"p999\":%lld,\"p9999\":%lld,\"p99999\":%lld,\"p999999\":%lld},\n",
           qs_idx[0], qs_idx[1], qs_idx[2], qs_idx[3], qs_idx[4], qs_idx[5], qs_idx[6]);
    printf("  \"mean_plays\": %.4f, \"mean_draws\": %.4f, \"mean_reshuffles\": %.4f, \"mean_eliminations\": %.4f,\n",
           T.sum_plays / N, T.sum_draws / N, T.sum_resh / N, T.sum_elims / N);
    printf("  \"mean_max_stack\": %.4f, \"mean_max_hand\": %.4f, \"mean_zeros\": %.4f, \"mean_sevens\": %.4f, \"mean_roulettes\": %.4f, \"mean_dup_turns\": %.4f,\n",
           T.sum_maxstack / N, T.sum_maxhand / N, T.sum_zero / N, T.sum_seven / N, T.sum_roul / N, T.sum_dup / N);
    printf("  \"end_emptied_hand\": %lld, \"end_last_standing\": %lld, \"end_capped\": %lld, \"games_with_elimination\": %lld,\n",
           T.endcause[1], T.endcause[2], T.endcause[3], T.games_with_elim);
    printf("  \"wins_by_seat\": [");
    for (int p = 0; p < np; p++) printf("%s%lld", p ? "," : "", T.wins_by_seat[p]);
    printf("],\n  \"wins_by_policy\": {");
    for (int p = 0; p < 5; p++) printf("%s\"%s\":%lld", p ? "," : "", POL_NAME[p], T.wins_by_policy[p]);
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
    return 0;
}
