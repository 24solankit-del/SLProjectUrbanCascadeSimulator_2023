/* =============================================================
   URBAN CASCADE SIMULATOR — PRNG ENGINE
   Deterministic Pseudo-Random Number Generator (Seeded)
   Guarantees exact bit-level reproduction of cascade propagation
   ============================================================= */

/**
 * xmur3 hash function — converts a string seed into a 32-bit integer
 * Used as the initial state for mulberry32 PRNG
 */
function xmur3(str) {
    let h = 1779033703 ^ str.length;
    for (let i = 0; i < str.length; i++) {
        h = Math.imul(h ^ str.charCodeAt(i), 3432918353);
        h = (h << 13) | (h >>> 19);
    }
    return function () {
        h = Math.imul(h ^ (h >>> 16), 2246822507);
        h = Math.imul(h ^ (h >>> 13), 3266489909);
        return (h ^= h >>> 16) >>> 0;
    };
}

/**
 * mulberry32 PRNG — fast, simple, deterministic 32-bit PRNG
 * Returns a function that produces uniform random floats in [0, 1)
 */
function mulberry32(a) {
    return function () {
        let t = (a += 0x6d2b79f5);
        t = Math.imul(t ^ (t >>> 15), t | 1);
        t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
}

/**
 * SeedEngine — manages the deterministic PRNG lifecycle
 */
class SeedEngine {
    constructor(seedStr) {
        this.seedStr = seedStr || 'NAGPUR-SMART-2026';
        this.rng = this._createRng(this.seedStr);
    }

    _createRng(str) {
        return mulberry32(xmur3(str)());
    }

    /** Set a new seed and reset the PRNG state */
    setSeed(seedStr) {
        this.seedStr = seedStr;
        this.rng = this._createRng(seedStr);
    }

    /** Get the next random float in [0, 1) — deterministic */
    next() {
        return this.rng();
    }

    /** Get the current seed string (for display / export) */
    getSeed() {
        return this.seedStr;
    }
}
