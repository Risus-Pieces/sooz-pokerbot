// mccfr.cpp - external-sampling Monte Carlo CFR on the EXACT betting tree with
// per-street card buckets (imperfect-recall card abstraction).
//
// Build: clang++ -O3 -march=native -std=c++17 -pthread -o solver/mccfr solver/mccfr.cpp
// Run:   ./solver/mccfr TREE.bin BUCKETS.bin SHOWDOWN.bin OUTDIR B0 B1 B2 B3 THREADS MINUTES [RESUME_DIR]
//
// Inputs
//   TREE.bin      data/tree.bin from lab/export_tree.py (node rows, see that file)
//   BUCKETS.bin   uint16[n_deals][2][4]: bucket of (button, big blind) on (pre, flop, turn, river)
//   SHOWDOWN.bin  int8[n_deals]: +1 button wins at showdown, -1 big blind wins, 0 split
// Output (every checkpoint, in OUTDIR/ckpt_<k>/ and OUTDIR/latest/):
//   strat_s.bin   uint8[dnodes_s][B_s][4] average-strategy probabilities (x255, rows sum ~255)
//   regret_s.bin, ssum_s.bin  float32 state for resuming
//   meta.txt      iterations, minutes, bucket counts
//
// Algorithm: external sampling (traverser explores all its actions, opponent
// and chance sampled), regret matching, linear-CFR-style discounting during the
// first DISCOUNT_MINUTES (both regrets and strategy sums scaled by t/(t+1) per
// epoch, as in Pluribus), negative-regret pruning after PRUNE_MINUTES (skip
// actions with regret < PRUNE_THRESHOLD 95% of the time, except on river/terminal
// children). Threads update shared tables without locks (Hogwild).
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <iostream>
#include <random>
#include <string>
#include <thread>
#include <vector>

namespace fs = std::filesystem;

struct Node { int street, actor, term, fold_winner, cb, co, child[4]; };

static std::vector<Node> T;
static std::vector<int> DIDX;           // decision index within its street
static int NDEC[4] = {0, 0, 0, 0};
static int NB[4];
static std::vector<float> R[4], S[4];   // [dnode][bucket][4]
static std::vector<uint16_t> BK;        // [deal][2][4]
static std::vector<int8_t> SD;          // [deal]
static long long NDEALS = 0;

static double DISCOUNT_MINUTES = 60, PRUNE_MINUTES = 30;
static const float PRUNE_THRESHOLD = -2.0e5f, REGRET_FLOOR = -3.0e5f;
static std::atomic<bool> g_prune{false};

template <class V> static void read_file(const std::string& p, V& v) {
    FILE* f = std::fopen(p.c_str(), "rb");
    if (!f) { std::cerr << "cannot open " << p << "\n"; std::exit(1); }
    std::fseek(f, 0, SEEK_END); long sz = std::ftell(f); std::fseek(f, 0, SEEK_SET);
    v.resize(sz / sizeof(typename V::value_type));
    if (std::fread(v.data(), 1, sz, f) != (size_t)sz) { std::cerr << "short read " << p << "\n"; std::exit(1); }
    std::fclose(f);
}

static void load_tree(const std::string& p) {
    std::vector<int32_t> raw; read_file(p, raw);
    int n = raw[0];
    T.resize(n); DIDX.assign(n, -1);
    for (int i = 0; i < n; ++i) {
        const int32_t* r = &raw[1 + 10 * i];
        Node& x = T[i];
        x.street = r[0]; x.actor = r[1]; x.term = r[2]; x.fold_winner = r[3]; x.cb = r[4]; x.co = r[5];
        for (int a = 0; a < 4; ++a) x.child[a] = r[6 + a];
        if (x.actor >= 0) DIDX[i] = NDEC[x.street]++;
    }
}

static inline size_t idx(int street, int d, int b) { return ((size_t)d * NB[street] + b) * 4; }

// utility to the button (player 0), in chips
static inline float utility(const Node& x, long long deal) {
    if (x.term == 1) return x.fold_winner == 0 ? (float)x.co : -(float)x.cb;
    return (float)SD[deal] * (float)x.cb;   // contributions are equal at showdown
}

struct Ctx { std::mt19937_64 rng; std::uniform_real_distribution<float> U{0.f, 1.f}; };

static inline void regret_match(const float* r, const int* child, float* sigma) {
    float pos = 0;
    for (int a = 0; a < 4; ++a) { sigma[a] = (child[a] >= 0 && r[a] > 0) ? r[a] : 0.f; pos += sigma[a]; }
    if (pos > 0) { for (int a = 0; a < 4; ++a) sigma[a] /= pos; return; }
    int n = 0; for (int a = 0; a < 4; ++a) n += child[a] >= 0;
    for (int a = 0; a < 4; ++a) sigma[a] = child[a] >= 0 ? 1.f / n : 0.f;
}

static float traverse(int node, int p, long long deal, Ctx& c) {
    const Node& x = T[node];
    if (x.term) { float u = utility(x, deal); return p == 0 ? u : -u; }
    int s = x.street, b = BK[deal * 8 + x.actor * 4 + s];
    size_t k = idx(s, DIDX[node], b);
    float* r = &R[s][k];
    float sigma[4]; regret_match(r, x.child, sigma);
    if (x.actor == p) {
        float v[4] = {0, 0, 0, 0}, ev = 0; bool explored[4] = {false, false, false, false};
        bool prune = g_prune.load(std::memory_order_relaxed) && s < 3 && c.U(c.rng) < 0.95f;
        for (int a = 0; a < 4; ++a) {
            if (x.child[a] < 0) continue;
            if (prune && r[a] < PRUNE_THRESHOLD && !T[x.child[a]].term) continue;
            v[a] = traverse(x.child[a], p, deal, c); explored[a] = true;
            ev += sigma[a] * v[a];
        }
        for (int a = 0; a < 4; ++a) {
            if (!explored[a]) continue;
            float nr = r[a] + (v[a] - ev);
            r[a] = nr < REGRET_FLOOR ? REGRET_FLOOR : nr;
        }
        return ev;
    }
    // opponent: accumulate average strategy, sample one action
    float* sm = &S[s][k];
    for (int a = 0; a < 4; ++a) sm[a] += sigma[a];
    float u = c.U(c.rng), acc = 0; int pick = -1;
    for (int a = 0; a < 4; ++a) { if (x.child[a] < 0) continue; acc += sigma[a]; pick = a; if (u < acc) break; }
    return traverse(x.child[pick], p, deal, c);
}

static void write_bin(const fs::path& p, const void* data, size_t bytes) {
    FILE* f = std::fopen(p.string().c_str(), "wb"); std::fwrite(data, 1, bytes, f); std::fclose(f);
}

static void checkpoint(const fs::path& dir, long long iters, double minutes) {
    fs::create_directories(dir);
    for (int s = 0; s < 4; ++s) {
        size_t n = (size_t)NDEC[s] * NB[s];
        std::vector<uint8_t> out(n * 4, 0);
        // decision node of each (s, d) to know legal actions
        static std::vector<std::vector<int>> nodes_of(4);
        if (nodes_of[s].empty()) { nodes_of[s].resize(NDEC[s]); for (size_t i = 0; i < T.size(); ++i) if (T[i].actor >= 0 && T[i].street == s) nodes_of[s][DIDX[i]] = (int)i; }
        for (int d = 0; d < NDEC[s]; ++d) {
            const Node& x = T[nodes_of[s][d]];
            for (int b = 0; b < NB[s]; ++b) {
                size_t k = idx(s, d, b);
                float tot = 0; int legal = 0;
                for (int a = 0; a < 4; ++a) if (x.child[a] >= 0) { tot += S[s][k + a] > 0 ? S[s][k + a] : 0; ++legal; }
                for (int a = 0; a < 4; ++a) {
                    if (x.child[a] < 0) continue;
                    float pr = tot > 0 ? std::max(0.f, S[s][k + a]) / tot : 1.f / legal;
                    out[k + a] = (uint8_t)std::lround(pr * 255.f);
                }
            }
        }
        write_bin(dir / ("strat_" + std::to_string(s) + ".bin"), out.data(), out.size());
        write_bin(dir / ("regret_" + std::to_string(s) + ".bin"), R[s].data(), R[s].size() * 4);
        write_bin(dir / ("ssum_" + std::to_string(s) + ".bin"), S[s].data(), S[s].size() * 4);
    }
    FILE* f = std::fopen((dir / "meta.txt").string().c_str(), "w");
    std::fprintf(f, "iterations %lld\nminutes %.2f\nbuckets %d %d %d %d\ndecision_nodes %d %d %d %d\n",
                 iters, minutes, NB[0], NB[1], NB[2], NB[3], NDEC[0], NDEC[1], NDEC[2], NDEC[3]);
    std::fclose(f);
}

int main(int argc, char** argv) {
    if (argc < 12) { std::cerr << "usage: mccfr TREE BUCKETS SHOWDOWN OUTDIR B0 B1 B2 B3 THREADS MINUTES CKPT_MIN [RESUME_DIR]\n"; return 2; }
    load_tree(argv[1]);
    read_file(argv[2], BK); read_file(argv[3], SD);
    NDEALS = (long long)SD.size();
    if ((long long)BK.size() != NDEALS * 8) { std::cerr << "bucket/showdown size mismatch\n"; return 1; }
    fs::path out = argv[4];
    for (int s = 0; s < 4; ++s) NB[s] = std::atoi(argv[5 + s]);
    int threads = std::atoi(argv[9]);
    double minutes = std::atof(argv[10]), ckpt_min = std::atof(argv[11]);
    if (const char* e = std::getenv("DISCOUNT_MINUTES")) DISCOUNT_MINUTES = std::atof(e);
    if (const char* e = std::getenv("PRUNE_MINUTES")) PRUNE_MINUTES = std::atof(e);
    for (int s = 0; s < 4; ++s) { R[s].assign((size_t)NDEC[s] * NB[s] * 4, 0.f); S[s].assign((size_t)NDEC[s] * NB[s] * 4, 0.f); }
    if (argc > 12) {
        fs::path rd = argv[12];
        for (int s = 0; s < 4; ++s) { read_file((rd / ("regret_" + std::to_string(s) + ".bin")).string(), R[s]); read_file((rd / ("ssum_" + std::to_string(s) + ".bin")).string(), S[s]); }
        std::cerr << "resumed from " << rd << "\n";
    }
    for (int b = 0; b < (int)BK.size(); ++b) {}
    std::cerr << "deals " << NDEALS << " decision nodes " << NDEC[0] << "/" << NDEC[1] << "/" << NDEC[2] << "/" << NDEC[3]
              << " buckets " << NB[0] << "/" << NB[1] << "/" << NB[2] << "/" << NB[3] << "\n";

    std::atomic<long long> iters{0};
    std::atomic<bool> stop{false};
    auto t0 = std::chrono::steady_clock::now();
    auto elapsed_min = [&] { return std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count() / 60.0; };
    std::vector<std::thread> ts;
    for (int t = 0; t < threads; ++t) ts.emplace_back([&, t] {
        Ctx c; c.rng.seed(0x50057ULL * (t + 1) + 12345);
        std::uniform_int_distribution<long long> D(0, NDEALS - 1);
        while (!stop.load(std::memory_order_relaxed)) {
            for (int k = 0; k < 256; ++k) {
                long long deal = D(c.rng);
                long long it = iters.fetch_add(1, std::memory_order_relaxed);
                traverse(0, (int)(it & 1), deal, c);
            }
        }
    });
    double next_ckpt = ckpt_min, next_disc = 1.0;
    int ck = 0;
    while (true) {
        std::this_thread::sleep_for(std::chrono::seconds(5));
        double m = elapsed_min();
        if (m >= PRUNE_MINUTES) g_prune = true;
        if (m < DISCOUNT_MINUTES && m >= next_disc) {     // linear-CFR discount once per minute
            double tk = next_disc; float d = (float)(tk / (tk + 1.0));
            for (int s = 0; s < 4; ++s) { for (auto& v : R[s]) v *= d; for (auto& v : S[s]) v *= d; }
            next_disc += 1.0;
        }
        if (m >= next_ckpt || m >= minutes) {
            long long n = iters.load();
            fs::path dir = out / ("ckpt_" + std::to_string(++ck));
            checkpoint(dir, n, m);
            fs::remove_all(out / "latest"); fs::copy(dir, out / "latest", fs::copy_options::recursive);
            std::cerr << "checkpoint " << ck << " at " << m << " min, " << n << " iterations ("
                      << (long long)(n / (m * 60.0)) << " it/s)\n";
            next_ckpt += ckpt_min;
        }
        if (m >= minutes) { stop = true; break; }
    }
    for (auto& t : ts) t.join();
    return 0;
}
