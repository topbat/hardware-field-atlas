import { useEffect, useRef, useState } from 'react';
import { Circuitry, DownloadSimple, FileCode, Lightning } from '@phosphor-icons/react';
import { useSearchParams } from 'react-router-dom';
import { Empty, External, SourcesFor } from '../components.jsx';
import '../engineering-workbench.css';

const fitNames = { fitted: '参考装配', dnp: '不装配', unknown: '装配状态未列出' };
const sideNames = { top: '正面', bottom: '背面' };

function BoardMap({ board, selectedRef, side, select, setSide, product }) {
  if (!board) return <Empty>这一板版暂无可核验的 PCB 位号坐标。</Empty>;
  const placements = board.placements.filter((item) => item.side === side);
  const placementView = board.coordinateSource === 'placement';
  return (
    <figure className="engineering-board">
      <div className="engineering-board-toolbar">
        <strong><Circuitry size={17} /> {placementView ? 'PCB 贴装位置' : 'PCB 位号投影'}</strong>
        <div className="segmented" aria-label="PCB 板面">
          {Object.entries(sideNames).map(([id, name]) => (
            <button key={id} type="button" aria-pressed={side === id} onClick={() => setSide(id)}>{name}</button>
          ))}
        </div>
      </div>
      <div className="engineering-board-stage">
        <div className="engineering-board-outline" style={{ aspectRatio: board.width + ' / ' + board.height }}>
          {placements.map((item) => {
            const left = 100 * item.x / board.width;
            const top = 100 * item.y / board.height;
            return (
              <button
                key={item.ref}
                type="button"
                className="engineering-marker"
                style={{ left: (side === 'top' ? left : 100 - left) + '%', top: top + '%' }}
                aria-label={'PCB 位号 ' + item.ref}
                data-pcb-ref={item.ref}
                aria-pressed={selectedRef === item.ref}
                title={item.ref}
                onClick={() => select(item.ref)}
              >
                <span>{item.ref}</span>
              </button>
            );
          })}
          {!placements.length && <span className="engineering-board-empty">此面暂无已映射位号</span>}
        </div>
      </div>
      <figcaption>
        <p>
          {placementView ? '使用原厂贴装参考点，连接器参考点可能位于首针。' : '根据公开 PCB 布局图标注的位置绘制。'}
          仅显示已映射位号，背面按翻板后的视角显示。
        </p>
        <span className="mono">{board.width} × {board.height} mm · {placements.length} 个位号</span>
        <SourcesFor product={product} ids={board.sourceIds} />
      </figcaption>
    </figure>
  );
}

function downloadBom(productId, revision) {
  const rows = [
    ['板版', '位号', '物料', '值', '封装', '型号', '装配状态'],
    ...revision.bom.map((item) => [revision.label, item.ref, item.name, item.value, item.package, item.mpn, fitNames[item.fit]]),
  ];
  const csv = rows.map((row) => row.map((value) => {
    const cell = String(value ?? '');
    const safe = /^[=+@-]/.test(cell.trimStart()) || /^[\t\r\n]/.test(cell) ? "'" + cell : cell;
    return '"' + safe.replaceAll('"', '""') + '"';
  }).join(',')).join('\r\n');
  const url = URL.createObjectURL(new Blob(['\uFEFF', csv], { type: 'text/csv;charset=utf-8' }));
  const link = document.createElement('a');
  link.href = url;
  link.download = productId + '-' + revision.id + '-bom.csv';
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function BomAndBoard({ product, revision, selectedRef, selectRef }) {
  const [query, setQuery] = useState('');
  const [sideOverride, setSide] = useState(null);
  const rowViewport = useRef(null);
  const activeRow = useRef(null);
  const { bom, board, pins } = revision;
  const placements = new Map(board?.placements.map((item) => [item.ref, item]));
  const selected = bom.find((item) => item.ref === selectedRef);
  const selectedPlacement = placements.get(selectedRef);
  const side = (sideOverride?.ref === selectedRef ? sideOverride?.side : null) || selectedPlacement?.side || 'top';
  const terms = query.normalize('NFKC').trim().toLowerCase().split(/\s+/).filter(Boolean);

  function matches(item) {
    const value = [item.ref, item.name, item.value, item.package, item.mpn]
      .filter(Boolean).join(' ').normalize('NFKC').toLowerCase();
    return terms.every((term) => value.includes(term));
  }

  const rows = bom.filter(matches);

  function select(ref) {
    const item = bom.find((row) => row.ref === ref);
    if (item && !matches(item)) setQuery('');
    setSide(null);
    selectRef(ref);
  }

  useEffect(() => {
    const viewport = rowViewport.current;
    const row = activeRow.current;
    if (!viewport || !row) return;
    const bounds = viewport.getBoundingClientRect();
    const rowBounds = row.getBoundingClientRect();
    const headerHeight = viewport.querySelector('thead')?.getBoundingClientRect().height || 0;
    const firstVisibleY = bounds.top + headerHeight;
    if (rowBounds.top < firstVisibleY) viewport.scrollTop += rowBounds.top - firstVisibleY;
    if (rowBounds.bottom > bounds.bottom) viewport.scrollTop += rowBounds.bottom - bounds.bottom;
  }, [selectedRef, query]);

  return (
    <div className="engineering-layout">
      <section id="engineering-placement" className="surface engineering-placement" aria-label="PCB 位号">
        <BoardMap board={board} selectedRef={selectedRef} side={side} select={select} setSide={(value) => setSide({ ref: selectedRef, side: value })} product={product} />
        {selected ? (
          <div className="engineering-selected" aria-live="polite">
            <p className="engineering-selected-label">所选位号</p>
            <p><strong className="mono">{selected.ref}</strong> {selected.name}</p>
            <p className="muted">{[selected.value, selected.package, selected.mpn].filter(Boolean).join(' · ') || '物料规格未列出'}</p>
            <p className="muted">
              {fitNames[selected.fit]}
              {' · ' + (selectedPlacement ? sideNames[selectedPlacement.side] : '暂无位号坐标')}
              {selectedPlacement && ' · ' + selectedPlacement.x + ', ' + selectedPlacement.y + ' mm'}
              {selectedPlacement?.rotation != null && ' · ' + selectedPlacement.rotation + '°'}
            </p>
            {pins.filter((pin) => pin.ref === selectedRef).map((pin) => (
              <p key={pin.id} className="engineering-pin-reference">{pin.label} <code>{pin.signal}</code></p>
            ))}
            <SourcesFor product={product} ids={selected.sourceIds} />
          </div>
        ) : board && <p className="engineering-selected muted">选中 PCB 点位或 BOM 位号，即可查看对应物料与关联引脚。</p>}
      </section>

      <section className="surface engineering-bom" aria-labelledby="engineering-bom-title">
        <div className="engineering-section-header">
          <h3 id="engineering-bom-title">板版 BOM</h3>
          <div className="engineering-bom-actions">
            <span className="mono">{rows.length} / {bom.length} 位号</span>
            {bom.length > 0 && (
              <button type="button" className="button small" onClick={() => downloadBom(product.id, revision)}>
                <DownloadSimple size={16} /> 导出本板版 CSV
              </button>
            )}
          </div>
        </div>
        {bom.length ? (
          <>
            <label className="engineering-search">
              <span>筛选 BOM</span>
              <input
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="位号、型号、规格或封装"
              />
            </label>
            {rows.length ? (
              <div className="table-scroll engineering-table" ref={rowViewport}>
                <table className="data-table">
                  <thead><tr><th scope="col">位号</th><th scope="col">物料</th><th scope="col">装配</th></tr></thead>
                  <tbody>
                    {rows.map((item) => {
                      const isSelected = item.ref === selectedRef;
                      const placement = placements.get(item.ref);
                      return (
                        <tr
                          key={item.ref}
                          ref={isSelected ? activeRow : null}
                          data-bom-ref={item.ref}
                          data-selected={isSelected}
                          onClick={() => select(item.ref)}
                        >
                          <th scope="row">
                            <button
                              type="button"
                              className="engineering-ref"
                              aria-label={'BOM 位号 ' + item.ref}
                              aria-pressed={isSelected}
                            >{item.ref}</button>
                          </th>
                          <td><strong>{item.name}</strong><small>{[item.value, item.package, item.mpn].filter(Boolean).join(' · ')}</small></td>
                          <td>{fitNames[item.fit]}{placement && <small>{sideNames[placement.side]}</small>}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : <Empty>未找到符合筛选条件的位号。</Empty>}
          </>
        ) : <Empty>这一板版暂无可核验的独立 BOM。</Empty>}
      </section>
    </div>
  );
}

function RevisionEvidence({ product, revision, selectRef }) {
  const { files, firmware, rails, pins, bom } = revision;
  const fileById = new Map(files.map((file) => [file.id, file]));
  const railById = new Map(rails.map((rail) => [rail.id, rail]));
  const pinById = new Map(pins.map((pin) => [pin.id, pin]));
  const availableRefs = new Set(bom.map((item) => item.ref));

  return (
    <>
      <div className="engineering-evidence-grid">
        <section className="surface engineering-evidence">
          <h3><FileCode size={18} /> 固件与板版配置</h3>
          {firmware.length ? (
            <ul>
              {firmware.map((item) => {
                const file = fileById.get(item.fileId);
                return (
                  <li key={item.name + '-' + item.version}>
                    <p><strong>{item.name}</strong> <code>{item.version}</code></p>
                    <p>{item.note}</p>
                    {item.pinIds.length > 0 && (
                      <p className="engineering-chip-line">
                        {item.pinIds.map((id) => <code key={id}>{pinById.get(id)?.signal}</code>)}
                      </p>
                    )}
                    {file && <External className="inline-link" href={file.url}>{file.name}</External>}
                    <SourcesFor product={product} ids={item.sourceIds} />
                  </li>
                );
              })}
            </ul>
          ) : <Empty>这一板版暂未关联固件。</Empty>}
        </section>

        <section className="surface engineering-evidence">
          <h3><Lightning size={18} /> 电压与供电</h3>
          {rails.length ? (
            <ul>
              {rails.map((rail) => (
                <li key={rail.id}>
                  <p><strong>{rail.label}</strong> <code>{rail.volts} V</code></p>
                  <p>{rail.note}</p>
                  <SourcesFor product={product} ids={rail.sourceIds} />
                </li>
              ))}
            </ul>
          ) : <Empty>这一板版暂未关联供电信息。</Empty>}
        </section>
      </div>

      <section className="surface engineering-evidence">
        <h3>引脚与信号</h3>
        {pins.length ? (
          <div className="table-scroll engineering-pin-table">
            <table className="data-table">
              <thead><tr><th scope="col">引脚</th><th scope="col">信号</th><th scope="col">电压关联</th><th scope="col">位号与说明</th></tr></thead>
              <tbody>
                {pins.map((pin) => {
                  const rail = railById.get(pin.railId);
                  return (
                    <tr key={pin.id}>
                      <th scope="row">{pin.label}</th>
                      <td><code>{pin.signal}</code></td>
                      <td>{rail ? rail.label + ' · ' + rail.volts + ' V' : '未标注'}</td>
                      <td>
                        {availableRefs.has(pin.ref) ? (
                          <button type="button" className="engineering-ref" onClick={() => selectRef(pin.ref)}>{pin.ref}</button>
                        ) : pin.ref && <code>{pin.ref}</code>}
                        <small>{pin.note}</small>
                        <SourcesFor product={product} ids={pin.sourceIds} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : <Empty>这一板版暂未关联引脚资料。</Empty>}
      </section>

      <section className="surface engineering-evidence">
        <h3>原始设计与配置文件</h3>
        {files.length ? (
          <ul className="engineering-file-list">
            {files.map((file) => (
              <li key={file.id}>
                <External className="inline-link" href={file.url}>{file.name}</External>
                {file.note && <p>{file.note}</p>}
                {file.sha256 && <p className="engineering-digest"><strong>SHA-256</strong> <code>{file.sha256}</code></p>}
                <SourcesFor product={product} ids={file.sourceIds} />
              </li>
            ))}
          </ul>
        ) : <Empty>这一板版暂未关联原始文件。</Empty>}
      </section>
    </>
  );
}

export function EngineeringWorkbench({ product }) {
  const [params, setParams] = useSearchParams();
  const { revisions, skus } = product.engineering;
  const revision = revisions.find((item) => item.id === params.get('board')) || revisions[0];
  const availableSkus = revision.skuIds.map((id) => skus.find((item) => item.id === id));
  const sku = availableSkus.find((item) => item.id === params.get('sku')) || availableSkus[0];
  const requestedRef = params.get('ref');
  const selectedRef = revision.bom.some((item) => item.ref === requestedRef) ? requestedRef : null;

  function changeRevision(id) {
    const target = revisions.find((item) => item.id === id);
    setParams((current) => {
      const next = new URLSearchParams(current);
      next.set('board', id);
      next.set('sku', target.skuIds.includes(sku.id) ? sku.id : target.skuIds[0]);
      next.delete('ref');
      return next;
    });
  }

  function selectRef(ref) {
    setParams((current) => {
      const next = new URLSearchParams(current);
      next.set('board', revision.id);
      next.set('sku', sku.id);
      next.set('ref', ref);
      return next;
    }, { replace: true });
  }

  return (
    <div className="engineering-workbench">
      <section className="surface engineering-release" aria-labelledby="engineering-title">
        <div className="engineering-release-title">
          <p className="eyebrow"><span className="signal-dot" /> BOARD ARCHIVE</p>
          <h2 id="engineering-title">版本化部件档案</h2>
          <p>{revision.note}</p>
          <SourcesFor product={product} ids={revision.sourceIds} />
        </div>
        <div className="engineering-controls">
          <label>
            <span>板版</span>
            <select value={revision.id} onChange={(event) => changeRevision(event.target.value)}>
              {revisions.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
            </select>
          </label>
          <label>
            <span>SKU</span>
            <select value={sku.id} onChange={(event) => {
              const id = event.target.value;
              setParams((current) => {
                const next = new URLSearchParams(current);
                next.set('board', revision.id);
                next.set('sku', id);
                return next;
              });
            }}>
              {availableSkus.map((item) => <option key={item.id} value={item.id}>{item.code}</option>)}
            </select>
          </label>
          <dl className="engineering-sku-data">
            <div><dt>模组</dt><dd>{sku.module}</dd></div>
            <div><dt>Flash</dt><dd>{sku.flash}</dd></div>
            <div><dt>PSRAM</dt><dd>{sku.psram}</dd></div>
            {sku.spiVoltage && <div><dt>模组 SPI 电压</dt><dd>{sku.spiVoltage}</dd></div>}
          </dl>
          <SourcesFor product={product} ids={sku.sourceIds} />
          {revision.bom.length > 0 && <p className="engineering-sku-note">BOM 和位号坐标来自该板版的公开参考设计。订货模组以所选 SKU 为准。</p>}
        </div>
      </section>
      <BomAndBoard key={revision.id} product={product} revision={revision} selectedRef={selectedRef} selectRef={selectRef} />
      <RevisionEvidence product={product} revision={revision} selectRef={(ref) => {
        selectRef(ref);
        document.getElementById('engineering-placement')?.scrollIntoView({ block: 'start' });
      }} />
    </div>
  );
}
