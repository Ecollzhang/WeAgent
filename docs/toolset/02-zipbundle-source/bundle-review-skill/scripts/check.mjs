const checks = [
  'changed files have focused scope',
  'security-sensitive behavior is documented',
  'tests cover the user-visible workflow',
]

for (const check of checks) {
  console.log(`[check] ${check}`)
}
