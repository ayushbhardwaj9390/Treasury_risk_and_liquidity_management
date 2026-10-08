import { plainGuides } from "../lib/pet-guide";

export default function ScreenExplainer({ view }: { view: string }) {
  const guide = plainGuides[view];
  if (!guide) return null;
  return <section className="screen-explainer" aria-label="Plain-language screen explanation"><p className="eyebrow">IN EVERYDAY WORDS</p><h2>{guide.question}</h2><p>{guide.meaning}</p><details key={view}><summary>Show a simple example</summary><p>{guide.example}</p></details></section>;
}
