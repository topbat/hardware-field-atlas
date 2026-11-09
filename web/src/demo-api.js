import { sitePath } from './deployment.js';
import { categories } from './labels.js';

let snapshot;
const categoryNames = new Map(categories.map(({ id, label }) => [id, label]));

async function loadCatalog() {
  snapshot ??= fetch(sitePath('demo/catalog.json')).then(async (response) => {
    if (!response.ok) throw new Error('档案暂时无法加载，请重试。');
    return JSON.parse(await response.text(), (_key, value) => (
      typeof value === 'string' && value.startsWith('/assets/') ? sitePath(value) : value
    )).products;
  }).catch((error) => {
    snapshot = undefined;
    throw error;
  });
  return snapshot;
}

const normalize = (value) => value.normalize('NFKC').toLowerCase();
const compact = (value) => value.replace(/[^\p{L}\p{N}]/gu, '');
const tokens = (value) => normalize(value || '').trim().split(/\s+/).filter(Boolean);
const partFields = (part) => [part.name, part.mpn, part.manufacturer];

function matches(terms, fields) {
  return terms.every((term) => fields.some((field) => {
    if (!field) return false;
    const value = normalize(field);
    const key = compact(term);
    return value.includes(term) || (key && compact(value).includes(key));
  }));
}

function search(products, params) {
  const terms = tokens(params.get('q'));
  const category = params.get('category');
  const kind = params.get('kind');
  const compute = params.get('compute');
  const model = params.get('model');
  const counts = new Map(categories.map(({ id }) => [id, 0]));
  const parts = [];
  const found = products.filter((product) => {
    if (kind && product.kind !== kind) return false;
    if (compute && !product.abilities.some((row) => row.compute === compute)) return false;
    if (model && Boolean(product.model) !== (model === 'true')) return false;
    const fields = [product.id, product.name, product.brand, product.tagline, product.revision,
      categoryNames.get(product.category), ...product.aliases, ...product.tags,
      ...product.parts.flatMap(partFields), ...product.abilities.map((row) => row.name)];
    if (!matches(terms, fields)) return false;
    counts.set(product.category, counts.get(product.category) + 1);
    if (category && product.category !== category) return false;
    for (const part of product.parts) {
      if (terms.length && matches(terms, partFields(part))) {
        parts.push({ productId: product.id, productName: product.name, part });
      }
    }
    return true;
  });
  return {
    products: found.slice(0, Number(params.get('limit')) || 100),
    total: found.length,
    parts: parts.slice(0, 150),
    categories: categories.map(({ id, label }) => ({ id, label, count: counts.get(id) })),
  };
}

function readLocal(key) {
  try {
    const entries = JSON.parse(localStorage.getItem('hardware-atlas.demo.' + key) || '[]');
    return Array.isArray(entries) ? entries : [];
  } catch {
    return [];
  }
}

function writeLocal(key, entries) {
  try {
    localStorage.setItem('hardware-atlas.demo.' + key, JSON.stringify(entries.slice(0, 20)));
  } catch {
    throw new Error('浏览器暂时无法保存研究数据。');
  }
}

function researchMatches(products, query) {
  const strict = search(products, new URLSearchParams({ q: query, limit: '4' })).products;
  if (strict.length) return strict;
  const question = compact(normalize(query));
  return products.filter((product) => (
    [product.name, ...product.aliases, ...product.parts.map((part) => part.mpn)].some((field) => {
      const key = compact(normalize(field || ''));
      return key.length >= 4 && question.includes(key);
    })
  )).slice(0, 4);
}

function research(products, body) {
  const { query, workflow, productIds, partId, useMemory } = body;
  const selected = productIds.length
    ? productIds.map((id) => products.find((product) => product.id === id)).filter(Boolean)
    : researchMatches(products, query);
  const citations = new Map();

  function cite(product, ids) {
    return ids.flatMap((id) => {
      const source = product.sources.find((item) => item.id === id);
      if (!source) return [];
      const key = product.id + ':' + id;
      citations.set(key, { ...source, id: key, productId: product.id });
      return ['[' + key + ']'];
    }).join(' ');
  }

  const results = selected.flatMap((product) => {
    if (partId) {
      const part = product.parts.find((item) => item.id === partId);
      if (product !== selected[0] || !part?.sourceIds.length) return [];
      return [product.name + '\n• ' + [part.name, part.role, part.mpn].filter(Boolean).join(' · ') + ' ' + cite(product, part.sourceIds)];
    }
    let rows;
    if (workflow === 'build') {
      rows = (product.build?.steps || []).map((step, index) => {
        const evidence = cite(product, product.build.stepSourceIds?.[index] || []);
        return (index + 1) + '. ' + step + ' ' + (evidence || '（编辑建议）');
      });
    } else {
      const fields = workflow === 'compare' ? product.abilities : [...product.parts, ...product.specs];
      const sourced = fields.filter((row) => row.sourceIds.length);
      const matching = sourced.filter((row) => matches(tokens(query), [row.name, row.label, row.mpn, row.role, row.value]));
      rows = (matching.length ? matching : sourced).slice(0, 5).map((row) => (
        '• ' + [row.name || row.label, row.value || row.role || row.offline, row.mpn].filter(Boolean).join(' · ') + ' ' + cite(product, row.sourceIds)
      ));
    }
    return rows.length ? [product.name + '\n' + rows.join('\n')] : [];
  });
  const notes = useMemory ? readLocal('notes').slice(0, 3) : [];
  const answer = (results.join('\n\n') || '没有找到可引用的证据。试试输入确切的产品、品牌或料号，或选择一个档案。')
    + (notes.length ? '\n\n本次附带的研究笔记\n' + notes.map((note) => '• ' + note.text).join('\n') : '');
  return {
    id: crypto.randomUUID(), query, mode: 'catalog', answer, citations: [...citations.values()],
    productIds: selected.map((product) => product.id), createdAt: new Date().toISOString(),
    steps: [
      { name: '定位范围', detail: '匹配 ' + selected.length + ' 份公开档案。' },
      { name: '汇集证据', detail: '引用 ' + citations.size + ' 条档案来源。' },
    ],
    warning: '在线体验使用公开档案检索。研究记录和笔记保存在当前浏览器。',
  };
}

export async function demoRequest(path, { method, body, signal }) {
  const url = new URL(path, window.location.origin);
  const route = url.pathname;
  if (route === '/research/config') return { visionEnabled: false };
  if (route === '/research/history') {
    if (method === 'DELETE') return writeLocal('history', []);
    return { runs: readLocal('history') };
  }
  if (route === '/research/notes') {
    const notes = readLocal('notes');
    if (method === 'POST') {
      return writeLocal('notes', [{ id: crypto.randomUUID(), text: body.text, createdAt: new Date().toISOString() }, ...notes]);
    }
    return { notes };
  }
  if (route.startsWith('/research/notes/') && method === 'DELETE') {
    const id = route.split('/').at(-1);
    return writeLocal('notes', readLocal('notes').filter((note) => note.id !== id));
  }
  const products = await loadCatalog();
  signal?.throwIfAborted();
  if (route === '/catalog') return search(products, url.searchParams);
  if (route.startsWith('/products/')) {
    const product = products.find((item) => item.id === route.split('/').at(-1));
    if (product) return product;
  }
  if (route === '/compare') {
    const ids = (url.searchParams.get('ids') || '').split(',');
    const selected = ids.map((id) => products.find((product) => product.id === id));
    if (selected.every(Boolean)) return { products: selected };
  }
  if (route === '/research/run' && method === 'POST') {
    const run = research(products, body);
    writeLocal('history', [run, ...readLocal('history')]);
    return run;
  }
  throw new Error('没有找到这条档案。');
}
