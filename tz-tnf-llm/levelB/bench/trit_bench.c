/* Fair single-platform comparison of ternary-weight unpacking layouts.
 *
 * Layouts under test (all store values in {-1,0,+1}):
 *   TQ2   : 2 bits per trit, 4 trits per byte   (2.000 bits/trit)
 *   TQ1   : 5 trits per byte, base-3 packing    (1.600 bits/trit), div/mod decode
 *   TQ1L  : same container, 256x5 lookup table  (1.600 bits/trit)
 *   TQ1_41: 41 trits per 65 bits, base-3 in a 64-bit word (1.5854 bits/trit)
 *   INT8  : one byte per trit, no decode        (8.000 bits/trit) -- upper bound
 *
 * Two workloads:
 *   unpack : decode into an int8 buffer
 *   dot    : decode and accumulate w[i]*x[i] with int8 activations (no int8 buffer)
 *
 * One machine, one compiler, one optimisation level for every variant.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>

static double now(void) {
  struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t);
  return t.tv_sec + 1e-9 * t.tv_nsec;
}

static int8_t *trits;          /* reference trits in {-1,0,1} */
static int8_t *acts;
static uint8_t *tq2, *tq1;
static uint64_t *tq1_41;
static int8_t *out;
static int8_t lut5[256][5];

static void build(size_t n) {
  size_t i;
  trits = aligned_alloc(64, n);
  acts  = aligned_alloc(64, n);
  out   = aligned_alloc(64, n + 64);
  srand(20260819);
  for (i = 0; i < n; i++) { trits[i] = (int8_t)((rand() % 3) - 1); acts[i] = (int8_t)((rand() % 255) - 127); }
  /* TQ2: 4 trits/byte, 2 bits each, value+1 in {0,1,2} */
  tq2 = aligned_alloc(64, n / 4 + 64);
  for (i = 0; i < n; i += 4) {
    uint8_t b = 0; for (int k = 0; k < 4; k++) b |= (uint8_t)((trits[i + k] + 1) & 3) << (2 * k);
    tq2[i / 4] = b;
  }
  /* TQ1: 5 trits/byte, base 3 */
  tq1 = aligned_alloc(64, n / 5 + 64);
  for (i = 0; i + 5 <= n; i += 5) {
    unsigned v = 0, p = 1;
    for (int k = 0; k < 5; k++) { v += (unsigned)(trits[i + k] + 1) * p; p *= 3; }
    tq1[i / 5] = (uint8_t)v;
  }
  /* TQ1_41: 41 trits per 64-bit word (3^41 < 2^65 ... use 40 to stay inside 64 bits) */
  tq1_41 = aligned_alloc(64, (n / 40 + 8) * 8);
  for (i = 0; i + 40 <= n; i += 40) {
    uint64_t v = 0, p = 1;
    for (int k = 0; k < 40; k++) { v += (uint64_t)(trits[i + k] + 1) * p; p *= 3ull; }
    tq1_41[i / 40] = v;
  }
  for (int b = 0; b < 256; b++) { int v = b; for (int k = 0; k < 5; k++) { lut5[b][k] = (int8_t)(v % 3 - 1); v /= 3; } }
}

static void unpack_tq2(size_t n) {
  for (size_t i = 0; i < n / 4; i++) {
    uint8_t b = tq2[i];
    out[4*i+0] = (int8_t)((b      & 3) - 1);
    out[4*i+1] = (int8_t)((b >> 2 & 3) - 1);
    out[4*i+2] = (int8_t)((b >> 4 & 3) - 1);
    out[4*i+3] = (int8_t)((b >> 6 & 3) - 1);
  }
}
static void unpack_tq1_div(size_t n) {
  for (size_t i = 0; i < n / 5; i++) {
    unsigned v = tq1[i];
    for (int k = 0; k < 5; k++) { out[5*i+k] = (int8_t)(v % 3 - 1); v /= 3; }
  }
}
static void unpack_tq1_lut(size_t n) {
  for (size_t i = 0; i < n / 5; i++) memcpy(out + 5*i, lut5[tq1[i]], 5);
}
static void unpack_tq1_41(size_t n) {
  for (size_t i = 0; i < n / 40; i++) {
    uint64_t v = tq1_41[i];
    for (int k = 0; k < 40; k++) { out[40*i+k] = (int8_t)(v % 3 - 1); v /= 3; }
  }
}
static void unpack_int8(size_t n) { memcpy(out, trits, n); }

static long dot_tq2(size_t n) {
  long acc = 0;
  for (size_t i = 0; i < n / 4; i++) {
    uint8_t b = tq2[i]; const int8_t *x = acts + 4*i;
    acc += (long)((b & 3) - 1) * x[0] + (long)((b >> 2 & 3) - 1) * x[1]
         + (long)((b >> 4 & 3) - 1) * x[2] + (long)((b >> 6 & 3) - 1) * x[3];
  }
  return acc;
}
static long dot_tq1_lut(size_t n) {
  long acc = 0;
  for (size_t i = 0; i < n / 5; i++) {
    const int8_t *w = lut5[tq1[i]]; const int8_t *x = acts + 5*i;
    for (int k = 0; k < 5; k++) acc += (long)w[k] * x[k];
  }
  return acc;
}
static long dot_tq1_div(size_t n) {
  long acc = 0;
  for (size_t i = 0; i < n / 5; i++) {
    unsigned v = tq1[i]; const int8_t *x = acts + 5*i;
    for (int k = 0; k < 5; k++) { acc += (long)((int)(v % 3) - 1) * x[k]; v /= 3; }
  }
  return acc;
}
static long dot_int8(size_t n) {
  long acc = 0;
  for (size_t i = 0; i < n; i++) acc += (long)trits[i] * acts[i];
  return acc;
}

static long ref_dot(size_t n) { long a = 0; for (size_t i = 0; i < n; i++) a += (long)trits[i]*acts[i]; return a; }

int main(int argc, char **argv) {
  size_t n = (argc > 1) ? (size_t)atol(argv[1]) : (1u << 24);
  int reps  = (argc > 2) ? atoi(argv[2]) : 7;
  n = n / 40 * 40;                     /* divisible by 4, 5 and 40 */
  build(n);
  long r = ref_dot(n);
  printf("{\"n_trits\": %zu, \"reps\": %d, \"results\": [\n", n, reps);
  struct { const char *name; double bits; int is_dot; } cfg[] = {
    {"unpack_int8", 8.0, 0}, {"unpack_tq2", 2.0, 0}, {"unpack_tq1_div", 1.6, 0},
    {"unpack_tq1_lut", 1.6, 0}, {"unpack_tq1_41w", 1.6, 0},
    {"dot_int8", 8.0, 1}, {"dot_tq2", 2.0, 1}, {"dot_tq1_lut", 1.6, 1}, {"dot_tq1_div", 1.6, 1},
  };
  for (unsigned c = 0; c < sizeof(cfg)/sizeof(cfg[0]); c++) {
    double best = 1e30, tot = 0; long chk = 0; int ok = 1;
    for (int it = 0; it < reps; it++) {
      double t0 = now();
      if (!cfg[c].is_dot) {
        memset(out, 0, n);
        if (!strcmp(cfg[c].name, "unpack_int8")) unpack_int8(n);
        else if (!strcmp(cfg[c].name, "unpack_tq2")) unpack_tq2(n);
        else if (!strcmp(cfg[c].name, "unpack_tq1_div")) unpack_tq1_div(n);
        else if (!strcmp(cfg[c].name, "unpack_tq1_lut")) unpack_tq1_lut(n);
        else unpack_tq1_41(n);
      } else {
        if (!strcmp(cfg[c].name, "dot_int8")) chk = dot_int8(n);
        else if (!strcmp(cfg[c].name, "dot_tq2")) chk = dot_tq2(n);
        else if (!strcmp(cfg[c].name, "dot_tq1_lut")) chk = dot_tq1_lut(n);
        else chk = dot_tq1_div(n);
      }
      double dt = now() - t0;
      if (dt < best) best = dt;
      tot += dt;
    }
    if (!cfg[c].is_dot) { if (memcmp(out, trits, n)) ok = 0; }
    else if (chk != r) ok = 0;
    printf("  {\"kernel\": \"%s\", \"bits_per_trit\": %.4f, \"best_ns_per_trit\": %.4f, "
           "\"mean_ns_per_trit\": %.4f, \"correct\": %s}%s\n",
           cfg[c].name, cfg[c].bits, best*1e9/n, (tot/reps)*1e9/n, ok?"true":"false",
           (c+1==sizeof(cfg)/sizeof(cfg[0]))?"":",");
  }
  printf("]}\n");
  return 0;
}
