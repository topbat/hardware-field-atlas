import { lazy, Suspense, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, HashRouter, Link, NavLink, Route, Routes, useLocation } from 'react-router-dom';
import { ArrowUpRight, Atom, Cube, Flask, GitDiff, ListMagnifyingGlass, X } from '@phosphor-icons/react';
import { Catalog } from './pages/Catalog.jsx';
import { Compare } from './pages/Compare.jsx';
import { Product } from './pages/Product.jsx';
import { Research } from './pages/Research.jsx';
import { onlineDemo } from './deployment.js';
import './styles.css';

const Admin = lazy(() => import('./pages/Admin.jsx').then((module) => ({ default: module.Admin })));

const compareKey = 'hardware-atlas.compare.v1';

function initialCompare() {
  try {
    const ids = JSON.parse(localStorage.getItem(compareKey) || '[]');
    return Array.isArray(ids) ? [...new Set(ids.filter((id) => typeof id === 'string'))].slice(0, 4) : [];
  } catch {
    return [];
  }
}

function App() {
  const [compareIds, setCompareIds] = useState(initialCompare);
  const location = useLocation();
  const compareUrl = compareIds.length >= 2 ? `/compare?ids=${encodeURIComponent(compareIds.join(','))}` : '/compare';
  useEffect(() => {
    try {
      localStorage.setItem(compareKey, JSON.stringify(compareIds));
    } catch {
      // Comparing still works when storage is unavailable.
    }
  }, [compareIds]);
  useEffect(() => {
    if (location.hash) return;
    window.scrollTo(0, 0);
  }, [location.pathname]);

  const toggleCompare = (id) => setCompareIds((ids) => (
    ids.includes(id) ? ids.filter((value) => value !== id) : ids.length < 4 ? [...ids, id] : ids
  ));
  const selection = { ids: compareIds, toggle: toggleCompare, set: setCompareIds, url: compareUrl };

  return (
    <>
      <a className="skip-link" href="#main-content" onClick={onlineDemo ? (event) => {
        event.preventDefault();
        document.getElementById('main-content')?.focus();
      } : undefined}>跳到内容</a>
      <header className="topbar">
        <div className="wrap topbar-inner">
          <Link to="/" className="brand" aria-label="硬件志首页">
            <span className="brand-mark"><Cube weight="duotone" size={25} /></span>
            <span><strong>硬件志</strong><small>HARDWARE ATLAS</small></span>
          </Link>
          <nav className="navigation" aria-label="主导航">
            <NavLink to="/" end><ListMagnifyingGlass size={18} /><span>硬件档案</span></NavLink>
            <NavLink to={compareUrl}><GitDiff size={18} /><span>对比台</span>{compareIds.length ? <small>{compareIds.length}</small> : null}</NavLink>
            <NavLink to="/research"><Flask size={18} /><span>研究室</span></NavLink>
          </nav>
          <Link className="header-cta" to="/research">开始研究 <ArrowUpRight size={15} /></Link>
        </div>
      </header>
      <main id="main-content" className="main-content" tabIndex={onlineDemo ? -1 : undefined}>
        <Routes>
          <Route path="/" element={<Catalog selection={selection} />} />
          <Route path="/products/:id" element={<Product selection={selection} />} />
          <Route path="/compare" element={<Compare selection={selection} />} />
          <Route path="/research" element={<Research />} />
          {!onlineDemo && <Route path="/admin" element={<Suspense fallback={<div className="wrap page-top" role="status">正在打开内容审核…</div>}><Admin /></Suspense>} />}
          <Route path="*" element={<div className="wrap page-top"><h1>找不到这个页面</h1><Link className="button" to="/">返回硬件档案</Link></div>} />
        </Routes>
      </main>
      {compareIds.length && !location.pathname.startsWith('/compare') ? (
        <div className="compare-tray">
          <div><GitDiff size={19} /><span>对比台 <strong>{compareIds.length}/4</strong></span></div>
          {compareIds.length >= 2 ? <Link className="button primary small" to={compareUrl}>打开对比</Link> : <span className="muted">再选一款</span>}
          <button className="icon-button" aria-label="清空对比" onClick={() => setCompareIds([])}><X size={18} /></button>
        </div>
      ) : null}
      <footer className="footer">
        <div className="wrap footer-inner">
          <div><Atom size={22} /><span><strong>硬件志</strong><small>HARDWARE ATLAS</small></span></div>
          <p>从一个部件开始，理解整台设备。</p>
          <Link to="/research">打开研究室 <ArrowUpRight size={15} /></Link>
        </div>
      </footer>
    </>
  );
}

const Router = onlineDemo ? HashRouter : BrowserRouter;
createRoot(document.getElementById('root')).render(<Router><App /></Router>);
