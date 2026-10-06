"use client";
import { useEffect, useRef, useState } from "react";
import { answerHelp, guides, tour } from "../lib/pet-guide";

function Mint() {
  return <svg className="mint-pet" viewBox="0 0 100 100" aria-hidden="true"><ellipse cx="50" cy="91" rx="30" ry="5" fill="#102e3820"/><path className="mint-tail" d="M70 66 Q100 40 93 72 Q85 88 66 82" fill="#55bda9" stroke="#16584f" strokeWidth="3"/><path d="M24 36 L20 8 L41 23 M59 23 L80 8 L76 36" fill="#66cbb6" stroke="#16584f" strokeWidth="3"/><path d="M27 27 L25 17 L34 24 M66 24 L75 17 L73 27" fill="#ffcfab"/><rect x="28" y="58" width="44" height="30" rx="16" fill="#55bda9" stroke="#16584f" strokeWidth="3"/><rect x="18" y="23" width="64" height="45" rx="22" fill="#93dfc8" stroke="#16584f" strokeWidth="3"/><ellipse cx="50" cy="50" rx="24" ry="15" fill="#e9fff3"/><g className="mint-eyes" fill="#163f42"><ellipse cx="37" cy="44" rx="4" ry="6"/><ellipse cx="63" cy="44" rx="4" ry="6"/></g><path d="M46 51 Q50 56 54 51 M50 56 Q43 62 39 57 M50 56 Q57 62 61 57" fill="none" stroke="#16584f" strokeWidth="2.5" strokeLinecap="round"/><circle cx="28" cy="53" r="4" fill="#ffcfab"/><circle cx="72" cy="53" r="4" fill="#ffcfab"/><path d="M40 73 H60 M43 78 H57" stroke="#e9fff3" strokeWidth="3" strokeLinecap="round"/><ellipse cx="34" cy="88" rx="10" ry="5" fill="#16584f"/><ellipse cx="66" cy="88" rx="10" ry="5"/></svg>;
}
export default function TreasuryPet({ view, navigate }: { view: string; navigate: (view: string) => void }) {
  const [open, setOpen] = useState(false), [step, setStep] = useState<number | null>(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<ReturnType<typeof answerHelp> | null>(null);
  const launcher = useRef<HTMLButtonElement>(null), closeButton = useRef<HTMLButtonElement>(null);
  useEffect(() => { if (open) closeButton.current?.focus(); }, [open]);
  useEffect(() => { setAnswer(null); setQuestion(""); if (step !== null && tour[step].view !== view) setStep(null); }, [view]);
  const guide = guides[view] ?? guides.overview;
  function close() { setOpen(false); launcher.current?.focus(); }
  function move(index: number) { setStep(index); setAnswer(null); navigate(tour[index].view); }
  return <div className="treasury-pet">
    {open && <aside id="mint-guide" className="pet-panel" aria-label="Mint treasury usage guide" onKeyDown={e => { if (e.key === "Escape") { e.stopPropagation(); close(); } }}>
      <header className="pet-header"><Mint/><div><strong>Hi, I’m Mint!</strong><span>Your treasury guide</span></div><button ref={closeButton} className="pet-close" aria-label="Close Mint guide" onClick={close}>×</button></header>
      <div className="pet-content"><p className="pet-mode">Built-in help · no live AI connection</p>
        <div className="pet-actions"><button onClick={() => { setStep(null); setAnswer(null); }}>Explain this screen</button><button onClick={() => move(0)}>Start tour</button></div>
        {step === null ? <><h2>{guide.title}</h2><ol>{guide.steps.map(s => <li key={s}>{s}</li>)}</ol></> : <div className="pet-tour"><p className="eyebrow">Step {step + 1} of {tour.length}</p><h2>{tour[step].title}</h2><p>{tour[step].text}</p><div className="pet-actions"><button disabled={step === 0} onClick={() => move(step - 1)}>Back</button>{step < tour.length - 1 ? <button onClick={() => move(step + 1)}>Next step →</button> : <button onClick={() => { setStep(null); setAnswer(null); }}>Finish tour</button>}</div><button className="text-button" onClick={() => setStep(null)}>Exit tour</button></div>}
        <form className="pet-question" onSubmit={e => { e.preventDefault(); if (question.trim()) { setStep(null); setAnswer(answerHelp(question)); } }}><label htmlFor="mint-question">Ask how to use the app</label><div><input id="mint-question" value={question} maxLength={300} onChange={e => setQuestion(e.target.value)} placeholder="How do I upload a file?"/><button type="submit" disabled={!question.trim()}>Ask</button></div></form>
        {answer && <div className="pet-answer" role="status"><p>{answer.text}</p>{answer.view && <button className="text-button" onClick={() => { if (answer.view) navigate(answer.view); }}>Open the workspace →</button>}</div>}
        <p className="pet-footnote">I explain the app. Treasury calculations and human approvals stay in their existing workflows.</p>
      </div>
    </aside>}
    <button ref={launcher} className="pet-launcher" aria-label={open ? "Hide Mint treasury guide" : "Meet Mint: help using this app"} aria-expanded={open} aria-controls="mint-guide" onClick={() => open ? close() : setOpen(true)}><Mint/><span><strong>Mint</strong><small>{open ? "Hide guide" : "Show me how"}</small></span></button>
  </div>;
}
