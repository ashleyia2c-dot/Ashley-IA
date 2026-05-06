#!/usr/bin/env node
/**
 * sync-assets.js — Copia assets/mobile/* del repo Reflex al www/ del Capacitor.
 *
 * Single source of truth: el HTML/CSS/JS móvil vive en assets/mobile/ del
 * repo principal. El APK Capacitor lo bundlea. Cualquier cambio en la PWA
 * se refleja en el APK al re-buildear.
 *
 * Uso: node scripts/sync-assets.js
 *      (o vía: npm run sync-assets)
 */

'use strict';

const fs = require('fs');
const path = require('path');

const SRC = path.resolve(__dirname, '../..', 'assets', 'mobile');
const DST = path.resolve(__dirname, '..', 'www');
const EXTRA_ASSETS = [
  // Imágenes y recursos compartidos del root del .web/build/client/
  // que la app móvil referencia (avatar, etc.)
  { from: path.resolve(__dirname, '../..', 'assets', 'ashley_pfp.jpg'), name: 'ashley_pfp.jpg' },
];

function rmRf(target) {
  if (!fs.existsSync(target)) return;
  for (const entry of fs.readdirSync(target, { withFileTypes: true })) {
    const full = path.join(target, entry.name);
    if (entry.isDirectory()) {
      rmRf(full);
    } else {
      fs.unlinkSync(full);
    }
  }
  fs.rmdirSync(target);
}

function copyDir(srcDir, dstDir) {
  fs.mkdirSync(dstDir, { recursive: true });
  for (const entry of fs.readdirSync(srcDir, { withFileTypes: true })) {
    const srcPath = path.join(srcDir, entry.name);
    const dstPath = path.join(dstDir, entry.name);
    if (entry.isDirectory()) {
      copyDir(srcPath, dstPath);
    } else if (entry.isFile()) {
      fs.copyFileSync(srcPath, dstPath);
    }
  }
}

function main() {
  console.log(`[sync-assets] source: ${SRC}`);
  console.log(`[sync-assets] dest:   ${DST}`);

  if (!fs.existsSync(SRC)) {
    console.error(`[sync-assets] ERROR: source dir not found: ${SRC}`);
    process.exit(1);
  }

  // Limpiar destino y recrear
  rmRf(DST);
  fs.mkdirSync(DST, { recursive: true });

  // Copiar assets/mobile/* a www/
  copyDir(SRC, DST);
  console.log(`[sync-assets] Copied PWA assets.`);

  // Copiar recursos extra (avatar, etc.) al root de www/
  for (const asset of EXTRA_ASSETS) {
    if (!fs.existsSync(asset.from)) {
      console.warn(`[sync-assets] WARN: ${asset.from} not found, skipping`);
      continue;
    }
    fs.copyFileSync(asset.from, path.join(DST, asset.name));
    console.log(`[sync-assets] Copied extra: ${asset.name}`);
  }

  // Renombrar/duplicar index.html si está bajo el subfolder original
  // (El PWA está estructurado para vivir en /mobile/, pero Capacitor
  // sirve www/ como root. Aseguramos que index.html en root cargue.)
  const indexInRoot = path.join(DST, 'index.html');
  if (!fs.existsSync(indexInRoot)) {
    console.warn(`[sync-assets] WARN: no index.html in www/ root.`);
  }

  // En el HTML, los paths empiezan por /mobile/ y /ashley_pfp.jpg.
  // En el APK, el web root es www/, así que /mobile/X no funciona.
  // Hacemos un fix: en el HTML, reemplazar /mobile/ por ./
  // Y dejamos /ashley_pfp.jpg porque el avatar está copiado a www/ también.
  const html = fs.readFileSync(indexInRoot, 'utf-8');
  const fixed = html
    .replace(/href="\/mobile\//g, 'href="./')
    .replace(/src="\/mobile\//g, 'src="./')
    .replace(/scope: '\/mobile\/'/g, "scope: './'")
    .replace(/'\/mobile\/sw\.js'/g, "'./sw.js'");
  fs.writeFileSync(indexInRoot, fixed, 'utf-8');
  console.log(`[sync-assets] Fixed paths in index.html for Capacitor root.`);

  // Mismo fix en connect.html (aunque connect.html es para PC, no APK,
  // pero por completitud)
  const connectHtml = path.join(DST, 'connect.html');
  if (fs.existsSync(connectHtml)) {
    const c = fs.readFileSync(connectHtml, 'utf-8');
    const cFixed = c
      .replace(/href="\/mobile\//g, 'href="./')
      .replace(/src="\/mobile\//g, 'src="./');
    fs.writeFileSync(connectHtml, cFixed, 'utf-8');
  }

  // En el manifest, scope/start_url deben ser '/' o './'
  const manifestPath = path.join(DST, 'manifest.json');
  if (fs.existsSync(manifestPath)) {
    const m = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));
    m.start_url = '/';
    m.scope = '/';
    // Iconos también: /ashley_pfp.jpg sigue funcionando como root
    fs.writeFileSync(manifestPath, JSON.stringify(m, null, 2), 'utf-8');
    console.log(`[sync-assets] Fixed manifest.json paths for Capacitor.`);
  }

  // En sw.js, los paths cacheados también
  const swPath = path.join(DST, 'sw.js');
  if (fs.existsSync(swPath)) {
    const s = fs.readFileSync(swPath, 'utf-8');
    const sFixed = s
      .replace(/'\/mobile\/index\.html'/g, "'/index.html'")
      .replace(/'\/mobile\/app\.css'/g, "'/app.css'")
      .replace(/'\/mobile\/app\.js'/g, "'/app.js'")
      .replace(/'\/mobile\/manifest\.json'/g, "'/manifest.json'")
      .replace(/url\.pathname\.startsWith\('\/mobile\/'\)/g, "url.pathname.startsWith('/')");
    fs.writeFileSync(swPath, sFixed, 'utf-8');
    console.log(`[sync-assets] Fixed sw.js paths for Capacitor.`);
  }

  console.log(`[sync-assets] DONE. Web bundle ready in ${DST}`);
}

main();
