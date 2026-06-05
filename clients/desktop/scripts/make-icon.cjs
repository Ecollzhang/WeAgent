const fs = require('fs')
const path = require('path')

const root = path.join(__dirname, '..')
const pngPath = path.join(root, 'logo.png')
const icoPath = path.join(root, 'logo.ico')

if (!fs.existsSync(pngPath) && fs.existsSync(icoPath)) {
  const ico = fs.readFileSync(icoPath)
  const pngOffset = ico.indexOf(Buffer.from([0x89, 0x50, 0x4e, 0x47]))
  if (pngOffset >= 0) {
    fs.writeFileSync(pngPath, ico.subarray(pngOffset))
    console.log(`Restored ${path.relative(process.cwd(), pngPath)} from logo.ico`)
  }
}

const png = fs.readFileSync(pngPath)

if (png.length < 24 || png.toString('hex', 0, 8) !== '89504e470d0a1a0a') {
  throw new Error('logo.png must be a PNG file')
}

const width = png.readUInt32BE(16)
const height = png.readUInt32BE(20)
const iconWidth = width >= 256 ? 0 : width
const iconHeight = height >= 256 ? 0 : height

const header = Buffer.alloc(22)
header.writeUInt16LE(0, 0)
header.writeUInt16LE(1, 2)
header.writeUInt16LE(1, 4)
header.writeUInt8(iconWidth, 6)
header.writeUInt8(iconHeight, 7)
header.writeUInt8(0, 8)
header.writeUInt8(0, 9)
header.writeUInt16LE(1, 10)
header.writeUInt16LE(32, 12)
header.writeUInt32LE(png.length, 14)
header.writeUInt32LE(header.length, 18)

fs.writeFileSync(icoPath, Buffer.concat([header, png]))
console.log(`Wrote ${path.relative(process.cwd(), icoPath)}`)
