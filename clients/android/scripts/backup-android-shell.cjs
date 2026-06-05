const fs = require('fs')
const path = require('path')

const root = path.resolve(__dirname, '..')
const source = path.join(root, 'android')
const backup = path.join(root, 'android.backup-black-screen')

function assertInsideRoot(target) {
  const relative = path.relative(root, target)
  if (relative.startsWith('..') || path.isAbsolute(relative)) {
    throw new Error(`Refuse to touch path outside clients/android: ${target}`)
  }
}

assertInsideRoot(source)
assertInsideRoot(backup)

if (!fs.existsSync(source)) {
  console.log('Android shell does not exist, nothing to back up.')
  process.exit(0)
}

if (fs.existsSync(backup)) {
  throw new Error(`Backup already exists: ${backup}`)
}

fs.renameSync(source, backup)
console.log(`Backed up Android shell:\n${source}\n-> ${backup}`)
