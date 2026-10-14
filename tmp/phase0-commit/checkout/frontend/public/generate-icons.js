/**
 * Generate placeholder PNG icons (run once locally).
 * For production, replace with actual icon files.
 * 
 * Usage: node generate-icons.js
 * Requires: npm install canvas
 */

const fs = require('fs')
const path = require('path')

// Placeholder: use this to generate real PNGs
console.log(`
Icon generation placeholder. To create real icons:

1. Install canvas:
   npm install canvas

2. Use this script to generate 192x192 and 512x512 PNG files

3. Or use ImageMagick:
   convert -size 192x192 xc:white -fill '#3b82f6' -draw "circle 96,96 96,10" icon-192.png

For now, using placeholder SVG as data URI in manifest.
`)

// For development, use inline SVG data URI
const svgIconBase64 = Buffer.from(
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 192 192">
    <rect fill="#3b82f6" width="192" height="192"/>
    <text x="96" y="110" font-size="80" fill="white" text-anchor="middle" font-family="Arial">CoS</text>
  </svg>`
).toString('base64')

console.log('Placeholder SVG icon (use in manifest.json for now)')
console.log(`data:image/svg+xml;base64,${svgIconBase64}`)
