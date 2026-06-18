/* ── EliteX Trade — Main JS ── */

document.addEventListener("DOMContentLoaded", () => {

  // ── Navbar scroll (account for announcement bar height) ──
  const nav = document.getElementById("mainNav");
  const annBar = document.querySelector(".announcement-bar");
  const annH = annBar ? annBar.offsetHeight : 0;

  const syncNav = () => {
    nav.classList.toggle("scrolled", window.scrollY > annH + 10);
  };
  window.addEventListener("scroll", syncNav, { passive: true });
  syncNav();

  // ── Scroll reveal ──
  const revealItems = document.querySelectorAll(
    ".unique-card,.review-card,.plan-card,.faq-item,.team-card,.myfx-card,.about-stat-card,.broker-chip,.why-stat"
  );
  const ro = new IntersectionObserver((entries) => {
    entries.forEach((e, idx) => {
      if (e.isIntersecting) {
        e.target.style.opacity = "1";
        e.target.style.transform = "translateY(0)";
        ro.unobserve(e.target);
      }
    });
  }, { threshold: 0.08, rootMargin: "0px 0px -30px 0px" });

  revealItems.forEach((el, i) => {
    el.style.cssText += `opacity:0;transform:translateY(24px);
      transition:opacity .55s ease ${(i % 6) * 0.07}s, transform .55s ease ${(i % 6) * 0.07}s;`;
    ro.observe(el);
  });

  // ── Auto-dismiss flash messages ──
  document.querySelectorAll(".flash-item").forEach(el => {
    setTimeout(() => {
      const a = bootstrap.Alert.getOrCreateInstance(el);
      if (a) a.close();
    }, 5000);
  });

  // ── Pre-fill plan from URL ?plan= ──
  const planParam = new URLSearchParams(window.location.search).get("plan");
  if (planParam) {
    const sel = document.querySelector('select[name="plan"]');
    if (sel) {
      [...sel.options].forEach(o => {
        if (o.value.toLowerCase().includes(planParam.toLowerCase())) o.selected = true;
      });
    }
  }

  // ── Smooth anchor scroll ──
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener("click", e => {
      const id = a.getAttribute("href").slice(1);
      const el = document.getElementById(id);
      if (el) {
        e.preventDefault();
        el.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });
  });

});
