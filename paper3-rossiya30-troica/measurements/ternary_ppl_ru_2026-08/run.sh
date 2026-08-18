#!/bin/bash
# Exact perplexity protocol. Runtime: fork PrismML-Eng/llama.cpp commit 9ca265a, cmake Release, GGML_NATIVE=ON.
# Models: /tmp/bonsai17.gguf  (Ternary-Bonsai-1.7B-Q2_0, sha256 d97d94eb5645...)
#         /tmp/qwen17q8.gguf  (Qwen3-1.7B-Q8_0,          sha256 061b54daade0...)
# Sequential, never in parallel: the host has 2 cores and concurrent runs would corrupt the timing.
set -e
CHUNKS=${CHUNKS:-40}
CORPUS=${CORPUS:-/tmp/eval_ru_v2.txt}
cd /tmp/lcpp/build/bin
export LD_LIBRARY_PATH=/tmp/lcpp/build/bin
for m in bonsai17 qwen17q8; do
  ./llama-perplexity -m /tmp/$m.gguf -f "$CORPUS" -c 512 --chunks "$CHUNKS" -t 2 --seed 42 \
      2>&1 | tee "/tmp/ppl_$(basename $CORPUS .txt)_$m.log"
done
