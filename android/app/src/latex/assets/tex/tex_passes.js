// Shared by the Android worker: fixes + extra passes.
(function (root) {
  const origReload = BusytexPipeline.prototype.reload_module;
  BusytexPipeline.prototype.reload_module = async function (...a) {
    const m = await origReload.apply(this, a);
    const cm = m.callMain;
    m.callMain = (args) => cm.call(m, Array.from(args || []));       // callMain edits its argument list; reused lists broke the 2nd TeX pass
    return m;
  };
  const AUX_EXT = /\.(aux|toc|out|lof|lot|bbl|blg|idx|ind|nav|snm|vrb|bcf|run\.xml|thm|brf)$/i;
  const needsRerun = r => {
    const tex = (r.logs || []).filter(l => /latex/.test(l.cmd));
    const last = tex.length ? tex[tex.length - 1].log || '' : '';
    return /Rerun to get|rerun LaTeX|Label\(s\) may have changed|undefined references|There were undefined/i.test(last);
  };
  root.compileWithPasses = async function (pipeline, files, main, bibtex, verbose, driver, pkgs, print) {
    let res = await pipeline.compile(files, main, bibtex, verbose, driver, pkgs);
    for (let pass = 2; pass <= 3 && res.exit_code === 0 && needsRerun(res); pass++) {
      print && print('Cross-references changed: running pass ' + pass);
      const M = await pipeline.Module;
      const FS = M.FS, PATH = M.PATH;
      const dir = PATH.join(pipeline.project_dir, PATH.dirname(main));
      const extra = [];
      for (const name of FS.readdir(dir)) {
        if (!AUX_EXT.test(name)) continue;
        const rel = PATH.join(PATH.dirname(main), name);
        extra.push({ path: rel, contents: FS.readFile(PATH.join(pipeline.project_dir, rel)) });
      }
      const keep = files.filter(f => !extra.some(e => e.path === f.path));
      res = await pipeline.compile(keep.concat(extra), main, bibtex, verbose, driver, pkgs);
    }
    return res;
  };
})(typeof self !== 'undefined' ? self : globalThis);
