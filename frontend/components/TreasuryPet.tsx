"use client";
import { useEffect, useRef, useState } from "react";
import { answerHelp, guides, suggestedQuestions, tour } from "../lib/pet-guide";

function Rodger() {
  return <svg className="mint-pet" viewBox="0 0 100 100" aria-hidden="true"><ellipse cx="50" cy="91" rx="30" ry="5" fill="#0f172a20"/><path className="mint-tail" d="M70 66 Q100 40 93 72 Q85 88 66 82" fill="#60a5fa" stroke="#1e3a8a" strokeWidth="3"/><path d="M24 36 L20 8 L41 23 M59 23 L80 8 L76 36" fill="#93c5fd" stroke="#1e3a8a" strokeWidth="3"/><path d="M27 27 L25 17 L34 24 M66 24 L75 17 L73 27" fill="#cbd5e1"/><rect x="28" y="58" width="44" height="30" rx="16" fill="#60a5fa" stroke="#1e3a8a" strokeWidth="3"/><rect x="18" y="23" width="64" height="45" rx="22" fill="#bfdbfe" stroke="#1e3a8a" strokeWidth="3"/><ellipse cx="50" cy="50" rx="24" ry="15" fill="#eff6ff"/><g className="mint-eyes" fill="#0f172a"><ellipse cx="37" cy="44" rx="4" ry="6"/><ellipse cx="63" cy="44" rx="4" ry="6"/></g><path d="M46 51 Q50 56 54 51 M50 56 Q43 62 39 57 M50 56 Q57 62 61 57" fill="none" stroke="#1e3a8a" strokeWidth="2.5" strokeLinecap="round"/><circle cx="28" cy="53" r="4" fill="#cbd5e1"/><circle cx="72" cy="53" r="4" fill="#cbd5e1"/><path d="M40 73 H60 M43 78 H57" stroke="#eff6ff" strokeWidth="3" strokeLinecap="round"/><ellipse cx="34" cy="88" rx="10" ry="5" fill="#1e3a8a"/><ellipse cx="66" cy="88" rx="10" ry="5"/></svg>;
}
const workspaceNames: Record<string, string> = { start: "Start here", company: "Company setup", automatic: "Automatic updates", overview: "Dashboard", forecast: "Cash forecast", energy: "Energy pilot", planning: "Cash planning", risk: "Risks", funding: "Funding & entities", integrations: "Data connections", governance: "Approvals & readiness", agents: "AI teams", analytics: "Analysis library" };
export default function TreasuryPet({ view, navigate, recordedDemo }: { view: string; navigate: (view: string) => void; recordedDemo: boolean }) {
  const [open, setOpen] = useState(false), [mode, setMode] = useState<"guide" | "ask" | "tour">("guide");
  const [step, setStep] = useState(0), [instruction, setInstruction] = useState(0);
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState<{ question: string; view: string; answer: ReturnType<typeof answerHelp> }[]>([]);
  const last = history.at(-1), answer = last?.view === view ? last.answer : undefined;
  const chat = useRef<HTMLDivElement>(null), input = useRef<HTMLInputElement>(null);
  const launcher = useRef<HTMLButtonElement>(null), closeButton = useRef<HTMLButtonElement>(null);
  useEffect(() => { if (open) closeButton.current?.focus(); }, [open]);
  useEffect(() => { if (open && mode === "ask") input.current?.focus(); }, [mode]);
  useEffect(() => { setQuestion(""); setInstruction(0); if (mode === "tour" && tour[step].view !== view) setMode("guide"); }, [view]);
  useEffect(() => { if (chat.current) chat.current.scrollTop = chat.current.scrollHeight; }, [history, open, mode]);
  const guide = guides[view] ?? guides.overview;
  const currentInstruction = Math.min(instruction, guide.steps.length - 1);
  function close() { setOpen(false); launcher.current?.focus(); }
  function move(index: number) { setStep(index); setMode("tour"); navigate(tour[index].view); }
  function ask(value: string) {
    if (!value.trim()) return;
    const response = answerHelp(value, { view, topic: answer?.topic, recordedDemo });
    setMode("ask"); setHistory(previous => [...previous, { question: value.trim(), view, answer: response }].slice(-12)); setQuestion(""); input.current?.focus();
  }
  return <div className="treasury-pet">
    {open && <aside id="mint-guide" className="pet-panel" aria-label="Rodger treasury usage guide" onKeyDown={e => { if (e.key === "Escape") { e.stopPropagation(); close(); } }}>
      <header className="pet-header"><Rodger/><div><strong>Hi, I’m Rodger!</strong><span>{workspaceNames[view] ?? "Your treasury guide"}</span></div><button ref={closeButton} className="pet-close" aria-label="Close Rodger guide" onClick={close}>×</button></header>
      <div className="pet-content"><p className="pet-mode">Built-in help · instant answers · no live AI call</p>
        <div className="pet-actions" aria-label="Rodger help modes"><button aria-pressed={mode === "guide"} onClick={() => setMode("guide")}>Screen guide</button><button aria-pressed={mode === "ask"} onClick={() => setMode("ask")}>Ask Rodger</button><button aria-pressed={mode === "tour"} onClick={() => move(0)}>Full app tour</button></div>
        {mode === "guide" && <>
          <label className="pet-workspace">Browse workspace guides<select value={guides[view] ? view : "overview"} onChange={e => navigate(e.target.value)}>{Object.keys(guides).map(key => <option key={key} value={key}>{workspaceNames[key] ?? guides[key].title}</option>)}</select></label>
          <h2>{guide.title}</h2><div className="pet-instruction" aria-live="polite"><p className="eyebrow">Step {currentInstruction + 1} of {guide.steps.length}</p><p>{guide.steps[currentInstruction]}</p></div>
          <div className="pet-actions"><button disabled={currentInstruction === 0} onClick={() => setInstruction(currentInstruction - 1)}>Previous instruction</button><button disabled={currentInstruction === guide.steps.length - 1} onClick={() => setInstruction(currentInstruction + 1)}>Next instruction →</button></div>
          <details className="pet-all-steps"><summary>Show all instructions</summary><ol>{guide.steps.map(s => <li key={s}>{s}</li>)}</ol></details>
          <p className="pet-section-label">Common questions on this screen</p><div className="pet-suggestions" aria-label="Suggested help questions">{suggestedQuestions(view).map(suggestion => <button key={suggestion} onClick={() => ask(suggestion)}>{suggestion}</button>)}</div>
        </>}
        {mode === "tour" && <div className="pet-tour"><p className="eyebrow">Step {step + 1} of {tour.length}</p><h2>{tour[step].title}</h2><p>{tour[step].text}</p><p className="muted">The tour opens screens and explains controls. It does not fill forms or submit records.</p><div className="pet-actions"><button disabled={step === 0} onClick={() => move(step - 1)}>Back</button>{step < tour.length - 1 ? <button onClick={() => move(step + 1)}>Next step →</button> : <button onClick={() => setMode("guide")}>Finish tour</button>}</div><button className="text-button" onClick={() => setMode("guide")}>Exit tour</button></div>}
        {mode === "ask" && <>
          <p className="pet-section-label">Ask about a control, a treasury term or an error. I explain the interface without inspecting your data.</p>
          <div className="pet-suggestions" aria-label="Suggested help questions">{(answer?.suggestions ?? suggestedQuestions(view)).map(suggestion => <button key={suggestion} onClick={() => ask(suggestion)}>{suggestion}</button>)}</div>
          {history.length > 0 && <><div ref={chat} className="pet-chat" role="log" aria-label="Rodger conversation" aria-live="polite" aria-relevant="additions">{history.map((turn, i) => <div key={i} className="pet-turn"><p className="pet-user"><strong>You · {workspaceNames[turn.view] ?? turn.view}</strong>{turn.question}</p><div className="pet-answer"><strong>Rodger · built-in guidance</strong><p>{turn.answer.text}</p>{turn.answer.view && <button className="text-button" onClick={() => { if (turn.answer.view) { navigate(turn.answer.view); setMode("guide"); } }}>Open {workspaceNames[turn.answer.view] ?? "workspace"} →</button>}</div></div>)}</div><div className="pet-chat-actions"><button disabled={!answer} onClick={() => ask("Give me an example")}>Give an example</button><button disabled={!answer} onClick={() => ask("More detail")}>More detail</button><button onClick={() => { setHistory([]); input.current?.focus(); }}>Clear conversation</button></div></>}
          <form className="pet-question" onSubmit={e => { e.preventDefault(); ask(question); }}><label htmlFor="mint-question">Ask how to use the app</label><div><input ref={input} id="mint-question" value={question} maxLength={300} onChange={e => setQuestion(e.target.value)} placeholder="How do I use this screen?"/><button type="submit" disabled={!question.trim()}>Ask</button></div></form>
        </>}
        <p className="pet-footnote">Session-only help; reload clears conversation. Questions and files are not sent to an AI service. Payments, trades and approvals remain in the human-controlled workflow.</p>
      </div>
    </aside>}
    <button ref={launcher} className="pet-launcher" aria-label={open ? "Hide Rodger treasury guide" : "Meet Rodger: help using this app"} aria-expanded={open} aria-controls="mint-guide" onClick={() => open ? close() : setOpen(true)}><Rodger/><span><strong>Rodger</strong><small>{open ? "Hide guide" : "Show me how"}</small></span></button>
  </div>;
}
