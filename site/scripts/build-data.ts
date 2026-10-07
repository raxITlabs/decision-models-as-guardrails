// Generate site/data/ from the benchmark results (release day), or say why it cannot.
//
//   pnpm data                      # reads ../ (the benchmark repository root)
//   pnpm data -- --repo <path>     # another checkout
//   pnpm data:fixture              # rebuild fixtures/data/ from the synthetic fixtures/source/
//
// site/data/ is git-ignored: scores are held until release day. When the inputs are missing this exits 0 and the
// site builds from fixtures/data/ instead.
import path from "node:path";
import { generate, hasRealInputs, writeGenerated } from "./generate";

const SITE = path.resolve(__dirname, "..");
const args = process.argv.slice(2);
const fixture = args.includes("--fixture");
const repoArg = args.indexOf("--repo");
const repo = fixture
  ? path.join(SITE, "fixtures", "source")
  : path.resolve(repoArg >= 0 ? args[repoArg + 1] : path.join(SITE, ".."));
const out = fixture ? path.join(SITE, "fixtures", "data") : path.join(SITE, "data");

if (!hasRealInputs(repo)) {
  console.log(`[data] no benchmark results under ${repo}; the site will build from fixtures/data/ (synthetic).`);
  process.exit(0);
}
const g = generate(repo, fixture ? "fixture" : "real");
writeGenerated(g, out);
console.log(
  `[data] wrote ${path.relative(SITE, out)}/ from ${fixture ? "the synthetic fixture" : repo}: ` +
    `${g.board.systems.length} systems, ${g.summary.rows} public rows (${g.summary.withText} with text, ` +
    `${g.summary.withheld} withheld), ${g.summary.droppedPrivate} unpublished rows left out.`,
);
