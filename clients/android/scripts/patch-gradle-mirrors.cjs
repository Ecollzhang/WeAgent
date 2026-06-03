const fs = require('fs')
const path = require('path')

const root = path.join(__dirname, '..')

const mirrorRepositories = `repositories {
        maven { url 'https://maven.aliyun.com/repository/google' }
        maven { url 'https://maven.aliyun.com/repository/public' }
        maven { url 'https://mirrors.cloud.tencent.com/nexus/repository/maven-public/' }
        google()
        mavenCentral()
    }`

const compactMirrorRepositories = `repositories {
    maven { url 'https://maven.aliyun.com/repository/google' }
    maven { url 'https://maven.aliyun.com/repository/public' }
    maven { url 'https://mirrors.cloud.tencent.com/nexus/repository/maven-public/' }
    google()
    mavenCentral()
}`

const cordovaMirrorRepositories = `repositories {
    maven { url 'https://maven.aliyun.com/repository/google' }
    maven { url 'https://maven.aliyun.com/repository/public' }
    maven { url 'https://mirrors.cloud.tencent.com/nexus/repository/maven-public/' }
    google()
    mavenCentral()
    flatDir{
        dirs 'src/main/libs', 'libs'
    }
}`

function patchFile(filePath) {
  if (!fs.existsSync(filePath)) return false
  let content = fs.readFileSync(filePath, 'utf8')
  const before = content

  content = content.replace(
    /repositories\s*\{\s*google\(\)\s*mavenCentral\(\)\s*maven\s*\{\s*url\s+"https:\/\/plugins\.gradle\.org\/m2\/"\s*\}\s*\}/g,
    `${mirrorRepositories.slice(0, -1)}
        maven { url 'https://plugins.gradle.org/m2/' }
    }`
  )

  content = content.replace(
    /repositories\s*\{\s*google\(\)\s*mavenCentral\(\)\s*flatDir\s*\{\s*dirs\s+'src\/main\/libs',\s*'libs'\s*\}\s*\}/g,
    cordovaMirrorRepositories
  )

  content = content.replace(
    /repositories\s*\{\s*google\(\)\s*mavenCentral\(\)\s*\}/g,
    compactMirrorRepositories
  )

  if (content !== before) {
    fs.writeFileSync(filePath, content, 'utf8')
    return true
  }
  return false
}

function patchWrapper(filePath) {
  if (!fs.existsSync(filePath)) return false
  let content = fs.readFileSync(filePath, 'utf8')
  const before = content

  content = content.replace(
    /distributionUrl=https\\:\/\/services\.gradle\.org\/distributions\/gradle-([^-]+)-(all|bin)\.zip/g,
    'distributionUrl=https\\://mirrors.cloud.tencent.com/gradle/gradle-$1-$2.zip'
  )

  if (content !== before) {
    fs.writeFileSync(filePath, content, 'utf8')
    return true
  }
  return false
}

function patchGradleProperties(filePath) {
  if (!fs.existsSync(filePath)) return false
  let content = fs.readFileSync(filePath, 'utf8')
  const before = content

  if (!/^android\.overridePathCheck=true$/m.test(content)) {
    content = content.trimEnd() + '\nandroid.overridePathCheck=true\n'
  }

  if (content !== before) {
    fs.writeFileSync(filePath, content, 'utf8')
    return true
  }
  return false
}

const files = [
  path.join(root, 'node_modules', '@capacitor', 'android', 'capacitor', 'build.gradle'),
  path.join(root, 'android', 'build.gradle'),
  path.join(root, 'android', 'capacitor-cordova-android-plugins', 'build.gradle'),
]

const wrapperFiles = [
  path.join(root, 'android', 'gradle', 'wrapper', 'gradle-wrapper.properties'),
]

const gradlePropertiesFiles = [
  path.join(root, 'android', 'gradle.properties'),
]

const changed = [
  ...files.filter(patchFile),
  ...wrapperFiles.filter(patchWrapper),
  ...gradlePropertiesFiles.filter(patchGradleProperties),
]
if (changed.length) {
  changed.forEach(file => console.log(`Patched Gradle mirrors: ${path.relative(root, file)}`))
} else {
  console.log('Gradle mirrors already patched or Android dependencies are not installed yet.')
}
