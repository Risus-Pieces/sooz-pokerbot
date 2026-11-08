// pool.cpp - generate a pool of random deals with per-player, per-street hand
// features for card abstraction and solver training.
//
//   clang++ -O3 -march=native -std=c++17 -pthread -o solver/pool solver/pool.cpp
//   ./solver/pool data/eval_both.bin OUT.bin N_DEALS SAMPLES THREADS SEED
//
// Record layout (64 bytes, little-endian):
//   uint8  cards[15]   hole[0] (button) 5, hole[1] (big blind) 5, board 5
//   int8   showdown    +1 button wins at showdown, -1 big blind wins, 0 split
//   float  feat[2][6]  per player: pre_ehs, flop_ehs, flop_hs, turn_ehs, turn_hs, river_hs
//   uint8  pad[...]    to 64 bytes
#include <atomic>
#include <cstring>
#include <iostream>
#include <thread>

#include "core.hpp"

#pragma pack(push, 1)
struct Rec {
    uint8_t cards[15];
    int8_t showdown;
    float feat[2][6];
};
#pragma pack(pop)
static_assert(sizeof(Rec) == 64, "record must be 64 bytes");

int main(int argc, char** argv) {
    if (argc < 7) { std::cerr << "usage: pool EVAL OUT N SAMPLES THREADS SEED\n"; return 2; }
    sd::Eval ev(argv[1]);
    std::string out = argv[2];
    long long n = std::atoll(argv[3]);
    int samples = std::atoi(argv[4]);
    int threads = std::atoi(argv[5]);
    unsigned long long seed = std::strtoull(argv[6], nullptr, 10);
    std::vector<Rec> recs(n);
    std::atomic<long long> next{0};
    auto work = [&](int tid) {
        sd::Rng rng(seed * 1000003ULL + tid);
        while (true) {
            long long i = next.fetch_add(1);
            if (i >= n) break;
            int cards[36];
            for (int c = 0; c < 36; ++c) cards[c] = c;
            for (int k = 0; k < 15; ++k) {
                std::uniform_int_distribution<int> U(k, 35);
                int j = U(rng); std::swap(cards[k], cards[j]);
            }
            Rec& r = recs[i];
            for (int k = 0; k < 15; ++k) r.cards[k] = (uint8_t)cards[k];
            const int* board = cards + 10;
            for (int p = 0; p < 2; ++p) {
                const int* hole = cards + 5 * p;
                sd::Features f0 = sd::features(ev, hole, board, 0, samples, rng);
                sd::Features f3 = sd::features(ev, hole, board, 3, samples, rng);
                sd::Features f4 = sd::features(ev, hole, board, 4, samples, rng);
                sd::Features f5 = sd::features(ev, hole, board, 5, samples, rng);
                float v[6] = {f0.ehs, f3.ehs, f3.hs, f4.ehs, f4.hs, f5.hs};
                std::memcpy(r.feat[p], v, sizeof v);
            }
            int32_t a = ev.best(cards, board, 5), b = ev.best(cards + 5, board, 5);
            r.showdown = a > b ? 1 : (a < b ? -1 : 0);
            if (tid == 0 && i % 20000 == 0) std::cerr << "\r" << i << "/" << n << std::flush;
        }
    };
    std::vector<std::thread> ts;
    for (int t = 0; t < threads; ++t) ts.emplace_back(work, t);
    for (auto& t : ts) t.join();
    FILE* f = std::fopen(out.c_str(), "wb");
    std::fwrite(recs.data(), sizeof(Rec), recs.size(), f);
    std::fclose(f);
    std::cerr << "\nwrote " << n << " deals to " << out << "\n";
    return 0;
}
