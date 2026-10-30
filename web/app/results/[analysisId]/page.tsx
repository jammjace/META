import Link from "next/link";
import { AnnotatedImage } from "@/components/annotated-image";
import { getAnalysis } from "@/lib/api";

export default async function ResultsPage({ params }: { params: Promise<{ analysisId: string }> }) {
  const { analysisId } = await params;
  const result = await getAnalysis(analysisId);
  return <main className="shell results-shell">
    <header className="masthead"><Link href="/" className="mark">FORM</Link><span>Saved analysis</span></header>
    <section className="results-head">
      <div><p className="eyebrow">BACK VIEW · BASELINE</p><h1>Visible structure,<br />mapped.</h1></div>
      <p>Select a highlighted region to inspect the saved model observation. Reloading this page does not call the model again.</p>
    </section>
    <AnnotatedImage result={result} />
    <aside className="notice">{result.warnings.map(warning => <p key={warning}>{warning}</p>)}</aside>
    <Link href="/" className="secondary">Analyze another photo</Link>
  </main>;
}

