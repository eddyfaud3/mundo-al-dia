"use client";

import { useState } from "react";

export default function NavigationMenu() {
  const [open, setOpen] = useState(false);

  function closeMenu() {
    setOpen(false);
  }

  return (
    <nav className="site-navigation" aria-label="Navegación principal">
      <button
        className="mobile-menu-toggle"
        type="button"
        aria-label={open ? "Cerrar menú" : "Abrir menú"}
        aria-expanded={open}
        aria-controls="main-navigation-links"
        onClick={() => setOpen(!open)}
      >
        <span className="menu-toggle-icon" aria-hidden="true">{open ? "×" : "☰"}</span>
        <span className="menu-toggle-text">{open ? "Cerrar" : "Menú"}</span>
      </button>
      <div id="main-navigation-links" className={`navigation-links${open ? " is-open" : ""}`}>
        <a href="/" aria-label="Inicio" title="Inicio" onClick={closeMenu} className="home-navigation-link">
          <span aria-hidden="true">🏠</span><span className="home-link-text">Inicio</span>
        </a>
        <a href="#ultimas" onClick={closeMenu}>Últimas noticias</a>
        <a href="#contacto" onClick={closeMenu}>Contacto</a>
        <a href="/admin" className="admin-link" onClick={closeMenu}>🔐 Admin</a>
      </div>
    </nav>
  );
}
