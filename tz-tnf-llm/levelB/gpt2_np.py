"""GPT-2 (124M) forward pass in numpy with a pluggable number format on every matmul.

Purpose: check whether a representation-SQNR gap between 16-bit activation formats
survives as a perplexity difference on real text. No training, no GPU.
"""
import json, math, os, struct, sys, functools
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- weights
def load_safetensors(path):
    f = open(path, "rb")
    n = struct.unpack("<Q", f.read(8))[0]
    head = json.loads(f.read(n))
    base = 8 + n
    out = {}
    mm = np.memmap(path, dtype=np.uint8, mode="r")
    for k, v in head.items():
        if k == "__metadata__":
            continue
        assert v["dtype"] == "F32", v["dtype"]
        s, e = v["data_offsets"]
        a = np.frombuffer(mm[base + s: base + e].tobytes(), dtype="<f4")
        out[k] = a.reshape(v["shape"]).astype(np.float32)
    return out

# ---------------------------------------------------------------- BPE tokenizer
def bytes_to_unicode():
    bs = list(range(ord("!"), ord("~") + 1)) + list(range(ord("\xa1"), ord("\xac") + 1)) + \
         list(range(ord("\xae"), ord("\xff") + 1))
    cs = bs[:]
    n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b); cs.append(256 + n); n += 1
    return dict(zip(bs, [chr(c) for c in cs]))

class BPE:
    def __init__(self, vocab_path, merges_path):
        self.encoder = json.load(open(vocab_path))
        merges = [tuple(l.split()) for l in open(merges_path, encoding="utf-8").read().split("\n")[1:] if l]
        self.ranks = {m: i for i, m in enumerate(merges)}
        self.b2u = bytes_to_unicode()
        import re
        self.pat = re.compile(r"'s|'t|'re|'ve|'m|'ll|'d| ?[A-Za-z]+| ?\d+| ?[^\sA-Za-z\d]+|\s+(?!\S)|\s+")
        self.cache = {}

    def bpe(self, token):
        if token in self.cache:
            return self.cache[token]
        word = list(token)
        while len(word) > 1:
            pairs = [(self.ranks.get((word[i], word[i+1]), 1 << 30), i) for i in range(len(word) - 1)]
            rank, i = min(pairs)
            if rank == 1 << 30:
                break
            word = word[:i] + [word[i] + word[i+1]] + word[i+2:]
        self.cache[token] = word
        return word

    def encode(self, text):
        ids = []
        for tok in self.pat.findall(text):
            t = "".join(self.b2u[b] for b in tok.encode("utf-8"))
            for piece in self.bpe(t):
                ids.append(self.encoder[piece])
        return ids

# ---------------------------------------------------------------- formats
def _fmt_float(x, e, m, ecodes=None, block=0):
    """Round to a (1,e,m) float. ecodes limits the reachable exponent codes
    (3**t for a ternary-coded exponent field). block>0 = per-block scale."""
    ecodes = ecodes or (1 << e)
    bias = ecodes // 2 - 1
    emin, emax = 1 - bias, ecodes - 1 - bias
    vmax = (2 - 2.0 ** -m) * 2.0 ** min(emax, 1000)
    x = np.asarray(x, dtype=np.float32)
    shape = x.shape
    if block:
        flat = x.reshape(-1)
        n = (flat.size // block) * block
        head = flat[:n].reshape(-1, block).astype(np.float64)
        s = np.max(np.abs(head), axis=1, keepdims=True) / vmax
        s[s == 0] = 1.0
        y = head / s
    else:
        s = float(np.max(np.abs(x))) / vmax or 1.0
        y = x.astype(np.float64).reshape(1, -1) / s
    ay = np.abs(y)
    with np.errstate(divide="ignore"):
        ex = np.floor(np.log2(np.where(ay > 0, ay, 1.0)))
    ex = np.clip(ex, emin, emax)
    step = 2.0 ** (ex - m)
    q = np.minimum(np.rint(ay / step) * step, vmax)
    out = np.sign(y) * q * s
    if block:
        flat2 = x.reshape(-1).copy()
        flat2[:out.size] = out.reshape(-1).astype(np.float32)
        return flat2.reshape(shape)
    return out.reshape(shape).astype(np.float32)

def _fmt_fixed(x, bits, block=0):
    hi = 2 ** (bits - 1) - 1
    x = np.asarray(x, dtype=np.float32); shape = x.shape
    if block:
        flat = x.reshape(-1); n = (flat.size // block) * block
        head = flat[:n].reshape(-1, block).astype(np.float64)
        s = np.max(np.abs(head), axis=1, keepdims=True) / hi
        s[s == 0] = 1.0
        v = (np.clip(np.rint(head / s), -hi, hi) * s).astype(np.float32)
        out = flat.copy(); out[:n] = v.reshape(-1)
        return out.reshape(shape)
    s = float(np.max(np.abs(x))) / hi or 1.0
    return (np.clip(np.rint(x / s), -hi, hi) * s).astype(np.float32)

FORMATS = {
    "fp32":            lambda x: x,
    "e2m13_b32":       lambda x: _fmt_float(x, 2, 13, block=32),
    "e3m12_b32":       lambda x: _fmt_float(x, 3, 12, block=32),
    "e5m10":           lambda x: _fmt_float(x, 5, 10),
    "e6m9_b32_PHI":    lambda x: _fmt_float(x, 6, 9, block=32),
    "e6m9_PHI":        lambda x: _fmt_float(x, 6, 9),
    "fixed16_b32":     lambda x: _fmt_fixed(x, 16, block=32),
    "tnf16_t4m8_b32":  lambda x: _fmt_float(x, 7, 8, ecodes=81, block=32),
    # 8-bit budget, where the representation gap is larger
    "e2m5_b32":        lambda x: _fmt_float(x, 2, 5, block=32),
    "e4m3":            lambda x: _fmt_float(x, 4, 3),
    "int8_b32":        lambda x: _fmt_fixed(x, 8, block=32),
    "e3m4_b32_PHI8":   lambda x: _fmt_float(x, 3, 4, block=32),
}

def ternary_weights(w):
    """Round-to-nearest ternary with a per-output-column scale (BitNet-style absmean)."""
    a = np.abs(w).mean(axis=0, keepdims=True)
    a = np.where(a == 0, 1.0, a)
    return (np.clip(np.rint(w / a), -1, 1) * a).astype(np.float32)

# ---------------------------------------------------------------- model
class GPT2:
    def __init__(self, w, qact=None, qw=None):
        self.w = w
        self.qact = qact or (lambda x: x)
        self.qw = qw
        self._wcache = {}

    def W(self, k):
        if self.qw is None:
            return self.w[k]
        if k not in self._wcache:
            self._wcache[k] = self.qw(self.w[k])
        return self._wcache[k]

    def lin(self, x, wk, bk):
        return self.qact(x) @ self.W(wk) + self.w[bk]

    @staticmethod
    def ln(x, g, b, eps=1e-5):
        mu = x.mean(-1, keepdims=True)
        v = x.var(-1, keepdims=True)
        return ((x - mu) / np.sqrt(v + eps)) * g + b

    def forward(self, ids):
        w = self.w
        T = len(ids)
        x = w["wte.weight"][ids] + w["wpe.weight"][:T]
        nh, hd = 12, 64
        for l in range(12):
            p = f"h.{l}."
            h = self.ln(x, w[p + "ln_1.weight"], w[p + "ln_1.bias"])
            qkv = self.lin(h, p + "attn.c_attn.weight", p + "attn.c_attn.bias")
            q, k, v = np.split(qkv, 3, axis=-1)
            q = q.reshape(T, nh, hd).transpose(1, 0, 2)
            k = k.reshape(T, nh, hd).transpose(1, 0, 2)
            v = v.reshape(T, nh, hd).transpose(1, 0, 2)
            att = (self.qact(q) @ self.qact(k).transpose(0, 2, 1)) / math.sqrt(hd)
            mask = np.triu(np.full((T, T), -1e10, dtype=np.float32), 1)
            att = att + mask
            att = att - att.max(-1, keepdims=True)
            np.exp(att, out=att)
            att /= att.sum(-1, keepdims=True)
            o = (self.qact(att) @ self.qact(v)).transpose(1, 0, 2).reshape(T, nh * hd)
            x = x + self.lin(o, p + "attn.c_proj.weight", p + "attn.c_proj.bias")
            h = self.ln(x, w[p + "ln_2.weight"], w[p + "ln_2.bias"])
            f = self.lin(h, p + "mlp.c_fc.weight", p + "mlp.c_fc.bias")
            f = 0.5 * f * (1.0 + np.tanh(0.7978845608 * (f + 0.044715 * f ** 3)))
            x = x + self.lin(f, p + "mlp.c_proj.weight", p + "mlp.c_proj.bias")
        x = self.ln(x, w["ln_f.weight"], w["ln_f.bias"])
        return self.qact(x) @ w["wte.weight"].T

def nll(logits, targets):
    z = logits - logits.max(-1, keepdims=True)
    lse = np.log(np.exp(z).sum(-1))
    return float(np.sum(lse - z[np.arange(len(targets)), targets]))
