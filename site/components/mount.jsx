// Mount all React components into the DOM
function mount(id, Component) {
  const el = document.getElementById(id);
  if (!el) return;
  const root = ReactDOM.createRoot(el);
  root.render(<Component />);
}

mount('flow-mount', PhaseFlow);
mount('tools-mount', ToolGrid);
mount('agreement-mount', AgreementDemo);
mount('ranking-mount', HierarchicalRanking);
mount('apex-mount', ApexDeepDive);
