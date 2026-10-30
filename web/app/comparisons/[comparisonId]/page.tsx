import Link from "next/link";
import { ComparisonView } from "@/components/comparison-view";
import { getComparison } from "@/lib/api";

export default async function ComparisonPage({ params }: { params: Promise<{ comparisonId: string }> }) {
  const { comparisonId } = await params;
  const result = await getComparison(comparisonId);
  return <main className="shell results-shell">
    <header className="masthead"><Link href="/" className="mark">FORM</Link><span>Saved comparison</span></header>
    <section className="comparison-summary"><p className="eyebrow">VISIBLE PROGRESS REPORT</p><h1>Before / Now</h1><p>{result.overall_summary}</p></section>
    <ComparisonView result={result} />
    {result.comparison_warnings.length > 0 && <aside className="notice">{result.comparison_warnings.map(warning => <p key={warning}>{warning}</p>)}</aside>}
    <Link href="/compare" className="secondary">Compare another pair</Link>
  </main>;
}
