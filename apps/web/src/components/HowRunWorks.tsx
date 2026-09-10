interface HowRunWorksProps {
  mode?: 'mock' | 'live'
  modelId?: string | null
}

export default function HowRunWorks({ mode, modelId }: HowRunWorksProps) {
  return (
    <section className="how-grid run-how" aria-labelledby="how-heading">
      <div>
        <div className="section-kicker"><span>03</span> evidence contract</div>
        <h2 id="how-heading">How this run works</h2>
        <p className="how-scope">{mode === 'mock'
          ? 'Sample replay: these are the live workflow roles. No providers are called in this sample.'
          : 'Live workflow roles. Plans propose changes; the recorded test gates decide whether a patch is verified.'}</p>
        {mode === 'live' && modelId && <p className="how-model"><span>Recorded NVIDIA model</span><code>{modelId}</code></p>}
      </div>
      <ol>
        <li><span>Nebius Token Factory</span><p>Hosts the model inference used to propose and repair migration candidates.</p></li>
        <li><span>NVIDIA Nemotron</span><p>Produces three grounded strategies and source changes; it does not choose the winner.</p></li>
        <li><span>Tavily</span><p>Searches for official migration guidance. Retained sources may also include directly retrieved official documentation.</p></li>
        <li><span>Nebius Sandboxes</span><p>Execute candidates from one prepared baseline, measure tests and dependencies, and revalidate the selected patch.</p></li>
      </ol>
    </section>
  )
}
