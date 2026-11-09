export const onlineDemo = import.meta.env.MODE === 'pages';

export function sitePath(path) {
  return import.meta.env.BASE_URL + path.replace(/^\//, '');
}

export function bomPath(id) {
  return onlineDemo ? sitePath('demo/bom/' + id + '.csv') : '/api/products/' + id + '/bom.csv';
}
