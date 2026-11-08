// core.hpp - Short Deck PLO5 hand evaluation and Monte Carlo hand features.
//
// Scores are identical to evaluator.omaha_score: the score table is the one
// fasteval.py builds (data/eval_both.bin, index = 2 * sum(5^rank) + is_flush),
// so C++ and Python can never disagree about who wins.
#pragma once

#include <array>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>

namespace sd {

static const int64_t POW5[9] = {1, 5, 25, 125, 625, 3125, 15625, 78125, 390625};
static const int PAIRS[10][2] = {{0,1},{0,2},{0,3},{0,4},{1,2},{1,3},{1,4},{2,3},{2,4},{3,4}};
static const int TRIP5[10][3] = {{0,1,2},{0,1,3},{0,1,4},{0,2,3},{0,2,4},{0,3,4},{1,2,3},{1,2,4},{1,3,4},{2,3,4}};
static const int TRIP4[4][3] = {{0,1,2},{0,1,3},{0,2,3},{1,2,3}};

struct Eval {
    std::vector<int32_t> both;

    explicit Eval(const std::string& path) {
        FILE* f = std::fopen(path.c_str(), "rb");
        if (!f) throw std::runtime_error("cannot open " + path);
        both.resize(3906250);
        size_t n = std::fread(both.data(), 4, both.size(), f);
        std::fclose(f);
        if (n != both.size()) throw std::runtime_error("short read " + path);
    }

    // Best exactly-2-hole + exactly-3-board score; board has nb in {3,4,5} cards.
    inline int32_t best(const int* hole, const int* board, int nb) const {
        int64_t hk[10]; int hs[10];
        for (int i = 0; i < 10; ++i) {
            int a = hole[PAIRS[i][0]], b = hole[PAIRS[i][1]];
            hk[i] = POW5[a >> 2] + POW5[b >> 2];
            hs[i] = ((a & 3) == (b & 3)) ? (a & 3) : -1;
        }
        int32_t bestv = 0;
        int nt = nb == 5 ? 10 : (nb == 4 ? 4 : 1);
        for (int j = 0; j < nt; ++j) {
            int c, d, e;
            if (nb == 5) { c = board[TRIP5[j][0]]; d = board[TRIP5[j][1]]; e = board[TRIP5[j][2]]; }
            else if (nb == 4) { c = board[TRIP4[j][0]]; d = board[TRIP4[j][1]]; e = board[TRIP4[j][2]]; }
            else { c = board[0]; d = board[1]; e = board[2]; }
            int64_t bk = POW5[c >> 2] + POW5[d >> 2] + POW5[e >> 2];
            int bs = ((c & 3) == (d & 3) && (d & 3) == (e & 3)) ? (c & 3) : -2;
            for (int i = 0; i < 10; ++i) {
                int32_t s = both[2 * (hk[i] + bk) + (hs[i] == bs ? 1 : 0)];
                if (s > bestv) bestv = s;
            }
        }
        return bestv;
    }
};

using Rng = std::mt19937_64;

// Monte Carlo features of `hole` on a partial board of nb cards (0, 3, 4 or 5):
//   ehs = win chance vs a uniformly random opponent hand, board run out to the river
//   hs  = share of random opponent hands our CURRENT made hand beats (nb >= 3), else ehs
// Cards in `dead` (e.g. nothing, or our known opponent hole for evaluation) are excluded.
struct Features { float ehs; float hs; };

inline Features features(const Eval& ev, const int* hole, const int* board, int nb, int n, Rng& rng) {
    bool used[36] = {false};
    for (int i = 0; i < 5; ++i) used[hole[i]] = true;
    for (int i = 0; i < nb; ++i) used[board[i]] = true;
    int rem[36], m = 0;
    for (int c = 0; c < 36; ++c) if (!used[c]) rem[m++] = c;
    int full[5], opp[5];
    for (int i = 0; i < nb; ++i) full[i] = board[i];
    int need = 5 - nb;
    double win = 0, now = 0;
    int32_t mine_now = nb >= 3 ? ev.best(hole, board, nb) : 0;
    for (int it = 0; it < n; ++it) {
        for (int i = 0; i < 5 + need; ++i) {
            std::uniform_int_distribution<int> U(i, m - 1);
            int j = U(rng); int t = rem[i]; rem[i] = rem[j]; rem[j] = t;
        }
        for (int i = 0; i < 5; ++i) opp[i] = rem[i];
        for (int i = 0; i < need; ++i) full[nb + i] = rem[5 + i];
        int32_t a = ev.best(hole, full, 5), b = ev.best(opp, full, 5);
        win += a > b ? 1.0 : (a == b ? 0.5 : 0.0);
        if (nb >= 3 && nb < 5) {
            int32_t o = ev.best(opp, board, nb);
            now += mine_now > o ? 1.0 : (mine_now == o ? 0.5 : 0.0);
        }
    }
    Features f;
    f.ehs = (float)(win / n);
    f.hs = (nb >= 3 && nb < 5) ? (float)(now / n) : f.ehs;
    return f;
}

}  // namespace sd
