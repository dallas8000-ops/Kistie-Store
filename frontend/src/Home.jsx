function Home() {
  return (
    <div className="text-center p-2">
      <h1>Welcome to Kistie Store</h1>
      <small className="d-block mb-2 react-subtle">Tukusanyukidde mu Kistie Store</small>
      <p className="lead react-lead">Shop the latest in women&apos;s clothing, accessories, jewelry, shoes, rings, perfume, and lingerie. Curated for East Africa, inspired by global trends.</p>
      <small className="d-block mb-3 react-muted">Gula ebyambalo ebipya by&apos;abakyala, ebikwasirako, obusaale, engatto, n&apos;ebyobe. Bikozesebwa mu Afurika y&apos;Ebuvanjuba, bikubbibwa okuva mu nsi yonna.</small>
      <img src="/images/hero.jpg" alt="Fashion Hero" className="img-fluid rounded shadow" style={{maxHeight: '400px'}} />
    </div>
  );
}

export default Home;
