// Web worker around BusyTeX. It looks at ALL project files (not only the main one) to decide which TeX data packages to load.
importScripts('busytex_pipeline.js');
const HINTS = ['fontspec'];
const origResolve = BusytexDataPackageResolver.prototype.resolve;
BusytexDataPackageResolver.prototype.resolve = function (files, main_tex_path, data_packages_js = null) {
  const names = new Set(HINTS);
  const re = /\\(?:usepackage|RequirePackage|documentclass)\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}/g;
  for (const f of files) {
    if (typeof f.contents === 'string' && /\.(tex|sty|cls)$/.test(f.path)) {
      for (const m of f.contents.matchAll(re)) m[1].split(',').forEach(n => n.trim() && names.add(n.trim()));
    }
  }
  const synthetic = Array.from(names).map(n => '\\usepackage{' + n + '}').join('\n');
  const patched = files.map(f => f.path === main_tex_path ? {...f, contents: synthetic} : f);
  return origResolve.call(this, patched, main_tex_path, data_packages_js);
};
self.pipeline = null;
onmessage = async ({data: {files, main_tex_path, bibtex, busytex_wasm, busytex_js, preload_data_packages_js, data_packages_js, texmf_local, preload, verbose, driver}}) => {
  if (busytex_wasm && busytex_js && preload_data_packages_js) {
    try {
      self.pipeline = new BusytexPipeline(busytex_js, busytex_wasm, data_packages_js, preload_data_packages_js, texmf_local,
        msg => postMessage({print: msg}), v => postMessage({initialized: v}), preload, BusytexPipeline.ScriptLoaderWorker);
    } catch (err) { postMessage({exception: 'Exception during initialization: ' + err + '\n' + err.stack}); }
  } else if (files && self.pipeline) {
    try { postMessage(await self.pipeline.compile(files, main_tex_path, bibtex, verbose, driver, data_packages_js)); }
    catch (err) { postMessage({exception: 'Exception during compilation: ' + err + '\n' + err.stack}); }
  }
};
