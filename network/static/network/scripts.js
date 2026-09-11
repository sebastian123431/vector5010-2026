document.addEventListener('DOMContentLoaded', function() {
    const btn = document.getElementById('btn-semantic');
    if (btn) {
        btn.addEventListener('click', loadNetwork);
    }
});

function loadNetwork() {
    const container = document.getElementById('3d-graph');
    if (!container) return console.error('Contenedor 3d-graph no encontrado');
    const Graph = ForceGraph3D()(container)
      .enableImprovedLayout(false)     // desactivar improvedLayout
      .linkDirectionalParticles(2);

    fetch('neuronal/data/')
      .then(res => res.json())
      .then(data => {
          if (!data.nodes || !data.edges) return console.error('Datos inválidos', data);
          Graph.graphData({
              nodes: data.nodes,
              links: data.edges.map(e => ({
                  source: e.from,
                  target: e.to,
                  value: e.value || 1
              }))
          });
      })
      .catch(err => console.error('Fetch error:', err));
}
