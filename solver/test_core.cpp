// test_core.cpp - checks the C++ evaluator against hands scored by Python and
// times the feature computation.
//   clang++ -O3 -std=c++17 -o solver/test_core solver/test_core.cpp
//   ./solver/test_core data/eval_both.bin /tmp/hands.txt
#include <chrono>
#include <fstream>
#include <iostream>

#include "core.hpp"

int main(int argc, char** argv) {
    sd::Eval ev(argv[1]);
    std::ifstream in(argv[2]);
    int h[5], b[5]; long long want; int n = 0, bad = 0;
    while (in >> h[0] >> h[1] >> h[2] >> h[3] >> h[4] >> b[0] >> b[1] >> b[2] >> b[3] >> b[4] >> want) {
        ++n;
        if (ev.best(h, b, 5) != want) ++bad;
    }
    std::cout << "checked " << n << " hands, mismatches " << bad << "\n";
    sd::Rng rng(1);
    int hole[5] = {32, 33, 28, 31, 12}, board[5] = {34, 13, 25, 0, 0};
    for (int nb : {0, 3, 4, 5}) {
        auto t = std::chrono::steady_clock::now();
        sd::Features f{};
        for (int r = 0; r < 100; ++r) f = sd::features(ev, hole, board, nb, 1000, rng);
        double ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t).count() / 100;
        std::cout << "board " << nb << ": ehs " << f.ehs << " hs " << f.hs << "  " << ms << " ms per 1000 samples\n";
    }
    return bad != 0;
}
