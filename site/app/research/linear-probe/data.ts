// Numbers from the study's published files under public/research/linear-probe (test_metrics_with_intervals.csv and
// paired_probe_minus_tuned_native.json, one set per model). Counts are rates times 256 block rows or 284 allow rows.
// data.test.ts checks every value against those files.
export type Arm = "fixed" | "tuned" | "massMean" | "probe" | "text" | "shuffled";
export type ModelKey = "strands" | "kev";
type ArmResult = { ba: number; low: number; high: number; missed: number; falseBlocks: number };
type Gain = { diff: number; low: number; high: number };
export const STUDY: Record<ModelKey, { name: string; arms: Record<Arm, ArmResult>; gain: Record<"probe" | "massMean", Gain> }> = {
  "strands": {
    "name": "Strands Decider 2B",
    "arms": {
      "fixed": {
        "ba": 0.8533,
        "low": 0.8248,
        "high": 0.879,
        "missed": 12,
        "falseBlocks": 70
      },
      "tuned": {
        "ba": 0.8828,
        "low": 0.8548,
        "high": 0.9079,
        "missed": 42,
        "falseBlocks": 20
      },
      "massMean": {
        "ba": 0.8923,
        "low": 0.867,
        "high": 0.9159,
        "missed": 20,
        "falseBlocks": 39
      },
      "probe": {
        "ba": 0.9693,
        "low": 0.9536,
        "high": 0.9845,
        "missed": 13,
        "falseBlocks": 3
      },
      "text": {
        "ba": 0.7558,
        "low": 0.7193,
        "high": 0.7919,
        "missed": 107,
        "falseBlocks": 20
      },
      "shuffled": {
        "ba": 0.423,
        "low": 0.3882,
        "high": 0.4617,
        "missed": 153,
        "falseBlocks": 158
      }
    },
    "gain": {
      "probe": {
        "diff": 0.0866,
        "low": 0.0625,
        "high": 0.1148
      },
      "massMean": {
        "diff": 0.0095,
        "low": -0.017,
        "high": 0.0342
      }
    }
  },
  "kev": {
    "name": "Kev 4B",
    "arms": {
      "fixed": {
        "ba": 0.9384,
        "low": 0.919,
        "high": 0.956,
        "missed": 0,
        "falseBlocks": 35
      },
      "tuned": {
        "ba": 0.9646,
        "low": 0.9503,
        "high": 0.9789,
        "missed": 1,
        "falseBlocks": 19
      },
      "massMean": {
        "ba": 0.951,
        "low": 0.9325,
        "high": 0.9674,
        "missed": 17,
        "falseBlocks": 9
      },
      "probe": {
        "ba": 0.9836,
        "low": 0.9711,
        "high": 0.9927,
        "missed": 3,
        "falseBlocks": 6
      },
      "text": {
        "ba": 0.7558,
        "low": 0.7193,
        "high": 0.7919,
        "missed": 107,
        "falseBlocks": 20
      },
      "shuffled": {
        "ba": 0.372,
        "low": 0.3356,
        "high": 0.4084,
        "missed": 162,
        "falseBlocks": 177
      }
    },
    "gain": {
      "probe": {
        "diff": 0.019,
        "low": -0.0004,
        "high": 0.0369
      },
      "massMean": {
        "diff": -0.0136,
        "low": -0.0373,
        "high": 0.0086
      }
    }
  }
};

/** Validation AUROC by sampled layer, best C per layer for the linear probes (validation_search.csv, as in the PR's
 * validation-layer-sweep.png). Keys: probe kind (LR = linear, MM = mass-mean) and the feature it reads. */
export type SweepKey = "LR:answer_mean" | "LR:option_delta" | "MM:answer_mean" | "MM:option_delta";
export type SweepRow = { layer: number } & Record<SweepKey, number>;
export const LAYER_SWEEP: Record<ModelKey, { selected: number; rows: SweepRow[] }> = {
  strands: {
    selected: 11,
    rows: [
      { layer: 0, "LR:answer_mean": 0.8462, "LR:option_delta": 0.8365, "MM:answer_mean": 0.7452, "MM:option_delta": 0.7885 },
      { layer: 3, "LR:answer_mean": 0.9904, "LR:option_delta": 0.976, "MM:answer_mean": 0.9423, "MM:option_delta": 0.9471 },
      { layer: 7, "LR:answer_mean": 0.9856, "LR:option_delta": 0.9856, "MM:answer_mean": 0.976, "MM:option_delta": 0.9279 },
      { layer: 11, "LR:answer_mean": 1, "LR:option_delta": 0.9904, "MM:answer_mean": 0.9663, "MM:option_delta": 0.9038 },
      { layer: 15, "LR:answer_mean": 1, "LR:option_delta": 1, "MM:answer_mean": 0.9808, "MM:option_delta": 0.9904 },
      { layer: 19, "LR:answer_mean": 1, "LR:option_delta": 1, "MM:answer_mean": 0.9904, "MM:option_delta": 0.9904 },
      { layer: 23, "LR:answer_mean": 0.9952, "LR:option_delta": 1, "MM:answer_mean": 0.976, "MM:option_delta": 0.9952 },
    ],
  },
  kev: {
    selected: 15,
    rows: [
      { layer: 0, "LR:answer_mean": 0.7356, "LR:option_delta": 0.8462, "MM:answer_mean": 0.7067, "MM:option_delta": 0.8221 },
      { layer: 5, "LR:answer_mean": 0.9567, "LR:option_delta": 0.9615, "MM:answer_mean": 0.9183, "MM:option_delta": 0.9038 },
      { layer: 10, "LR:answer_mean": 0.9952, "LR:option_delta": 0.9904, "MM:answer_mean": 0.9423, "MM:option_delta": 0.9663 },
      { layer: 15, "LR:answer_mean": 1, "LR:option_delta": 1, "MM:answer_mean": 1, "MM:option_delta": 1 },
      { layer: 20, "LR:answer_mean": 1, "LR:option_delta": 1, "MM:answer_mean": 0.9952, "MM:option_delta": 1 },
      { layer: 25, "LR:answer_mean": 1, "LR:option_delta": 1, "MM:answer_mean": 0.9952, "MM:option_delta": 0.9904 },
      { layer: 31, "LR:answer_mean": 1, "LR:option_delta": 1, "MM:answer_mean": 0.8798, "MM:option_delta": 0.75 },
    ],
  },
};
