// Fills in the header and footer, reveals sections as they scroll in, and wires the copy button.
(function () {
  const here = location.pathname.split('/').pop() || 'index.html';
  const pages = [['index.html', 'Overview'], ['live.html', 'Live graphs']];
  document.querySelector('header.site').innerHTML =
    '<div class="in"><a class="brand" href="index.html"><span class="logo"><svg viewBox="0 0 60 40" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M2 22 H14 L19 10 L25 32 L31 4 L37 36 L42 16 L46 22 H58" stroke="#fff" stroke-width="5"/></svg></span><span>QuakeScope</span></a><nav>' +
    pages.map(([h, t]) => `<a href="${h}"${h === here ? ' class="here" aria-current="page"' : ''}>${t}</a>`).join('') +
    '<a class="ext" data-port="3000" data-path="/" href="#">Grafana &#8599;</a></nav></div>';
  document.querySelector('footer').innerHTML =
    'QuakeScope &middot; API telemetry project &middot; Earthquake data from the <a href="https://earthquake.usgs.gov/fdsnws/event/1/">USGS Earthquake API</a>';

  // Links to other services (Grafana, Prometheus, API) use this page's host and their own port.
  document.querySelectorAll('a[data-port]').forEach(a => {
    a.href = `${location.protocol}//${location.hostname}:${a.dataset.port}${a.dataset.path || '/'}`;
    a.target = '_blank';
    a.rel = 'noopener';
  });

  // Smooth reveal on scroll.
  const items = document.querySelectorAll('.rv');
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } }), { threshold: .12 });
    items.forEach(el => io.observe(el));
  } else items.forEach(el => el.classList.add('in'));

  // Copy buttons.
  document.querySelectorAll('.copy').forEach(btn => btn.addEventListener('click', async () => {
    const text = document.querySelector(btn.dataset.copy).textContent;
    try { await navigator.clipboard.writeText(text); btn.textContent = 'Copied'; }
    catch (e) { btn.textContent = 'Press Ctrl+C'; }
    setTimeout(() => (btn.textContent = 'Copy'), 1600);
  }));
})();
