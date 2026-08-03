"""脚本审查引擎 — 基于成熟规则模式的代码审查，无需 LLM.

支持语言: Python, JavaScript/TypeScript, Vue, Go, Java, SQL, HTML
覆盖维度: security (安全), style (规范), logic (逻辑), performance (性能)

灵感来源:
- ESLint 规则集 (https://eslint.org/docs/latest/rules/)
- Bandit (Python security linter)
- Pylint / Ruff
- golangci-lint
- SonarQube 规则库
- OWASP Top 10 / CWE Top 25
"""
import re
import os
import hashlib
from collections import Counter


# ══════════════════════════════════════════════════════════════
#  规则定义
# ══════════════════════════════════════════════════════════════

class Rule:
    """一条审查规则."""
    def __init__(self, rule_id, severity, category, title, description, suggestion,
                 patterns, languages=None, file_exts=None, analysis=''):
        self.id = rule_id
        self.severity = severity        # critical | warning | suggestion
        self.category = category        # security | style | logic | performance
        self.title = title
        self.description = description
        self.suggestion = suggestion
        self.patterns = patterns if isinstance(patterns, list) else [patterns]
        self.languages = languages      # None = 适用所有语言
        self.file_exts = file_exts
        self.analysis = analysis        # 额外的分析说明（用于报告中的详细解读）


# ══════════════════════════════════════════════════════════════
#  安全规则 (Security) — OWASP Top 10 / CWE Top 25
# ══════════════════════════════════════════════════════════════

SECURITY_RULES = [
    Rule('SEC001', 'critical', 'security',
         '硬编码密钥 / 密码 / Token',
         '代码中包含明文密钥、密码或 API Token，一旦提交到版本控制系统将造成凭据泄露。'
         '攻击者可通过 git log 或公开仓库直接获取这些凭据，进而控制相关服务和资源。',
         '使用环境变量（os.environ / process.env）+ .env 文件存储敏感信息，.env 加入 .gitignore；'
         '生产环境使用密钥管理服务（AWS Secrets Manager / HashiCorp Vault / GitHub Secrets）',
         [r'(?i)(api[_-]?key|api[_-]?secret|secret[_-]?key|access[_-]?key)\s*[:=]\s*["\'][^"\']{8,}["\']',
          r'(?i)(password|passwd|pwd)\s*[:=]\s*["\'][^"\']{3,}["\']',
          r'(?i)(token|auth[_-]?token|jwt[_-]?secret)\s*[:=]\s*["\'][^"\']{8,}["\']',
          r'(?i)(private[_-]?key|ssh[_-]?key)\s*[:=]\s*["\'][^"\']{8,}["\']',
          r'(?i)\b(sk-[a-zA-Z0-9]{20,})\b',
          r'(?i)\b(ghp_[a-zA-Z0-9]{30,})\b',
          r'(?i)\b(AKIA[0-9A-Z]{16})\b',
          r'(?i)\b(eyJ[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{10,})\b',
          ],
         analysis='硬编码凭据是 OWASP A07:2021（身份识别和身份验证失效）中最常见的漏洞之一。'
                  '许多数据泄露事件的起因就是凭据被意外提交到公开仓库。'),

    Rule('SEC002', 'critical', 'security',
         'SQL 注入风险 — 字符串拼接构造查询',
         '使用字符串拼接（+、f-string、format()、模板字面量）构造 SQL 查询，攻击者可通过精心构造的'
         '用户输入注入恶意 SQL 代码，导致数据泄露、篡改或删除。这是 OWASP A03:2021 注入类漏洞的典型代表。',
         '使用参数化查询：Python 用 cursor.execute(sql, (param1, param2))；'
         'ORM 框架自带防注入（SQLAlchemy / Django ORM / Prisma / TypeORM）；'
         '如必须动态拼接，使用白名单校验表名/列名',
         [r'(?i)(execute|cursor\.execute|raw_query|rawQuery)\s*\(\s*[f"\'][^)]*(\+|\%s|%\(|\.format\()',
          r'(?i)(\"|\')\s*\+\s*\w+\s*\+\s*(\"|\')',
          r'(?i)SELECT\s+.*\s+FROM\s+.*\+',
          r'(?i)INSERT\s+INTO\s+.*\+',
          r'(?i)query\s*=\s*[\"\'][^\"\']*\+[^\"\']*[\"\']',
          r'(?i)`\$\{.*\}.*(?:SELECT|INSERT|DELETE|UPDATE|DROP)',
          ],
         analysis='SQL 注入连续多年位列 OWASP Top 3，即使是经验丰富的开发者也常犯此错误。'
                  '关键点在于：用户输入永远不能直接参与 SQL 语句的构建。'),

    Rule('SEC003', 'critical', 'security',
         'XSS 漏洞 — 未转义的 HTML 输出',
         '直接将用户输入设置为 innerHTML 或在 Vue/React 中使用 v-html/dangerouslySetInnerHTML 输出用户内容，'
         '攻击者可注入恶意脚本窃取用户 Cookie、会话令牌或重定向到钓鱼页面。',
         '使用 textContent 替代 innerHTML；Vue 中用模板插值 {{ }} 替代 v-html；'
         'React 中用 JSX 表达式替代 dangerouslySetInnerHTML；'
         '确实需要渲染 HTML 时使用 DOMPurify 等经过安全审计的清洗库',
         [r'\.innerHTML\s*=',
          r'v-html\s*=',
          r'dangerouslySetInnerHTML',
          r'document\.write\s*\(',
          r'(?i)eval\s*\(\s*(?!JSON\.parse)',
          ],
         analysis='XSS（跨站脚本攻击）是 Web 应用最常见的漏洞之一。'
                  '即使输入来自数据库而非直接用户输入，也应视为不可信（存储型 XSS）。'),

    Rule('SEC004', 'critical', 'security',
         '命令注入风险',
         '使用用户可控的输入拼接系统命令（os.system、subprocess + shell=True、exec），'
         '攻击者可注入额外的命令，获取服务器 Shell 权限。',
         '避免直接调用系统命令；必须使用时用 subprocess.run([cmd, arg1, arg2], shell=False) 列表形式传参；'
         '对用户输入用 shlex.quote() 转义；优先使用语言内置库而非外部命令',
         [r'(?i)os\.system\s*\(',
          r'(?i)subprocess\.(call|run|Popen)\s*\([^)]*shell\s*=\s*True',
          r'(?i)\bexec\s*\(\s*(?!$)',
          r'(?i)`[^`]*\$[{(]',
          ],
         analysis='命令注入在 Python/Node.js 应用中尤其危险，因为后端通常有较高的系统权限。'
                  '即使不使用 shell=True，直接拼接命令字符串也是不安全的。'),

    Rule('SEC005', 'warning', 'security',
         '不安全的加密算法',
         '使用了已被破解或不安全的加密算法（MD5、SHA1）或加密模式（ECB），'
         '无法有效保护数据机密性和完整性。',
         '哈希用 SHA-256/SHA-3（Python hashlib.sha256）；密码哈希用 bcrypt/scrypt/argon2；'
         '对称加密用 AES-256-GCM；非对称加密用 RSA-2048+ 或 ECC',
         [r'(?i)\b(md5|sha1)\b',
          r'(?i)hashlib\.(md5|sha1)\(',
          r'(?i)Crypto\.Cipher\.(DES|ARC4|Blowfish)\b',
          r'(?i)MODE_ECB\b',
          ],
         analysis='MD5 和 SHA1 已被证明存在碰撞攻击。对于密码存储，即使 SHA-256 也不够安全（缺少 salt + 迭代），'
                  '应使用专为密码设计的 bcrypt/scrypt/argon2。'),

    Rule('SEC006', 'warning', 'security',
         '路径遍历风险',
         '文件路径直接由用户输入拼接，攻击者可通过 ../ 跨目录访问任意文件（/etc/passwd、.env 等）。',
         '用 os.path.realpath() 规范化路径后检查是否在允许的目录内；'
         '用 os.path.basename() 去除路径部分；禁止用户输入中包含 ../ 或绝对路径',
         [r'(?i)open\s*\(\s*[^)]*\b(request\.(args|form|json|GET|POST)|input\s*\()',
          r'(?i)(read|write|delete|remove)\s*\([^)]*(\.\./|\.\.\\)',
          r'(?i)os\.path\.join\s*\([^)]*request\.',
          ],
         analysis='路径遍历（CWE-22）在文件上传、模板渲染、静态文件服务场景中尤其常见。'
                  '即使在前端做了后缀名校验，后端也应严格验证路径。'),

    Rule('SEC007', 'warning', 'security',
         '不安全的反序列化',
         '使用 pickle / yaml.load / marshal 等不安全反序列化函数处理不可信数据，'
         '可导致任意代码执行（RCE）。',
         '用 json.loads() 替代 pickle；YAML 必须使用 yaml.safe_load()；'
         '绝不反序列化来自网络请求、URL 参数、Cookie 等不可信来源的数据',
         [r'(?i)pickle\.(load|loads)\(',
          r'(?i)yaml\.load\s*\(\s*(?!.*Loader=yaml\.(Safe|Base)Loader)',
          r'(?i)marshal\.load',
          r'(?i)cPickle\.(load|loads)\(',
          ],
         analysis='Python 官方文档明确警告 pickle 不应处理不可信数据。'
                  'pickle.loads 可以执行任意 Python 代码，是最危险的 Python 函数之一。'),

    Rule('SEC008', 'suggestion', 'security',
         '缺少 HTTPS / TLS 证书验证',
         'HTTP 请求中 TLS 证书验证被禁用（verify=False 或 rejectUnauthorized: false），'
         '使应用容易受到中间人攻击（MITM）。',
         '生产环境必须启用 TLS 验证；开发环境如需跳过验证，限制在 localhost；'
         '使用环境变量区分 dev/prod 行为；内部服务间通信使用 mTLS',
         [r'(?i)verify\s*=\s*False',
          r'(?i)ssl\._create_unverified_context',
          r'(?i)CURLOPT_SSL_VERIFYPEER\s*,\s*(0|false)',
          r'(?i)rejectUnauthorized\s*:\s*false',
          ],
         analysis='禁用 TLS 验证让加密传输形同虚设。攻击者在同一网络（如公共 WiFi）中可轻易实施 MITM 攻击，'
                  '窃取 API Key、用户密码等敏感信息。'),
]

# ══════════════════════════════════════════════════════════════
#  规范规则 (Style)
# ══════════════════════════════════════════════════════════════

STYLE_RULES = [
    Rule('STY001', 'warning', 'style',
         '函数 / 方法过长',
         '函数或方法体量过大，通常意味着该函数承担了过多职责，违反单一职责原则（SRP），'
         '导致难以理解、测试和维护。',
         '将长函数按逻辑步骤拆分为多个职责单一的小函数；提取公共逻辑为私有方法；'
         '如果函数包含多个条件分支，考虑使用策略模式或查表法替代',
         [None],  # 按行数检测
         analysis='研究表明，函数长度与缺陷密度呈正相关。超过 200 行的函数，'
                  '单元测试覆盖难度显著增加，code review 效率大幅降低。'),

    Rule('STY002', 'warning', 'style',
         '检测到重复代码块',
         '多段相同或高度相似的代码出现在不同位置，这违反 DRY（Don\'t Repeat Yourself）原则。'
         '重复代码增加维护成本——修改一处逻辑需要同时修改所有副本，极易遗漏。',
         '提取重复代码到独立函数/工具模块；如果是相似但不完全相同的逻辑，用参数化/泛型处理差异；'
         '面向对象语言考虑提取到基类或 mixin',
         [None],  # 哈希检测
         analysis='代码重复是技术债务的主要来源之一。SonarQube 建议重复率应低于 3%。'),

    Rule('STY003', 'suggestion', 'style',
         '缺少文档注释',
         '公开函数、类或模块缺少文档字符串（docstring/JSDoc），降低了代码的可读性和可维护性。'
         '新成员或调用方无法快速理解 API 的用途、参数和返回值。',
         'Python: 为所有 public 函数/类添加 docstring（PEP 257）；'
         'JS/TS: 为 exported 函数添加 JSDoc (@param, @returns)；'
         'Go: 为 exported 函数添加 // FuncName does X 注释',
         [None],  # AST 级别检测
         analysis='好的文档注释不仅是给人类看的——IDE 和编辑器会解析它们提供智能提示。'
                  '缺少文档的 API 往往被误用，导致线上故障。'),

    Rule('STY004', 'suggestion', 'style',
         'TODO / FIXME / HACK 标记',
         '代码中残留临时标记，通常表示未完成的实现、已知的缺陷或临时绕过方案。'
         '这些标记往往长期存在而不被处理，成为隐藏的技术债务。',
         '将 TODO/FIXME 转为正式任务（创建 issue/ticket）并附上链接；'
         '或在本 PR 中完成标记的事项；HACK 应附上说明解释为什么用绕过的方案以及何时修复',
         [r'\b(TODO|FIXME|XXX|HACK|KLUDGE|WORKAROUND)\b'],
         analysis='经验表明，代码中的 TODO 标记平均存活时间超过 6 个月。'
                  '建议在 CI 中配置 TODO 扫描，阻止新的 TODO 进入主干分支。'),

    Rule('STY005', 'suggestion', 'style',
         '命名风格不一致',
         '变量/函数/类命名不符合语言社区约定俗成的风格，降低了代码的可读性和专业性。',
         'Python: snake_case 变量/函数, PascalCase 类, UPPER_CASE 常量；'
         'JS/TS: camelCase 变量/函数, PascalCase 类/组件, UPPER_CASE 常量；'
         'Go: camelCase 私有/PascalCase 公开；Java: camelCase 变量/PascalCase 类',
         [r'(?m)^def\s+[a-z]+[A-Z]\w*\s*\(',       # Python 函数名包含大写
          r'(?m)^class\s+[a-z]',                      # Python 类名小写开头
          r'(?m)\bconst\s+[a-z]+_[a-z]+\s*=\s*(?!.*[A-Z]{2,})',  # JS 下划线命名（非全大写常量）
          ]),

    Rule('STY006', 'suggestion', 'style',
         '可能未使用的导入',
         '导入的模块可能未被实际使用，增加了代码依赖、启动时间和认知负担。'
         '注意：此检测基于简单规则，可能存在误报，请人工确认。',
         '删除未使用的 import；Python 用 autoflake / ruff --select F401；'
         'JS/TS 用 ESLint no-unused-vars；Go 编译器会自动报 unused import 错误',
         [r'(?m)^from\s+(\S+)\s+import\s+\S+',   # 标记所有 from import 供人工检查
          ]),
]

# ══════════════════════════════════════════════════════════════
#  逻辑规则 (Logic)
# ══════════════════════════════════════════════════════════════

LOGIC_RULES = [
    Rule('LOG001', 'warning', 'logic',
         '可能的空值访问',
         '在未进行 null/None 检查的情况下访问对象属性或方法，可能导致运行时异常'
         '（TypeError / NullPointerException / Cannot read property of undefined）。',
         '使用可选链操作符（?.）、空值合并（?? / or）；添加显式的 if (obj) 判空；'
         'TypeScript 中开启 strictNullChecks；Python 3.10+ 可使用 X | None 类型标注',
         [r'(?m)^\s*\w+\.\w+\.\w+\s*[=\(]',       # 链式调用（可能中间为 null）
          r'(?i)\.(first|one|get)\s*\(\s*\)\.\w+',  # ORM 链式调用，first() 可返回 None
          ],
         analysis='空值错误（Null Reference Error）是生产环境中最常见的运行时异常之一。'
                  'Tony Hoare 称 null 引用是他"十亿美元的错误"。TypeScript strict 模式和 Python mypy 可以'
                  '在编译期捕获大部分空值问题。'),

    Rule('LOG002', 'warning', 'logic',
         '异常处理不当 — 吞异常 / 裸 except',
         '使用空的 except: pass 或 catch {} 吞掉了所有异常，掩盖了潜在 Bug，'
         '使问题难以排查。裸 except 还会捕获 KeyboardInterrupt 和 SystemExit，导致程序无法正常终止。',
         '捕获具体异常类型：except ValueError as e；记录异常日志：logger.exception()；'
         '只捕获你能处理的异常，无法处理的应重新抛出（raise）；'
         'JS 中避免 catch {} 空块，至少 console.error 记录',
         [r'(?i)except\s*(Exception\s*)?:\s*\n\s*(pass|continue|return\s+None)',
          r'(?i)except\s*:',
          r'try\s*\{[^}]*\}\s*catch\s*\(\s*(?:e\w*)?\s*\)\s*\{\s*\}',
          ],
         analysis='异常处理的核心原则是"尽早抛出，尽晚捕获"。裸 except 吞异常是生产环境中 Bug 难以追踪的'
                  '首要原因之一，因为异常栈信息被完全丢弃。'),

    Rule('LOG003', 'warning', 'logic',
         '变量条件赋值 — 可能未定义',
         '变量在 if/else 分支中有条件地赋值，但在分支外的代码中使用该变量时，'
         '某些路径下变量可能未被赋值导致 UnboundLocalError 或 undefined。',
         '在条件判断前为变量设置默认值；确保所有分支都覆盖了赋值；'
         '使用三元表达式或字典映射替代 if/else 赋值',
         [None],  # 动态检测
         analysis='这种情况在复杂条件分支中非常隐蔽，单元测试往往只覆盖了 happy path，'
                  '导致异常路径下的未定义变量错误在生产环境才暴露。'),

    Rule('LOG004', 'warning', 'logic',
         '竞态条件风险 — 共享状态无保护',
         '多线程 / 异步环境下对共享变量 / 全局状态的读写未加同步保护，'
         '可能导致数据不一致、丢失更新、或死锁。',
         'Python: threading.Lock / asyncio.Lock 保护临界区；使用 queue.Queue 传递数据而非共享变量；'
         'JS: Promise.all / async-await 正确编排异步流；Node.js 单线程事件循环天然无竞态，'
         '但数据库操作仍需注意',
         [r'(?i)\bglobal\s+\w+',            # Python global 在多线程中有风险
          r'(?i)\bnonlocal\s+\w+',           # 闭包中修改外部变量
          ]),

    Rule('LOG005', 'suggestion', 'logic',
         '死代码 — 不可达路径',
         'return / raise / throw / break / continue 之后的代码永远无法执行，'
         '属于无效代码，增加了维护者的困惑。',
         '删除不可达的代码；如果是有意保留（如作为文档），添加明确的注释说明；'
         '使用 IDE 的"检测不可达代码"功能或 linter 检查',
         [r'(?mi)(?:return|raise|throw)\s+[^;\n]+[\n;]\s*\S',
          ]),

    Rule('LOG006', 'critical', 'logic',
         '条件判断使用赋值而非比较',
         '在条件中使用单个 =（赋值）而非 ==/===（比较），导致条件结果恒为真/假，'
         '且变量值被意外修改。这是经典的 C/Java/JS 陷阱。',
         '用 === 或 == 进行比较；Python 中 if x = 5 会直接抛出 SyntaxError；'
         'JS 中开启 ESLint no-cond-assign 规则；建议使用 Yoda 条件写法 (5 == x)',
         [r'(?i)if\s*\(\s*\w+\s*=\s*[^=]',
          r'(?i)while\s*\(\s*True\s*\)',
          ]),
]

# ══════════════════════════════════════════════════════════════
#  性能规则 (Performance)
# ══════════════════════════════════════════════════════════════

PERFORMANCE_RULES = [
    Rule('PERF001', 'warning', 'performance',
         'N+1 查询模式',
         '在循环内逐条执行数据库查询，导致 N+1 问题——外层查询 N 条记录，每条记录又触发 1 次子查询，'
         '总共 N+1 次数据库往返，严重拖慢响应速度。',
         '使用 JOIN 或预加载（eager loading）替代循环内查询；'
         'Python ORM: joinedload / selectinload；Django: select_related / prefetch_related；'
         '批量查询: SELECT * FROM t WHERE id IN (...)',
         [r'(?i)for\s+\w+\s+in\s+[^:]+:\s*\n\s*.*\.(query|filter|all|get|execute|find|findOne)',
          r'(?i)\.forEach\s*\([^)]*=>\s*\{[^}]*\.(find|findOne|query|createQueryBuilder)',
          r'(?i)\.map\s*\([^)]*=>\s*\{[^}]*\.(find|findOne|query|createQueryBuilder)',
          ],
         analysis='N+1 问题是 ORM 框架中最常见的性能陷阱。即使单次查询只需 1ms，1000 次就会造成明显的'
                  '响应延迟。ORMs 的 lazy loading 特性往往是 N+1 的根源。'),

    Rule('PERF002', 'warning', 'performance',
         '循环内字符串拼接 (Schlemiel the Painter)',
         '在循环中使用 += 拼接字符串，每次迭代都创建新的字符串对象并复制之前的内容，'
         '总体复杂度 O(n²)，即"Schlemiel the Painter\'s Algorithm"。',
         'Python: parts = []; loop: parts.append(s); result = "".join(parts)；'
         'Java: StringBuilder sb = new StringBuilder(); sb.append(s)；'
         'JS: parts.push(s); result = parts.join("")',
         [r'(?i)for\s+\w+\s+in\s+[^:]+:\s*\n.*\b(\w+)\s*\+=',
          r'(?i)for\s*\([^)]*\)\s*\{[^}]*\b(\w+)\s*\+=',
          ],
         analysis='对于 10 次循环，O(n²) 和 O(n) 的差异可能不明显。但当循环 10000 次时，'
                  '字符串拼接会慢几千倍。使用 join 将复杂度降为 O(n)。'),

    Rule('PERF003', 'suggestion', 'performance',
         '不必要的深拷贝',
         '对大数据结构使用 copy.deepcopy 或 JSON.parse(JSON.stringify()) 做深拷贝，'
         '消耗大量 CPU 和内存。在循环中使用时尤为致命。',
         '评估是否真的需要深拷贝——多数场景下浅拷贝（.copy() / spread / slice）足够；'
         '考虑使用不可变数据结构（immer.js / frozen dict）；传递引用而非拷贝',
         [r'(?i)copy\.deepcopy\s*\(',
          r'(?i)JSON\.parse\s*\(\s*JSON\.stringify\s*\(',
          ]),

    Rule('PERF004', 'warning', 'performance',
         '可能的内存泄漏',
         '未清理的定时器/事件监听器、闭包中保留大对象引用、或无限增长的缓存，'
         '随着运行时间增长，内存占用持续上升直至 OOM。',
         '组件卸载 / 页面销毁时清理：clearInterval / clearTimeout / removeEventListener；'
         '使用 WeakMap / WeakRef 存储可被 GC 的对象引用；缓存设置 maxsize 和 TTL',
         [r'(?i)setInterval\s*\(\s*(?!.*clearInterval)',
          r'(?i)addEventListener\s*\(\s*(?!.*removeEventListener)',
          r'(?i)@\w+\.lru_cache\s*\(\s*maxsize\s*=\s*None\s*\)',
          ],
         analysis='SPA（单页应用）中的内存泄漏尤其隐蔽——用户可能长时间不关闭页面，'
                  '每次路由切换都可能泄漏少量内存，最终导致页面卡顿甚至崩溃。'),

    Rule('PERF005', 'suggestion', 'performance',
         '未使用分页 / 懒加载',
         '一次性查询全部数据（.all() / .toList() / SELECT * 无 LIMIT），'
         '数据量大时导致内存飙升和响应超时。',
         '添加分页：LIMIT + OFFSET 或 cursor-based 分页；'
         '前端用虚拟滚动（Virtual Scroll）渲染大列表；Python 用 yield 生成器流式处理',
         [r'(?m)\.all\s*\(\s*\)\s*$',
          r'(?m)\.toList\s*\(\s*\)',
          r'(?i)SELECT\s+\*\s+FROM\s+\w+\s*$',
          ]),

    Rule('PERF006', 'suggestion', 'performance',
         '异步上下文中的同步阻塞调用',
         '在 async 函数 / 协程中使用同步阻塞的 sleep / HTTP 请求 / 文件 I/O，'
         '阻塞事件循环，导致整个服务的并发能力下降。',
         'Python: await asyncio.sleep() 替代 time.sleep()；aiohttp / httpx 替代 requests；'
         'aiofiles 替代 open()；JS: await fs.promises.readFile 替代 fs.readFileSync；'
         '数据库用 async driver（asyncpg / aiomysql）',
         [r'(?i)async\s+def\s+\w+[^:]*:.*\btime\.sleep\b',
          r'(?i)async\s+def\s+\w+[^:]*:.*\brequests\.(get|post|put|delete)\b',
          r'(?i)async\s+\([^)]*\)\s*=>\s*\{[^}]*\.readFileSync',
          ]),
]

# ══════════════════════════════════════════════════════════════
#  所有规则汇总
# ══════════════════════════════════════════════════════════════

ALL_RULES = SECURITY_RULES + STYLE_RULES + LOGIC_RULES + PERFORMANCE_RULES

# 语言到文件扩展名的映射
LANG_EXT_MAP = {
    'python': ['.py', '.pyx', '.pyi'],
    'javascript': ['.js', '.mjs', '.jsx'],
    'typescript': ['.ts', '.tsx'],
    'vue': ['.vue'],
    'go': ['.go'],
    'java': ['.java', '.kt'],
    'sql': ['.sql'],
    'html': ['.html', '.htm'],
    'css': ['.css', '.scss', '.less'],
    'shell': ['.sh', '.bash', '.zsh'],
    'php': ['.php'],
    'ruby': ['.rb'],
    'rust': ['.rs'],
    'c': ['.c', '.h'],
    'cpp': ['.cpp', '.cc', '.cxx', '.hpp'],
}


# ══════════════════════════════════════════════════════════════
#  代码度量
# ══════════════════════════════════════════════════════════════

class CodeMetrics:
    """代码质量度量."""
    def __init__(self, code, language=''):
        self.code = code
        self.lines = code.split('\n')
        self.total_lines = len(self.lines)
        self.non_empty_lines = len([l for l in self.lines if l.strip()])
        self.empty_lines = self.total_lines - self.non_empty_lines
        self.comment_lines = self._count_comments(language)
        self.code_lines = self.non_empty_lines - self.comment_lines
        self.functions = self._count_functions(language)
        self.classes = self._count_classes(language)
        self.max_indent = self._max_indent()
        self.file_count = 1  # 单次审查的文件数

    def _count_comments(self, lang):
        count = 0
        in_block = False
        for line in self.lines:
            stripped = line.strip()
            if not stripped:
                continue
            if lang in ('python',):
                if stripped.startswith('#'):
                    count += 1
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    in_block = not in_block
                    count += 1
                elif in_block:
                    count += 1
            elif lang in ('javascript', 'typescript', 'vue', 'go', 'java', 'php', 'rust', 'c', 'cpp'):
                if stripped.startswith('//'):
                    count += 1
                if stripped.startswith('/*') or stripped.startswith('/**'):
                    in_block = True
                    count += 1
                elif '*/' in stripped and in_block:
                    in_block = False
                    count += 1
                elif in_block:
                    count += 1
            elif lang in ('sql',):
                if stripped.startswith('--'):
                    count += 1
            elif lang in ('html',):
                if stripped.startswith('<!--'):
                    count += 1
        return count

    def _count_functions(self, lang):
        patterns = {
            'python': r'(?m)^\s*(def |async def )',
            'javascript': r'(?m)(?:function\s+\w+|(?:const|let|var)\s+\w+\s*=\s*(?:async\s*)?\([^)]*\)\s*=>|(?:const|let|var)\s+\w+\s*=\s*(?:async\s*)?function)',
            'typescript': r'(?m)(?:function\s+\w+|(?:const|let|var)\s+\w+\s*=\s*(?:async\s*)?\([^)]*\)\s*=>|(?:const|let|var)\s+\w+\s*=\s*(?:async\s*)?function)',
            'go': r'(?m)^\s*func\s+',
            'java': r'(?m)^\s*(?:public|private|protected|static|\s)+[\w<>\[\]]+\s+(\w+)\s*\([^)]*\)',
            'vue': r'(?m)(?:function\s+\w+|(?:const|let|var)\s+\w+\s*=\s*\([^)]*\)\s*=>|methods\s*:\s*\{)',
        }
        pattern = patterns.get(lang)
        if pattern:
            return len(re.findall(pattern, self.code))
        return 0

    def _count_classes(self, lang):
        patterns = {
            'python': r'(?m)^\s*class\s+\w+',
            'javascript': r'(?m)^\s*class\s+\w+',
            'typescript': r'(?m)^\s*class\s+\w+',
            'java': r'(?m)^\s*(?:public\s+)?class\s+\w+',
            'vue': r'export\s+default\s*\{',
            'go': r'(?m)^\s*type\s+\w+\s+struct',
        }
        pattern = patterns.get(lang)
        if pattern:
            return len(re.findall(pattern, self.code))
        return 0

    def _max_indent(self):
        max_n = 0
        for line in self.lines:
            n = len(line) - len(line.lstrip())
            if n > max_n:
                max_n = n
        return (max_n // 2) if max_n > 0 else 0  # 粗略转换为缩进级别

    def comment_ratio(self):
        if self.non_empty_lines == 0:
            return 0
        return round(self.comment_lines / self.non_empty_lines * 100, 1)

    def avg_function_lines(self):
        if self.functions == 0:
            return 0
        return round(self.code_lines / self.functions, 1)

    def to_dict(self):
        return {
            'total_lines': self.total_lines,
            'code_lines': self.code_lines,
            'comment_lines': self.comment_lines,
            'empty_lines': self.empty_lines,
            'comment_ratio': self.comment_ratio(),
            'functions': self.functions,
            'classes': self.classes,
            'avg_function_lines': self.avg_function_lines(),
            'max_indent_level': self.max_indent,
        }


# ══════════════════════════════════════════════════════════════
#  审查引擎
# ══════════════════════════════════════════════════════════════

class ScriptReviewResult:
    """脚本审查结果."""
    def __init__(self, overall_score=0, summary='', scores=None, issues=None, metrics=None):
        self.overall_score = overall_score
        self.summary = summary
        self.scores = scores or {'security': 0, 'style': 0, 'logic': 0, 'performance': 0}
        self.issues = issues or []
        self.metrics = metrics or {}


class ScriptReviewEngine:
    """基于规则模式的代码审查引擎 — 多维度 + 细粒度分析."""

    # 同类代码块检测的最小行数
    DUP_BLOCK_MIN_LINES = 3
    # 长函数阈值
    LONG_FUNC_THRESHOLD = 200

    # ── 主入口 ──

    def review(self, code, language='', file_paths=None):
        """执行脚本审查.

        Args:
            code: 代码内容
            language: 编程语言提示
            file_paths: 文件路径列表

        Returns:
            ScriptReviewResult
        """
        lines = code.split('\n')
        detected_lang = language.lower() if language else self._detect_language(file_paths, code)
        issues = []

        # 1. 代码度量
        metrics = CodeMetrics(code, detected_lang)

        # 2. 正则规则匹配（含上下文提取）
        rule_patterns = {}  # rule_id -> 匹配的行号集合，用于去重
        for rule in ALL_RULES:
            if not rule.patterns or rule.patterns == [None]:
                continue
            for pattern in rule.patterns:
                for i, line in enumerate(lines, start=1):
                    if re.search(pattern, line):
                        # 在规则内去重
                        rule_key = (rule.id, i)
                        if rule_key in rule_patterns:
                            continue
                        rule_patterns[rule_key] = True
                        # 提取上下文
                        ctx_before, ctx_after = self._extract_context(lines, i)
                        issues.append({
                            'rule_id': rule.id,
                            'severity': rule.severity,
                            'category': rule.category,
                            'title': rule.title,
                            'description': rule.description,
                            'analysis': getattr(rule, 'analysis', ''),
                            'suggestion': rule.suggestion,
                            'line_start': i,
                            'code_snippet': line.strip()[:300],
                            'context_before': ctx_before,
                            'context_after': ctx_after,
                            'fixed_snippet': '',
                            'file_path': file_paths[0] if file_paths else '',
                            'status': 'open',
                        })
                        break

        # 3. 长函数检测 (STY001)
        if detected_lang:
            func_issues = self._check_long_functions(code, detected_lang, lines)
            issues.extend(func_issues)

        # 4. 重复代码检测 (STY002)
        if metrics.code_lines >= self.DUP_BLOCK_MIN_LINES * 3:
            dup_issues = self._check_duplicate_blocks(lines, file_paths)
            issues.extend(dup_issues)

        # 5. 文档注释检测 (STY003)
        doc_issues = self._check_missing_docs(code, detected_lang, lines)
        issues.extend(doc_issues)

        # 6. 条件变量赋值检测 (LOG003)
        cond_var_issues = self._check_conditional_vars(code, detected_lang, lines)
        issues.extend(cond_var_issues)

        # 7. 计算评分
        scores = self._compute_scores(issues, metrics)

        # 8. 综合评分
        overall = round(sum(scores.values()) / 4, 1)

        # 9. 生成摘要
        summary = self._build_summary(issues, overall, detected_lang, metrics)

        return ScriptReviewResult(
            overall_score=overall,
            summary=summary,
            scores=scores,
            issues=issues,
            metrics=metrics.to_dict(),
        )

    # ── 上下文提取 ──

    def _extract_context(self, lines, line_num, radius=2):
        """提取问题行周围的代码上下文."""
        idx = line_num - 1  # 转 0-based
        before, after = [], []

        for i in range(max(0, idx - radius), idx):
            ln = lines[i].strip()
            if ln:
                before.append({'line': i + 1, 'code': ln[:200]})

        for i in range(idx + 1, min(len(lines), idx + radius + 1)):
            ln = lines[i].strip()
            if ln:
                after.append({'line': i + 1, 'code': ln[:200]})

        return before, after

    # ── 语言检测 ──

    def _detect_language(self, file_paths, code):
        """检测编程语言."""
        if file_paths:
            for fpath in file_paths:
                ext = os.path.splitext(fpath)[1].lower()
                for lang, exts in LANG_EXT_MAP.items():
                    if ext in exts:
                        return lang
        # 启发式检测
        if re.search(r'(?m)^\s*(def |class |import |from |async def )', code):
            return 'python'
        if re.search(r'(?m)^\s*(const |let |var |function |import |export |async function)', code):
            return 'javascript'
        if re.search(r'(?m)<template|<script|<style', code):
            return 'vue'
        if re.search(r'(?m)^\s*package \w+', code):
            return 'go'
        if re.search(r'(?m)^\s*public class |private |protected ', code):
            return 'java'
        if re.search(r'(?m)<!DOCTYPE|<html|<div|<span|<meta', code):
            return 'html'
        return 'unknown'

    # ── 长函数检测 ──

    def _check_long_functions(self, code, lang, lines):
        """检测过长函数并生成详细报告."""
        results = []
        func_defs = []

        if lang == 'python':
            pattern = re.compile(r'^(    |\t)?(def |async def )(\w+)', re.MULTILINE)
            for m in pattern.finditer(code):
                func_defs.append((m.start(), m.group(3) or m.group(2)))
        elif lang in ('javascript', 'typescript', 'vue'):
            pattern = re.compile(
                r'(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?(?:\(|function))',
                re.MULTILINE
            )
            for m in pattern.finditer(code):
                func_defs.append((m.start(), m.group(1) or m.group(2) or 'anonymous'))
        elif lang == 'go':
            pattern = re.compile(r'^func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)', re.MULTILINE)
            for m in pattern.finditer(code):
                func_defs.append((m.start(), m.group(1) or 'anonymous'))
        elif lang == 'java':
            pattern = re.compile(
                r'^\s*(?:public|private|protected|static|\s)+[\w<>\[\],\s]+\s+(\w+)\s*\([^)]*\)\s*\{',
                re.MULTILINE
            )
            for m in pattern.finditer(code):
                func_defs.append((m.start(), m.group(1) or 'anonymous'))

        for idx, (start, name) in enumerate(func_defs):
            start_line = code[:start].count('\n') + 1
            next_start = func_defs[idx + 1][0] if idx + 1 < len(func_defs) else len(code)
            end_line = code[:next_start].count('\n') + 1
            span = end_line - start_line
            if span > self.LONG_FUNC_THRESHOLD:
                snippet = lines[min(start_line - 1, len(lines) - 1)].strip()[:200]
                ctx_before, ctx_after = self._extract_context(lines, start_line, radius=1)
                results.append({
                    'rule_id': 'STY001',
                    'severity': 'warning',
                    'category': 'style',
                    'title': '函数 / 方法过长',
                    'description': (f"函数 '{name}' 约 {span} 行，远超推荐上限 {self.LONG_FUNC_THRESHOLD} 行。"
                                    f"过长的函数难以理解、测试和维护，通常意味着该函数承担了过多职责。"),
                    'analysis': (f"按每行约 50 字符的阅读速度计算，阅读该函数需要约 {span // 3} 秒，"
                                 f"而理解其全部逻辑需要数倍于此的时间。建议拆分为 {span // 80 + 1} 个职责单一的小函数。"),
                    'suggestion': ('将该函数按逻辑步骤拆分为多个小函数。例如：数据校验、数据转换、'
                                   '核心计算、结果输出等阶段各提取为独立函数。每个函数聚焦单一职责，'
                                   '这样也便于编写单元测试。'),
                    'line_start': start_line,
                    'code_snippet': snippet,
                    'context_before': ctx_before,
                    'context_after': ctx_after,
                    'fixed_snippet': '',
                    'file_path': '',
                    'status': 'open',
                })
        return results

    # ── 重复代码检测 ──

    def _check_duplicate_blocks(self, lines, file_paths):
        """检测重复代码块（基于行哈希）。"""
        results = []
        # 对每行代码计算哈希（忽略空白和注释）
        hashes = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith('#') or stripped.startswith('//'):
                hashes.append(None)
            else:
                # 规范化：移除多余空格
                normalized = ' '.join(stripped.split())
                h = hashlib.md5(normalized.encode()).hexdigest()[:8]
                hashes.append(h)

        block_size = 3
        seen = {}  # hash_signature -> (start_line, snippet)
        for i in range(len(hashes) - block_size + 1):
            block_hashes = tuple(h for h in hashes[i:i + block_size] if h is not None)
            if len(block_hashes) < block_size:
                continue
            sig = str(block_hashes)
            if sig in seen:
                prev_start = seen[sig][0]
                if i + 1 - prev_start >= block_size:  # 确保不是相邻行
                    snippet = '\n'.join(l.strip() for l in lines[i:i + block_size])
                    results.append({
                        'rule_id': 'STY002',
                        'severity': 'warning',
                        'category': 'style',
                        'title': '检测到重复代码块',
                        'description': (f'第 {prev_start}-{prev_start + block_size} 行与'
                                        f'第 {i + 1}-{i + block_size + 1} 行的代码高度重复。'
                                        f'重复代码增加维护成本，修改时需要同步更新所有副本。'),
                        'analysis': ('代码重复是最常见的代码坏味道之一。研究表明，重复代码中的 Bug '
                                     '在被修复时，约有 30% 的情况下只修复了其中一处，导致其他副本中仍存在相同 Bug。'),
                        'suggestion': '将重复代码提取为独立函数/方法，在原来位置调用该函数。如果代码相似但不完全相同，可以用参数来控制差异部分。',
                        'line_start': i + 1,
                        'code_snippet': snippet[:400],
                        'context_before': self._extract_context(lines, prev_start)[0],
                        'context_after': self._extract_context(lines, i + 1)[1],
                        'fixed_snippet': '',
                        'file_path': file_paths[0] if file_paths else '',
                        'status': 'open',
                    })
                    break  # 每对重复只报一次
            else:
                seen[sig] = (i + 1, lines[i].strip()[:100])
        return results

    # ── 文档注释检测 ──

    def _check_missing_docs(self, code, lang, lines):
        """检测缺少文档注释的公开函数/类."""
        results = []
        if lang == 'python':
            # 检测缺少 docstring 的公开函数/类
            for i, line in enumerate(lines, start=1):
                stripped = line.strip()
                if re.match(r'^def\s+(?!_\w)[a-zA-Z]\w*\s*\(', stripped) or \
                   re.match(r'^class\s+(?!_\w)[a-zA-Z]\w*\s*[(:]', stripped):
                    # 检查下一行是否有 docstring
                    if i < len(lines):
                        next_line = lines[i].strip() if i < len(lines) else ''
                        if not (next_line.startswith('"""') or next_line.startswith("'''") or
                                next_line.startswith('#') or next_line.startswith('#')):
                            name = re.match(r'(?:def|class)\s+(\w+)', stripped).group(1)
                            results.append({
                                'rule_id': 'STY003',
                                'severity': 'suggestion',
                                'category': 'style',
                                'title': '缺少文档注释',
                                'description': f"公开函数/类 '{name}' 缺少文档字符串（docstring），调用方无法快速了解其用途和参数。",
                                'analysis': '有文档注释的 API 被误用的概率显著低于无文档的 API。团队成员和 AI 编程助手都依赖文档注释来正确使用接口。',
                                'suggestion': f"为 '{name}' 添加 docstring，至少包含简要描述、参数说明（:param）和返回值（:return）。",
                                'line_start': i,
                                'code_snippet': stripped[:200],
                                'context_before': [],
                                'context_after': [],
                                'fixed_snippet': '',
                                'file_path': '',
                                'status': 'open',
                            })
        elif lang in ('javascript', 'typescript'):
            # 检测缺少 JSDoc 的导出函数
            for i, line in enumerate(lines, start=1):
                stripped = line.strip()
                if re.match(r'export\s+(?:async\s+)?function\s+\w+', stripped) or \
                   re.match(r'export\s+(?:const|let)\s+\w+\s*=\s*(?:async\s*)?\(', stripped):
                    # 检查前一行是否有 JSDoc
                    if i > 1:
                        prev = lines[i - 2].strip()
                        if not prev.startswith('/**') and not prev.startswith('*'):
                            name_match = re.search(r'(?:function\s+|(?:const|let)\s+)(\w+)', stripped)
                            name = name_match.group(1) if name_match else 'anonymous'
                            results.append({
                                'rule_id': 'STY003',
                                'severity': 'suggestion',
                                'category': 'style',
                                'title': '缺少 JSDoc 文档注释',
                                'description': f"导出的函数 '{name}' 缺少 JSDoc 注释，IDE 无法提供智能参数提示。",
                                'analysis': 'JSDoc 不仅是文档，也是 TypeScript 类型推断和 IDE IntelliSense 的数据来源。',
                                'suggestion': f"为 '{name}' 添加 JSDoc：@param {Type} name - description，@returns {Type} description",
                                'line_start': i,
                                'code_snippet': stripped[:200],
                                'context_before': [],
                                'context_after': [],
                                'fixed_snippet': '',
                                'file_path': '',
                                'status': 'open',
                            })

        # 限制报告数
        return results[:10]

    # ── 条件变量赋值检测 ──

    def _check_conditional_vars(self, code, lang, lines):
        """检测条件分支中可能未定义的变量."""
        results = []
        if lang not in ('python',):
            return results

        # 检测 if/else 中赋值但在分支外使用的变量
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            # 检测 if xxx: var = something
            if_assign = re.match(r'^\s*if\s+.+:\s*$', stripped)
            if if_assign:
                # 找该 if 块中的赋值
                var_assigns = []
                j = i + 1
                while j < len(lines) and (lines[j - 1].startswith('    ') or
                                           lines[j - 1].startswith('\t') or
                                           not lines[j - 1].strip()):
                    m = re.match(r'^\s+(\w+)\s*=', lines[j - 1])
                    if m:
                        var_assigns.append(m.group(1))
                    j += 1

                # 检查这些变量在 if 后面是否被使用（且不在 else 中赋值）
                if var_assigns and 'else' not in ''.join(lines[i:j]):
                    for var in var_assigns[:3]:  # 限制每个 if 最多报 3 个
                        used_after = any(
                            re.search(r'\b' + re.escape(var) + r'\b', l)
                            for l in lines[j:min(j + 10, len(lines))]
                        )
                        if used_after:
                            results.append({
                                'rule_id': 'LOG003',
                                'severity': 'warning',
                                'category': 'logic',
                                'title': '变量条件赋值 — 可能未定义',
                                'description': (f"变量 '{var}' 在 if 块（第 {i} 行）中有条件地赋值，"
                                                f"但 if 块之后（约第 {j} 行）使用了该变量。"
                                                f"如果条件不满足，变量将未定义导致运行时错误。"),
                                'analysis': '条件分支中的变量赋值是隐式的状态管理，容易在异常路径下暴露出未定义错误。建议在分支前设置默认值，或在所有分支中都定义该变量。',
                                'suggestion': f"在 if 判断前为 '{var}' 设置默认值（如 var = None），或添加 else 分支。",
                                'line_start': i,
                                'code_snippet': stripped[:200],
                                'context_before': self._extract_context(lines, i)[0],
                                'context_after': self._extract_context(lines, j)[1],
                                'fixed_snippet': '',
                                'file_path': '',
                                'status': 'open',
                            })
        return results[:10]

    # ── 评分计算 ──

    def _compute_scores(self, issues, metrics):
        """综合计算各维度评分 (0-10)。"""
        dims = {'security': 0, 'style': 0, 'logic': 0, 'performance': 0}
        counts = {'security': 0, 'style': 0, 'logic': 0, 'performance': 0}

        severity_penalty = {'critical': -2.5, 'warning': -0.8, 'suggestion': -0.3}

        for issue in issues:
            cat = issue.get('category', 'style')
            if cat in dims:
                counts[cat] += 1
                dims[cat] += severity_penalty.get(issue.get('severity', 'warning'), -0.5)

        # 从 10 分起扣，基础分受代码度量影响
        base_scores = {}
        for cat in dims:
            # 有注释的代码风格稍好
            if cat == 'style' and metrics.comment_ratio() > 10:
                base_scores[cat] = 10.5
            elif cat == 'style' and metrics.comment_ratio() < 3 and metrics.code_lines > 50:
                base_scores[cat] = 9
            else:
                base_scores[cat] = 10

        result = {}
        for cat in dims:
            result[cat] = round(max(0, min(10, base_scores[cat] + dims[cat])), 1)

        return result

    # ── 摘要生成 ──

    def _build_summary(self, issues, overall_score, language, metrics):
        """生成详细的审查摘要报告."""
        parts = []

        # 标题行
        if overall_score >= 8.5:
            grade = '优秀'
            emoji = ''
        elif overall_score >= 7:
            grade = '良好'
            emoji = ''
        elif overall_score >= 5:
            grade = '一般'
            emoji = ''
        elif overall_score >= 3:
            grade = '较差'
            emoji = ''
        else:
            grade = '差'
            emoji = ''

        parts.append(f'代码审查完成（{language or "自动检测语言"}），综合评分 **{overall_score}/10**（{grade}）\n')

        # 代码度量概览
        parts.append('## 代码度量')
        metric_items = [
            f"总行数 {metrics.total_lines}（有效代码 {metrics.code_lines} 行，注释 {metrics.comment_lines} 行，空行 {metrics.empty_lines} 行）",
            f"注释率 {metrics.comment_ratio()}%",
            f"共 {metrics.functions} 个函数/方法，{metrics.classes} 个类/结构体",
        ]
        if metrics.functions > 0:
            metric_items.append(f"平均函数长度 {metrics.avg_function_lines()} 行")
        if metrics.max_indent > 0:
            metric_items.append(f"最大嵌套深度约 {metrics.max_indent} 层")
        parts.append('\n'.join(f'- {x}' for x in metric_items) + '\n')

        # 问题统计
        if not issues:
            parts.append('**未发现明显问题，代码质量良好。**')
            return '\n'.join(parts)

        sev_counts = Counter()
        cat_issues = Counter()
        cat_severity = {}  # category -> {critical, warning, suggestion}
        for i in issues:
            sev = i.get('severity', 'warning')
            cat = i.get('category', 'style')
            sev_counts[sev] += 1
            cat_issues[cat] += 1
            if cat not in cat_severity:
                cat_severity[cat] = Counter()
            cat_severity[cat][sev] += 1

        parts.append('## 问题汇总')
        parts.append(f'共发现 **{len(issues)}** 个问题：')
        sev_parts = []
        if sev_counts.get('critical'):
            sev_parts.append(f'**严重 {sev_counts["critical"]} 个**')
        if sev_counts.get('warning'):
            sev_parts.append(f'警告 {sev_counts["warning"]} 个')
        if sev_counts.get('suggestion'):
            sev_parts.append(f'建议 {sev_counts["suggestion"]} 个')
        parts.append('，'.join(sev_parts) + '\n')

        # 各维度分析
        parts.append('## 各维度分析')
        dim_order = ['security', 'logic', 'style', 'performance']
        dim_labels = {
            'security': '安全', 'style': '规范', 'logic': '逻辑', 'performance': '性能'
        }
        for cat in dim_order:
            count = cat_issues.get(cat, 0)
            if count == 0:
                parts.append(f'- **{dim_labels[cat]}**：未发现问题 ✓')
            else:
                detail_parts = []
                cs = cat_severity.get(cat, Counter())
                if cs.get('critical'):
                    detail_parts.append(f'严重 {cs["critical"]}')
                if cs.get('warning'):
                    detail_parts.append(f'警告 {cs["warning"]}')
                if cs.get('suggestion'):
                    detail_parts.append(f'建议 {cs["suggestion"]}')
                parts.append(f'- **{dim_labels[cat]}**：{count} 个问题（{", ".join(detail_parts)}）')

        # 优先修复建议
        critical_issues = [i for i in issues if i.get('severity') == 'critical']
        if critical_issues:
            parts.append('\n## 优先修复建议')
            parts.append(f'以下 **{len(critical_issues)}** 个严重问题应优先修复：')
            for ci in critical_issues[:5]:
                parts.append(f'- [{ci["rule_id"]}] 第{ci["line_start"]}行 — {ci["title"]}')
            if len(critical_issues) > 5:
                parts.append(f'- ...及其他 {len(critical_issues) - 5} 个严重问题')

        # 健康度评价
        parts.append(f'\n## 代码质量评价')
        if overall_score >= 8:
            parts.append('代码整体质量较高，按建议优化后可达到生产标准。')
        elif overall_score >= 6:
            parts.append('代码存在一定问题，建议优先修复安全问题，再逐步改进规范、逻辑和性能方面的问题。')
        else:
            parts.append('代码存在较多问题，强烈建议在合并前修复所有严重（critical）问题，并对警告（warning）级别问题进行评估。')

        return '\n'.join(parts)


# ══════════════════════════════════════════════════════════════
#  单例
# ══════════════════════════════════════════════════════════════

script_review_engine = ScriptReviewEngine()
