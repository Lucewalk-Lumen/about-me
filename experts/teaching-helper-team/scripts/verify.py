# -*- coding: utf-8 -*-
"""运行前校验：结构 / 引用可解析 / 版本一致 / 依赖锁定 / 命名规范 / import 可解析。

直接扫描文件系统与 plugin.json，不依赖任何额外清单，因此不存在清单与实际的漂移。

用法：python3 scripts/verify.py
退出码：0 = 通过；1 = 存在 FAIL（阻断加载）。

自检可信度约定（勿改回）：
  结论行必须同时给出**受检项（分母）**。只有 FAIL 计数而没有分母时，`0 FAIL`
  无法区分「断言都跑过且都通过」与「断言根本没执行」——后者是空转式的假通过。
  故所有断言一律经 check() 登记，末尾逐节打印受检项数；声明的校验节若整节未出现，
  直接判 FAIL（自检覆盖缺失）。新增断言请走 check()/section()，勿直接 append 到 FAIL。
"""
import ast
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FAIL, WARN = [], []
NOTES = []            # 供报告展示的客观口径（不参与判定）
CHECKS = 0            # 受检项累计：每执行一条断言 +1
SECTIONS = []         # [(节标题, 该节受检项数)]
_cur = [None, 0]      # [当前节标题, 当前节计数]

# 在册校验节清单。**必须独立于 section() 调用**：若由 section(must_run=True) 反向填充，
# 则「在册集合」与「实跑集合」同源，两者永远一致，守护恒定成立即等于没有守护（空转）。
# 因此这里是字面量，新增/改名校验节时必须同步登记，否则末尾直接判 FAIL。
EXPECTED_SECTIONS = (
    '1 必需结构', '2 禁止目录与文件', '3 包根白名单',
    '3b .codebuddy-plugin/ 内部白名单', '3c 声明目录一级白名单',
    '4 plugin.json 引用与官方清单', '5 单一运行入口', '6 版本一致',
    '7 Markdown 链接可解析', '8 依赖精确锁定',
    '8b 依赖口径一致（lock 覆盖 setup.py 的 PY_DEPS）',
    '9 命名规范', '10 内联路径引用可解析', '10b 纯文件名引用可解析',
    '11 Python import 可解析', '12 agent 定义字段',
    '13 代码命令行位置不得含中文', '14 命令行位脚本引用存在性',
    '15 profession / displayName 完整性',
    '16 对齐官方 validate_expert.py 硬规则', '17 推荐提示词协同度',
    '18 主理人花名在包内文档可见',
    '19 成员四方互校（members/agents/avatars/teamInfo）',
    '20 成员回传契约覆盖',
    '21 协同依赖一致性（依赖表与成员声明）',
    '22 主理人回传聚合契约',
    '23 降级矩阵完整性（前端链路不可用时的边界）',
    '24 口径回归守护（耗时口径）',
    '25 初始化中断可恢复（写状态顺序 + venv 功能校验）',
)


def section(title):
    """进入一个新校验节：结算上一节计数，开始计当前节。"""
    _flush()
    _cur[0], _cur[1] = title, 0


def _flush():
    if _cur[0] is not None:
        SECTIONS.append((_cur[0], _cur[1]))


def fail(m):
    FAIL.append(m)


def warn(m):
    WARN.append(m)


def check(cond, msg, warn_only=False):
    """唯一断言入口：登记受检项 → 判定 → 记 FAIL/WARN。返回判定结果。"""
    global CHECKS
    CHECKS += 1
    _cur[1] += 1
    if not cond:
        (warn if warn_only else fail)(msg)
    return bool(cond)


def rd(p):
    try:
        return p.read_text(encoding='utf-8')
    except Exception:
        return ''


REQUIRED_FILES = ['.codebuddy-plugin/plugin.json', 'settings.json', 'requirements.lock',
                  'README.md', 'CHANGELOG.md', 'STRUCTURE.md', 'LICENSE',
                  'scripts/verify.py']
REQUIRED_DIRS = ['agents', 'avatars', 'skills', 'scripts']
FORBIDDEN_DIRS = {'__pycache__', '__MACOSX', 'build', 'dist', 'node_modules', '.git', 'tests'}
FORBIDDEN_SUFFIX = {'.pyc', '.log', '.tmp', '.bak', '.orig', '.swp'}
FORBIDDEN_NAMES = {'.DS_Store', '.env', 'Thumbs.db', '.env.example', 'pyproject.toml'}
EXEMPT = {'README.md', 'CHANGELOG.md', 'STRUCTURE.md', 'UPGRADE.md', 'ROLLBACK.md',
          'LICENSE', 'LICENSE.md', 'SKILL.md', 'settings.json', 'plugin.json',
          'requirements.lock', 'matplotlibrc', 'config.json', 'package.json'}
# 第三方库与既定命名目录：不做 ASCII 小写约束（改写会破坏第三方库与既定数据命名）
SKIP_NAMING = ('/assets', 'skills/_shared', '/references', '/templates', '/knowledge')
# 运行时产物与用户工作区目录（非包内随附文件），解析时豁免
RUNTIME_ART = ('trace.json', 'result.json', 'data/pipeline', '.fbs/', 'qc-output/',
               'data/material-extractor/', 'OUTPUT/', 'output/')

# 1. 必需结构
section('1 必需结构')
for f in REQUIRED_FILES:
    check((ROOT / f).is_file(), f'缺少必需文件: {f}')
for d in REQUIRED_DIRS:
    check((ROOT / d).is_dir(), f'缺少必需目录: {d}')

# 2. 禁止项
section('2 禁止目录与文件')
for p in ROOT.rglob('*'):
    rel = p.relative_to(ROOT)
    if p.is_dir():
        check(p.name not in FORBIDDEN_DIRS, f'禁止目录: {rel}')
    if p.is_file():
        check(not (p.suffix in FORBIDDEN_SUFFIX or p.name in FORBIDDEN_NAMES),
              f'禁止文件: {rel}')

# 3. 包根白名单
#    设计原则（勿改回）：自研门禁的「保留 / 丢弃」谓词必须**逐字复刻官方打包器**，不得自造更严的
#    白名单——`_` 前缀要拦（官方不过滤、会被打包进 zip），`.` 前缀要放（官方会丢弃）。
#    官方打包器 package_expert.py 只过滤隐藏文件（`.` 开头）与 __pycache__，
#    **不过滤 `_` 前缀等非隐藏条目** → 任何未声明的包根条目都会被原样打进分发 zip。
#    （示例：包根若留下 `_` 前缀临时文件，会被原样打包、使分发件条目数凭空增加。）
#    官方校验器与既有各节都不检查「包根白名单」，此节是唯一能拦住这类污染的门禁。
section('3 包根白名单')
ALLOWED_ROOT_DIRS = {'.codebuddy-plugin', 'agents', 'avatars', 'references', 'scripts', 'skills'}
ALLOWED_ROOT_FILES = {'CHANGELOG.md', 'LICENSE', 'README.md', 'STRUCTURE.md',
                      'requirements.lock', 'settings.json', 'UPGRADE.md', 'ROLLBACK.md'}
for _p in sorted(ROOT.iterdir()):
    # 与官方打包器 package_expert.py 第 74 行谓词逐字对齐：
    #     if any(p.startswith('.') and p != '.codebuddy-plugin' for p in parts): continue
    # 即：所有 `.` 前缀条目（除 `.codebuddy-plugin` 外）官方一律丢弃、**永不进 zip**，此处放行；
    # 而 `_` 前缀等非隐藏条目官方**不过滤**、会被打包，仍由下方白名单拦截。
    # 依据：`.created-by-session`（36 B）是 WorkBuddy 主机在包被装载到
    # `<cfg>/plugins/marketplaces/my-experts/plugins/<pkg>/` 时落下的会话标记，作者不可控，
    # 且官方校验器要求包位于该路径下 → 若不放行 `.` 前缀，门禁会在唯一有意义的运行环境里恒红
    # （假阳性），使门禁失去意义。注意 `.codebuddy-plugin` 必须**不**被跳过：它要继续参与白名单校验。
    if _p.name.startswith('.') and _p.name != '.codebuddy-plugin':
        continue
    if _p.is_dir():
        check(_p.name in ALLOWED_ROOT_DIRS,
              f'包根出现未声明的目录: {_p.name}/ —— 会被官方打包器打进分发件')
    else:
        check(_p.name in ALLOWED_ROOT_FILES,
              f'包根出现未声明的文件: {_p.name} —— 会被官方打包器打进分发件')

# 3b. 声明目录内部白名单：.codebuddy-plugin/
#     设计依据：§3 的谓词承担「与官方打包器逐字对齐」的契约，职责单一，不应被白名单逻辑污染。
#     「允许清单」用来声明「应该存在什么」（`_` 前缀要拦、非隐藏项要声明）；
#     「官方丢弃谓词」用来决定「什么会被打包」（`.` 前缀一律丢）。
#     两者职责不同、不可互相替代——包根需要「前者 + 后者」，声明目录内部同样需要「前者 + 后者」。
#     故本节同样跳过 `.` 前缀项：官方打包器也会丢弃它们，不构成污染。
#     而 `.codebuddy-plugin/` 内的**非隐藏**杂项既不被 §3 拦（§3 只守包根一层）、
#     又会被官方打包器原样打进分发件，故必须由本节拦。
#     注：plugin.json 的存在性与「文件类型」由 §1 / §4 保证，本节只负责「无未声明的非隐藏条目」。
section('3b .codebuddy-plugin/ 内部白名单')
PLUGIN_DIR = ROOT / '.codebuddy-plugin'
ALLOWED_PLUGIN_ENTRIES = {'plugin.json'}
if PLUGIN_DIR.is_dir():
    for _p in sorted(PLUGIN_DIR.iterdir()):
        if _p.name.startswith('.'):        # 官方打包器同样丢弃 `.` 前缀，不构成污染
            continue
        check(_p.name in ALLOWED_PLUGIN_ENTRIES,
              f'.codebuddy-plugin/ 出现未声明的条目: {_p.name} —— 会被官方打包器打进分发件')

# 3c. 声明目录一级白名单（agents/ avatars/ scripts/ skills/）
#     设计依据（与 §3b 同理）：声明目录内部同样需要「允许清单 + 官方丢弃谓词」——
#     `_` 前缀/普通杂项要拦（官方不过滤、会被打包），`.` 前缀要放（官方会丢弃）。
#     白名单从 plugin.json **推导**（不硬编码），避免清单与实际漂移：
#       agents/  ← plugin.json.agents[]                （取 basename）
#       avatars/ ← plugin.json.avatar + members[].avatar（取 basename）
#       scripts/ ← 固定 {'verify.py'}
#       skills/  ← plugin.json.skills[]（取 basename）+ '_shared'
#                 （_shared 是共享契约目录，不在 skills[] 内，故显式补充）
#     跳过 `.` 前缀项（与官方谓词一致，防同类假阳性复发）。
#     若 plugin.json 缺失/解析失败 → 本节受检项为 0，由 §1/§4 承担对应 FAIL，避免级联重复报错。
#     已知覆盖边界：§3c 只守到「声明目录的一级条目」；更深层级（如 skills/<skill>/scripts/）
#     结构自由，不设白名单（与 §3b 同理，本门禁只覆盖一级）。
section('3c 声明目录一级白名单')
_pjf = ROOT / '.codebuddy-plugin' / 'plugin.json'
_pj = {}
if _pjf.is_file():
    try:
        _pj = json.loads(_pjf.read_text(encoding='utf-8'))
    except Exception:
        _pj = {}
if _pj:
    _expect = {
        'agents': {pathlib.Path(a).name for a in (_pj.get('agents') or [])},
        'avatars': {pathlib.Path(_pj['avatar']).name} if _pj.get('avatar') else set(),
        'scripts': {'verify.py'},
        'skills': {pathlib.Path(s).name for s in (_pj.get('skills') or [])} | {'_shared'},
    }
    for _m in (_pj.get('members') or []):
        if _m.get('avatar'):
            _expect['avatars'].add(pathlib.Path(_m['avatar']).name)
    for _d, _names in _expect.items():
        _dp = ROOT / _d
        if not _dp.is_dir():
            continue
        for _p in sorted(_dp.iterdir()):
            if _p.name.startswith('.'):        # 官方打包器同样丢弃 `.` 前缀，不构成污染
                continue
            check(_p.name in _names,
                  f'{_d}/ 出现未声明的条目: {_p.name} —— 会被官方打包器打进分发件')

# 4. plugin.json 引用必须可解析 + 官方清单合规
section('4 plugin.json 引用与官方清单')
pj = {}
pjf = ROOT / '.codebuddy-plugin/plugin.json'
if pjf.is_file():
    try:
        pj = json.loads(pjf.read_text(encoding='utf-8'))
    except Exception as e:
        pj = {}
        check(False, f'plugin.json 不是合法 JSON：{e}')
    for a in pj.get('agents', []) or []:
        check((ROOT / a.lstrip('./')).is_file(), f'plugin.json 引用的 agent 不存在: {a}')
    for s in pj.get('skills', []) or []:
        sp = ROOT / s.lstrip('./')
        if check(sp.is_dir(), f'plugin.json 引用的技能目录不存在: {s}'):
            check((sp / 'SKILL.md').is_file(), f'技能缺少 SKILL.md: {s}')
    if pj.get('avatar'):
        check((ROOT / pj['avatar']).is_file(), '团队头像不存在')
    for m in pj.get('members', []) or []:
        check((ROOT / m['avatar']).is_file(), f"成员头像不存在: {m['avatar']}")
        check((ROOT / 'agents' / f"{m['id']}.md").is_file(), f"成员 agent 文件不存在: {m['id']}")
    ti = pj.get('teamInfo', {}) or {}
    for aid in [ti.get('leadAgent')] + list(ti.get('memberAgents', []) or []):
        if aid:
            check((ROOT / 'agents' / f'{aid}.md').is_file(), f'teamInfo 引用的 agent 不存在: {aid}')
    # 官方《专家团开发标准》
    for k in ('tools', 'allowed-tools', 'capabilities'):   # 注：dependencies 为官方标准允许字段，不在此列
        check(k not in pj, f'plugin.json 不得自行声明 {k}')
    # 官方《专家团开发标准》未对 displayName / profession 设定字符数上限
    # （官方模板中 profession 取值区间约为 17-40 字符）。
    # 长度约束仅保留给成员昵称（members[].name），避免卡片昵称过长。
    NAME_LIMIT = 15
    for m in pj.get('members', []) or []:
        for k, v in (m.get('name', {}) or {}).items():
            if isinstance(v, str):
                check(len(v) <= NAME_LIMIT,
                      f'卡面字段 {m.get("id")}.name.{k} = {len(v)} 字符，超过 {NAME_LIMIT}')
    dd = pj.get('displayDescription', {}).get('zh', '')
    check(40 <= len(dd) <= 50, f'displayDescription.zh = {len(dd)} 字，不在 40-50 区间')
    check(pj.get('defaultInitPrompt') == (pj.get('quickPrompts') or [None])[0],
          'defaultInitPrompt 必须等于 quickPrompts[0]')

# 5. 单一运行入口
section('5 单一运行入口')
stf = ROOT / 'settings.json'
ENTRY_AGENT = ''
if stf.is_file():
    st = json.loads(stf.read_text(encoding='utf-8'))
    if check(list(st.keys()) == ['agent'], 'settings.json 必须为单键 {"agent": ...}'):
        ENTRY_AGENT = st['agent']
        check((ROOT / 'agents' / f"{ENTRY_AGENT}.md").is_file(), '入口 agent 文件不存在')
        if pj.get('agentName'):
            check(pj['agentName'] == ENTRY_AGENT,
                  'settings.json 的 agent 与 plugin.json 的 agentName 不一致')

# 6. 版本一致
section('6 版本一致')
if pj:
    ver = pj.get('version')
    cl = ROOT / 'CHANGELOG.md'
    if cl.is_file():
        _cl = cl.read_text(encoding='utf-8')
        # 接受官方格式「X.Y.Z 版本发布 🚀(YYYY-MM-DD)」或传统「[X.Y.Z]」两种条目写法
        _ok = (f'[{ver}]' in _cl) or bool(re.search(rf'##\s*{re.escape(ver)}\s*版本发布', _cl))
        check(_ok, f'CHANGELOG 缺少版本条目 {ver}')
    for f in sorted((ROOT / 'skills').glob('*/SKILL.md')):
        t = f.read_text(encoding='utf-8')
        m = re.search(r'^version:\s*(\S+)', t, re.M)
        rel = f.relative_to(ROOT)
        if not m:
            check(False, f'{rel} 缺少 version')
        else:
            check(m.group(1) == ver, f'{rel} 版本 {m.group(1)} != 包版本 {ver}')
        check(re.search(r'^description:', t, re.M) is not None,
              f'{rel} 缺少 description', warn_only=True)

# 7. Markdown 链接可解析
section('7 Markdown 链接可解析')
LINK = re.compile(r'\[([^\]]*)\]\((?!https?:|mailto:|#)([^)]+)\)')
CODE_SPAN = re.compile(r'`[^`]*`')
_link_n = 0
for base in ('skills', 'agents'):
    for f in (ROOT / base).rglob('*.md'):
        # 行内代码里的 [alt](src) 是 Markdown 语法示例，不是真链接
        for m in LINK.finditer(CODE_SPAN.sub(' ', rd(f))):
            tgt = m.group(2).split('#')[0].strip()
            if not tgt:
                continue
            if tgt.startswith('[') and tgt.endswith(']'):   # 模板占位（如 [年份]），非真链接
                continue
            _link_n += 1
            check((f.parent / tgt).exists(), f'{f.relative_to(ROOT)} 链接失效: {tgt}')
NOTES.append(f'§7 参与判定的相对链接 {_link_n} 条')

# 8. 依赖精确锁定
section('8 依赖精确锁定')
lf = ROOT / 'requirements.lock'
if lf.is_file():
    for line in lf.read_text(encoding='utf-8').splitlines():
        s = line.strip()
        if s and not s.startswith('#'):
            check('==' in s, f'requirements.lock 未精确锁定: {s}')


# 8b. 依赖口径一致
#     requirements.lock 声明「精确锁定」，而 setup.py 实际按分组区间安装（>=x,<y），
#     两处清单各自维护极易漂移：lock 少列一个包，该包就永不进入锁文件、安装却照旧发生。
#     本节做**单向覆盖**校验：PY_DEPS 中出现的每个包，都必须在 lock 中有锁定行。
#     （反向不校验：lock 中允许存在 setup 默认不安装的可选包，如图表库。）
#     解析方式：PY_DEPS 是静态字典字面量，用 ast 求值而非正则，避免注释/换行/引号干扰。
section('8b 依赖口径一致（lock 覆盖 setup.py 的 PY_DEPS）')


def _norm_pkg(name):
    """PEP 503 归一化：包名比较统一为小写 + 连字符。"""
    return re.sub(r'[-_.]+', '-', (name or '').strip().lower())


def _req_name(spec):
    m = re.match(r'\s*([A-Za-z0-9][A-Za-z0-9._-]*)', spec or '')
    return _norm_pkg(m.group(1)) if m else ''


_lock_pkgs, _setup_pkgs = set(), set()
if lf.is_file():
    for _line in lf.read_text(encoding='utf-8').splitlines():
        _s = _line.strip()
        if _s and not _s.startswith('#'):
            _n = _req_name(_s)
            if _n:
                _lock_pkgs.add(_n)
_su = ROOT / 'skills/setup/scripts/setup.py'
if _su.is_file():
    try:
        _tree = ast.parse(_su.read_text(encoding='utf-8'))
        _py_deps = None
        for _node in _tree.body:
            _tgt = getattr(_node, 'target', None)
            if isinstance(_tgt, ast.Name) and _tgt.id == 'PY_DEPS':
                try:
                    _py_deps = ast.literal_eval(_node.value)
                except Exception:
                    _py_deps = None
        if not isinstance(_py_deps, dict):
            check(False, 'setup.py 的 PY_DEPS 不是可静态求值的字典字面量，依赖口径无法机器校验')
        else:
            for _grp, _specs in _py_deps.items():
                for _sp in (_specs or []):
                    _n = _req_name(_sp)
                    if _n:
                        _setup_pkgs.add(_n)
            check(len(_py_deps) > 0, 'setup.py 的 PY_DEPS 为空字典，依赖口径校验失去意义')
    except SyntaxError as _e:
        check(False, f'setup.py 语法错误，无法解析 PY_DEPS：{_e}')
check(bool(_lock_pkgs), 'requirements.lock 未解析出任何锁定包，依赖口径校验失去意义')
check(bool(_setup_pkgs), 'setup.py 的 PY_DEPS 未解析出任何包，依赖口径校验失去意义')
for _n in sorted(_setup_pkgs):
    check(_n in _lock_pkgs, f'setup.py PY_DEPS 中的包未在 requirements.lock 锁定: {_n}')
NOTES.append(f'§8b 依赖口径：lock {len(_lock_pkgs)} 个包；PY_DEPS {len(_setup_pkgs)} 个包；'
             f'覆盖缺口 {len(_setup_pkgs - _lock_pkgs)} 个')

# 9. 命名规范（第三方库与既定命名目录豁免）
section('9 命名规范')
for p in ROOT.rglob('*'):
    # 统一为正斜杠：SKIP_NAMING 常量以 '/' 书写，而 str(Path) 在 Windows 上产出反斜杠，
    # 否则豁免失效，会对 skills/_shared/DATA-CONTRACT.md 等误报「文件名含大写」。
    rel = p.relative_to(ROOT).as_posix()
    if p.name.startswith('.') or p.name in EXEMPT:
        continue
    if any(k in rel for k in SKIP_NAMING):
        continue
    bad = None
    if re.search(r'[一-鿿]', p.name):
        bad = f'文件名含中文: {rel}'
    elif re.search(r'\s', p.name):
        bad = f'文件名含空格: {rel}'
    elif re.search(r'[A-Z]', p.name):
        bad = f'文件名含大写: {rel}'
    check(bad is None, bad or '')

# 10. 内联路径引用可解析
section('10 内联路径引用可解析')
INLINE = re.compile(r'`((?:\.{1,2}/)?[\w一-鿿.-]+/(?:[\w一-鿿.-]+/)*[\w一-鿿.-]+\.(?:md|json|py|yaml|yml|lock|db|png|jpg|html|js|mjs|ps1|css|cjs|ts|svg|sh))')
SKIP_INLINE = ('http', 'https', 'mailto', '${')
_SKILL_DIRS = [d for d in (ROOT / 'skills').iterdir() if d.is_dir()]


def _resolvable(f, tgt):
    if any(s in tgt for s in RUNTIME_ART):
        return True
    if any(s in tgt for s in ('XX', 'xx', '<', '{', '}', '图N')):
        return True
    for b in [f.parent, f.parent.parent, f.parent.parent.parent, ROOT] + _SKILL_DIRS:
        if (b / tgt).exists():
            return True
    name = pathlib.Path(tgt).name
    if name and not any(s in name for s in ('XX', '<', '{')):
        if any(True for _ in ROOT.rglob(name)):
            return True
    return False


for base in ('skills', 'agents'):
    for f in (ROOT / base).rglob('*.md'):
        for line in rd(f).split('\n'):
            for m in INLINE.finditer(line):
                tgt = m.group(1)
                if any(s in tgt for s in SKIP_INLINE):
                    continue
                check(_resolvable(f, tgt),
                      f'{f.relative_to(ROOT)} 内联路径失效: {tgt}')
for nm in ('README.md', 'CHANGELOG.md', 'STRUCTURE.md'):
    f = ROOT / nm
    if not f.is_file():
        continue
    for line in rd(f).split('\n'):
        for m in INLINE.finditer(line):
            tgt = m.group(1)
            if any(s in tgt for s in SKIP_INLINE):
                continue
            check(_resolvable(f, tgt), f'{nm} 内联路径失效: {tgt}')

# 10b. 纯文件名引用可解析（无路径分隔符，如 `SOURCES.md` / `requirements.lock`）
#     §10 的正则要求路径含 `/`，会漏检这类简写引用；此处补齐。
section('10b 纯文件名引用可解析')
PLAIN_REF = re.compile(r'(?<!\[)`([A-Za-z0-9_][A-Za-z0-9_.-]*\.(?:md|txt|toml|lock|yaml|yml|json|mjs|ps1|css|cjs|ts|svg|sh))`')
# 运行时产物 / 用户工作区命名 / 条件性文件：不要求随包存在
PLAIN_ALLOW = {
    'IDENTITY.md', 'WIKI-SCHEMA.md', 'YYYY-MM-DD_topic.md',
    'full_text.txt', 'ocr_all.txt', 'textbook.md',
    'index.md', 'glossary.md', 'story-bank.md', 'commitments.md',
    'concept-dependencies.md', 'framework.md', 'framework.mermaid.md',
    'proposal_draft.md', 'quality_report.md', 'expansion_report.md', 'expansion-plan.md',
    't01_summary_content-summary.md', 't01_draft_thesis-mentor.md', 't01_scrape_crawler.json',
    # 运行时产物（流程生成，落用户工作区）
    'metadata.json', 'result.json', 'trace.json', 'input.json', 'summary.json',
    'deck.json', 'deck-spec.json', 'deck.spec.json', 'distilled_metadata.json',
    'extracted-slides.json', 'dependencies.json', 'explanations.json',
    'provenance-audit.json', 'chapter-scan-result.json', 'injections.json',
    'project-config.json', 'expansion_plan.json', 'proposal_state.json',
    'manifest.json', 'setup-status.json', 'chunks.json', 'textbook.json',
    'venv_python.txt',
}
_PLAIN_NAMES = {p.name for p in ROOT.rglob('*')}
for base in ('skills', 'agents'):
    for f in (ROOT / base).rglob('*.md'):
        for m in PLAIN_REF.finditer(rd(f)):
            tgt = m.group(1)
            check(tgt in _PLAIN_NAMES or tgt in PLAIN_ALLOW or tgt in EXEMPT,
                  f'{f.relative_to(ROOT)} 纯文件名引用失效: {tgt}')

# 11. Python import 可解析（包目录与单文件同等对待；注释与文档串不参与）
# 兼容 Python 3.9：sys.stdlib_module_names 在 3.10+ 才提供，3.9 退化为已知标准库集合，
# 避免 import 解析阶段对 json/re/pathlib 等误报为「无法解析」。
section('11 Python import 可解析')
try:
    _STDLIB_BASE = set(sys.stdlib_module_names)
except AttributeError:
    _STDLIB_BASE = set()
_COMMON_STDLIB = {
    'abc', 'argparse', 'ast', 'base64', 'bisect', 'collections', 'contextlib', 'copy',
    'csv', 'datetime', 'decimal', 'difflib', 'enum', 'functools', 'glob', 'gzip',
    'hashlib', 'heapq', 'html', 'http', 'importlib', 'inspect', 'io', 'itertools',
    'json', 'logging', 'math', 'mimetypes', 'os', 'pathlib', 'pickle', 'platform',
    'pprint', 'random', 're', 'shutil', 'signal', 'socket', 'sqlite3', 'ssl', 'stat',
    'string', 'struct', 'subprocess', 'sys', 'tempfile', 'textwrap', 'threading',
    'time', 'typing', 'unittest', 'urllib', 'uuid', 'warnings', 'weakref', 'xml',
    'zipfile', 'zlib',
    # 3.9 兜底补全（sys.stdlib_module_names 在 3.10+ 才有；下列常被手维护名单漏判）
    '__future__', 'copyreg', 'dataclasses', 'ipaddress', 'opcode', 'posixpath',
    'reprlib', 'token', 'tokenize', 'unicodedata',
}
STDLIB = _STDLIB_BASE | _COMMON_STDLIB | {
    'docx', 'pptx', 'bs4', 'matplotlib', 'pypdf', 'pdfminer', 'ebooklib', 'striprtf',
    'requests', 'lxml', 'numpy', 'scipy', 'seaborn', 'PIL', 'fitz', 'docling', 'pandas',
    'playwright', 'bsk'}          # 可选：动态渲染与浏览器采集，按需安装
SEARCH = [ROOT / d for d in ('scripts', 'skills/_shared')]
for d in (ROOT / 'skills').iterdir():
    if d.is_dir():
        SEARCH += [d / 'scripts', d / 'scripts' / 'extractor', d / 'scripts' / 'extractor' / 'parsers']
IMPORT_RE = re.compile(r'^\s*(?:from|import)\s+([A-Za-z_][\w.]*)')
import importlib.util as _importlib_util   # 动态判定可解析模块，兼容 3.9（无 sys.stdlib_module_names）
_RESOLVED_OK = set()                        # 缓存「当前环境可解析」的模块名，避免逐行重复 find_spec
for f in ROOT.rglob('*.py'):
    in_doc = False                                 # 三引号块（docstring/英文注释）内的 from 不是 import
    for line in rd(f).split('\n'):
        s = line.strip()
        if s.startswith('#'):
            continue
        if line.count('"""') + line.count("'''") - line.count('\\"\\"\\"') > 0:
            n3 = line.count('"""') + line.count("'''")
            if n3 % 2 == 1:
                in_doc = not in_doc
            elif n3 >= 2:
                pass                               # 同行开合，状态不变
            if in_doc:
                continue
        elif in_doc:
            continue
        m = IMPORT_RE.match(line)
        if not m:
            continue
        mod = m.group(1).split('.')[0]
        if mod in STDLIB or mod in _RESOLVED_OK:
            continue
        # 当前 Python 环境能定位到该模块（标准库 / 已安装依赖）即视为可解析；
        # 修正 3.9 下手维护 _COMMON_STDLIB 名单不全导致的「无法解析 import」误报（如 __future__/unicodedata/ipaddress/posixpath/dataclasses）。
        try:
            _spec = _importlib_util.find_spec(mod)
        except Exception:
            _spec = None
        if _spec is not None:
            _RESOLVED_OK.add(mod)
            continue
        ok = ((f.parent / f'{mod}.py').exists()                       # 同目录单文件
              or (f.parent / mod / '__init__.py').exists()            # 同目录包
              or any((d / f'{mod}.py').exists() or (d / mod / '__init__.py').exists()
                     for d in SEARCH))
        check(ok, f'{f.relative_to(ROOT)} 无法解析 import: {mod}')

# 12. agent 定义：必填字段齐全 + 无冗余字段
section('12 agent 定义字段')
# 平台要求：缺 displayName 会报「displayName 字段为必填」，agent 无法注册。
AGENT_FIELDS = {'name', 'description', 'displayName', 'profession', 'tools', 'model',
                'permissionMode', 'skills', 'mcpServers', 'disallowedTools', 'effort',
                'maxTurns', 'background', 'initialPrompt', 'memory', 'color'}
AGENT_REQUIRED = {'name', 'description', 'displayName'}
# 昵称长度上限（仅约束 displayName，不约束 profession）
NAME_LIMIT = 15
for f in sorted((ROOT / 'agents').glob('*.md')):
    t = rd(f)
    m = re.match(r'^---\n(.*?)\n---\n', t, re.S)
    if not m:
        check(False, f'{f.relative_to(ROOT)} 缺少 frontmatter')
        continue
    fm = m.group(1)
    for key in AGENT_REQUIRED:
        check(re.search(rf'^{key}:', fm, re.M) is not None,
              f'{f.relative_to(ROOT)} frontmatter 缺平台必填字段: {key}')
    for line in fm.split('\n'):
        mm = re.match(r'^([A-Za-z][\w]*):', line)
        if mm:
            check(mm.group(1) in AGENT_FIELDS,
                  f'{f.relative_to(ROOT)} frontmatter 含非白名单字段: {mm.group(1)}')
    # 同上：agent 的 profession 不受字符数约束，仅约束昵称 displayName。
    for mm in re.finditer(r'^displayName:\n((?:[ \t]+\w+:[^\n]*\n?)+)', fm, re.M):
        for k, v in re.findall(r'[ \t]+(\w+):\s*"?([^"\n]+)', mm.group(1)):
            check(len(v.strip()) <= NAME_LIMIT,
                  f'{f.relative_to(ROOT)} 卡面昵称 {k} = {len(v.strip())} 字符，超过 {NAME_LIMIT}')

# 13. .md 代码（围栏块 + 行内代码）中，命令行位置不得出现中文字符
#     例：`node scripts/中文脚本名 --flag` 属中文伪命令，应报错。
#     判定口径：命令动词后的第一个 token（脚本/程序名）不得含 CJK 汉字；
#     参数/占位符中的中文（如 `python3 scripts/md2spec.py 教案.md`）不算违规。
section('13 代码命令行位置不得含中文')
CMD_POS = re.compile(
    r'^\s*(?:\$\s*)?(?:sudo\s+)?(?:node|npm|npx|pnpm|yarn|bash|sh|zsh|pwsh|powershell|'
    r'python|python2|python3|deno|bun|ruby|perl)\s+(\S+)')
CJK = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff]')


def _code_spans(text: str):
    """产出 .md 中所有围栏代码块的行与行内代码片段。"""
    for m in re.finditer(r'```[^\n]*\n(.*?)```', text, re.S):
        for line in m.group(1).split('\n'):
            yield line
    inline_text = re.sub(r'```.*?```', '', text, flags=re.S)
    for m in re.finditer(r'`([^`\n]+)`', inline_text):
        yield m.group(1)


for f in sorted(ROOT.rglob('*.md')):
    rel = f.relative_to(ROOT)
    if any(p in rel.parts for p in FORBIDDEN_DIRS):
        continue
    for span in _code_spans(rd(f)):
        for line in span.split('\n'):
            mm = CMD_POS.match(line)
            if mm:
                check(CJK.search(mm.group(1)) is None,
                      f'{rel} 代码中命令行位置含中文（疑似伪命令）: {line.strip()[:70]}')

# 14. 代码命令行位脚本引用存在性
#     取命令动词后的第一个 token；若其形如脚本文件（xxx.py/.js/.mjs/.cjs/.ts/.sh/.ps1/.css，
#     可含 scripts/... 前缀），则该文件必须能在「所在技能目录、包根、或任意技能目录」定位到，
#     否则报错（防止死锁式悬空脚本引用）。
#     豁免（最小化）：1. token 含 shell 变量 / 占位符（$ < > { } * …）；
#     2. 以脚本为参数而非被执行对象的场景（如 `node <in.md>`，其扩展名不在脚本白名单内，自然跳过）。
section('14 命令行位脚本引用存在性')
SCRIPT_TOKEN = re.compile(r'^(?:\.{0,2}/)?(?:[\w.-]+/)*[\w.-]+\.(?:py|js|mjs|cjs|ts|sh|ps1|css)$')
TOKEN_EXEMPT = ('$', '<', '>', '{', '}', '*', '…', '`')
_CMD_SCAN = [ROOT / 'README.md', ROOT / 'STRUCTURE.md']
for _b in ('skills', 'agents'):
    _CMD_SCAN += sorted((ROOT / _b).rglob('*.md'))
for f in _CMD_SCAN:
    rel = f.relative_to(ROOT)
    if any(p in rel.parts for p in FORBIDDEN_DIRS):
        continue
    for span in _code_spans(rd(f)):
        for line in span.split('\n'):
            mm = CMD_POS.match(line)
            if not mm:
                continue
            tok = mm.group(1)
            if any(s in tok for s in TOKEN_EXEMPT) or not SCRIPT_TOKEN.match(tok):
                continue
            check(_resolvable(f, tok), f'{rel} 命令行位引用的脚本不存在: {tok}')

# 15. plugin.json profession / displayName 完整性（官方必填字段）
#     Team 型：官方《专家团开发标准》要求 profession 必须与 displayName 一致，
#     官方校验器 validate_expert.py 比较 zh 字段，不一致即 error 并 abort 打包。
#     注意：不得以「中英文措辞可差异化」为由豁免该断言——官方校验器比的就是 zh 字段；
#     若自检放行而官方拒绝，则自检绿灯失去参考价值。
section('15 profession / displayName 完整性')
if pj:
    for _fld in ('profession', 'displayName'):
        _v = pj.get(_fld, {}) or {}
        for _k in ('zh', 'en'):
            check(bool(str(_v.get(_k, '') or '').strip()),
                  f'plugin.json {_fld}.{_k} 缺失或为空')
    check(pj.get('expertType') == 'team',
          f"plugin.json expertType 应为 team，实为 {pj.get('expertType')!r}")
    if pj.get('expertType') == 'team':
        _dn_zh = (pj.get('displayName') or {}).get('zh', '')
        _pf_zh = (pj.get('profession') or {}).get('zh', '')
        check(not (_dn_zh and _pf_zh) or _dn_zh == _pf_zh,
              f'Team 型 profession.zh 必须等于 displayName.zh（{_pf_zh!r} != {_dn_zh!r}）')

# 16. 对齐官方 validate_expert.py 的硬规则
#     自建门禁不得弱于官方权威校验器，否则自检绿灯不能代表可加载。
#     以下规则此前完全漏检（categoryId 枚举 / tags / quickPrompts / agentName / kebab-case）。
#     白名单须与官方最新行业分类表一致：经核对平台官方 validate_expert.py（最新版）的
#     VALID_CATEGORY_IDS，官方行业分类**始终为 12 类**，**从未扩充至 15 类**；此前本包误将
#     13-TencentZone / 14-WorldWise / 15-Education 当作官方枚举，系对官方清单的误读，
#     会导致 categoryId=15-Education 在平台官方校验器处被判非法、包无法加载。现对齐回官方 12 类。
section('16 对齐官方 validate_expert.py 硬规则')
VALID_CATEGORY_IDS = {
    '01-ProductDesign', '02-Engineering', '03-GameSpatial', '04-DataAI',
    '05-MarketingGrowth', '06-ContentCreative', '07-SalesCommerce',
    '08-FinanceInvestment', '09-OperationsHR', '10-ProjectQuality',
    '11-SecurityCompliance', '12-IndustryConsultant',
}
if pj:
    _cat = pj.get('categoryId', '')
    check(_cat in VALID_CATEGORY_IDS, f'categoryId 不在官方合法枚举内: {_cat!r}')
    _tags = pj.get('tags', []) or []
    check(len(_tags) == 3, f'tags 必须为 3 个，实为 {len(_tags)}')
    _qps = pj.get('quickPrompts', []) or []
    check(len(_qps) == 3, f'quickPrompts 必须为 3 个，实为 {len(_qps)}')
    check(pj.get('agentName') != 'team-lead', 'agentName 不可为通用名 team-lead，须加专家团前缀')
    check(bool(re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$', pj.get('name', '') or '')),
          f"plugin.json name 必须为 kebab-case（≥2 字符）: {pj.get('name')!r}")

# 17. 推荐提示词协同度（对应 P4：提示词必须体现「团队」而非「单人工具」）
#     判定口径：语料无关的能力词表命中数 ≥ 2 —— 只要求「一条提示词里出现两个不同能力面」，
#     不锚定具体成员名，避免改文案（如「纪要」→「会议记录」）就误判为回归。
#     必红用例：换成单人 prompt（如「帮我写一篇论文。」）→ 命中 1 → 判红。
section('17 推荐提示词协同度')
CAPABILITY_LEXICON = (
    '纪要', '会议', '录音', '案例', '论文', '课程', '课件', '课题', '申报', '教材',
    '检索', '文献', '政策', '知识库', '大纲', '提取', '抽取', '梳理', '去AI味', '引用',
    '核验', '质量检测', '语音', '配音', '录屏', '复盘', '素材',
)
MIN_CAPABILITY_HITS = 2
if pj:
    for _i, _qp in enumerate(pj.get('quickPrompts', []) or [], 1):
        _zh = (_qp or {}).get('zh', '') if isinstance(_qp, dict) else ''
        _en = (_qp or {}).get('en', '') if isinstance(_qp, dict) else ''
        check(bool(str(_zh).strip()), f'quickPrompts[{_i}].zh 缺失或为空')
        check(bool(str(_en).strip()), f'quickPrompts[{_i}].en 缺失或为空')
        _hit = [w for w in CAPABILITY_LEXICON if w in str(_zh)]
        check(len(_hit) >= MIN_CAPABILITY_HITS,
              f'quickPrompts[{_i}].zh 仅命中 {len(_hit)} 个能力词（需 ≥{MIN_CAPABILITY_HITS}），'
              f'疑似单人工具型提示词：{str(_zh)[:40]}')

# 18. 主理人花名在包内可见（对应 P3：决定不改卡面展示层，故花名改由包内文档承载）
#     依据：卡面「双名路径」按决策维持现状（卡面不出现成员花名），
#     但花名本身是团队辨识度的载体，须在包内至少有一处机器可定位的落点（README 成员表）。
#     必红用例：删掉 README 中的主理人花名 → 判红。
section('18 主理人花名在包内文档可见')
_MEMBERS = (pj.get('members', []) or []) if pj else []
_LEAD_MEMBERS = [m for m in _MEMBERS if (m or {}).get('role') == 'lead']
_LEAD_NAME_ZH = ((_LEAD_MEMBERS[0].get('name') or {}).get('zh', '') if _LEAD_MEMBERS else '')
check(bool(_LEAD_NAME_ZH), 'plugin.json members 中找不到 role=lead 的中文花名')
if _LEAD_NAME_ZH:
    check(_LEAD_NAME_ZH in rd(ROOT / 'README.md'),
          f'README.md 未出现主理人花名「{_LEAD_NAME_ZH}」，团队花名在包内无落点')

# 19. 成员四方互校（members、agents、avatars 与 teamInfo/settings）
#     「同一份成员事实写进四处」是结构漂移的高发区：改了一处漏改其余三处，
#     官方校验器不一定报错，但运行期会出现「拉到成员却没有对应 agent」的静默降级。
#     必红用例：任改错一个成员 id → 判红。
section('19 成员四方互校（members/agents/avatars/teamInfo）')
_AGENT_FILES = {f.stem for f in (ROOT / 'agents').glob('*.md')}


def _fm_displayname(fname):
    """取 agent frontmatter 的 displayName 子字段（en/zh）。"""
    t = rd(ROOT / 'agents' / f'{fname}.md')
    m = re.match(r'^---\n(.*?)\n---\n', t, re.S)
    if not m:
        return {}
    mm = re.search(r'^displayName:\n((?:[ \t]+\w+:[^\n]*\n?)+)', m.group(1), re.M)
    if not mm:
        return {}
    return {k: v.strip().strip('"').strip("'")
            for k, v in re.findall(r'[ \t]+(\w+):\s*"?([^"\n]+)', mm.group(1))}


if pj:
    _mids = [(m or {}).get('id', '') for m in _MEMBERS]
    check(len(_mids) == len(set(_mids)) and all(_mids),
          f'members[].id 存在重复或空值: {_mids}')
    check(set(_mids) == _AGENT_FILES,
          f'members 与 agents/ 不一致：仅 members 有 {sorted(set(_mids) - _AGENT_FILES)}；'
          f'仅 agents/ 有 {sorted(_AGENT_FILES - set(_mids))}')
    _ti = pj.get('teamInfo', {}) or {}
    check(len(_LEAD_MEMBERS) == 1,
          f'members 中 role=lead 的成员必须恰好 1 个，实为 {len(_LEAD_MEMBERS)}')
    _lead_id = _LEAD_MEMBERS[0].get('id', '') if len(_LEAD_MEMBERS) == 1 else ''
    check(_lead_id == _ti.get('leadAgent'), f'role=lead 的成员 id 与 teamInfo.leadAgent 不一致: '
          f'{_lead_id!r} != {_ti.get("leadAgent")!r}')
    check(_lead_id == pj.get('agentName'), f'role=lead 的成员 id 与 plugin.json.agentName 不一致: '
          f'{_lead_id!r} != {pj.get("agentName")!r}')
    if ENTRY_AGENT:
        check(_lead_id == ENTRY_AGENT, f'role=lead 的成员 id 与 settings.json.agent 不一致: '
              f'{_lead_id!r} != {ENTRY_AGENT!r}')
    check(sorted(_ti.get('memberAgents', []) or []) == sorted(set(_mids) - {_lead_id}),
          'teamInfo.memberAgents 必须等于 members 去掉主理人后的集合')
    for _m in _MEMBERS:
        _mid = (_m or {}).get('id', '')
        _nm, _dn = (_m.get('name') or {}), _fm_displayname(_mid)
        for _k in ('zh', 'en'):
            check(bool(str(_nm.get(_k, '') or '').strip()),
                  f'members[{_mid}].name.{_k} 缺失或为空')
            check(_dn.get(_k) == str(_nm.get(_k, '')).strip(),
                  f'members[{_mid}].name.{_k} 与 agent frontmatter displayName.{_k} 不一致: '
                  f'{str(_nm.get(_k, ""))!r} != {_dn.get(_k)!r}')
        check((_m or {}).get('role') in ('lead', 'member'),
              f'members[{_mid}].role 非法: {(_m or {}).get("role")!r}')
        # 键名口径双写加固（1.0.2）：members[] 必须**同时**提供 name 与 displayName 且同值。
        # 理由：平台读取存在 `leader.displayName ?? leader.name` 的回退，但该回退可能被收紧；
        # 双写让两条读取路径都命中同一正确值。此处断言防止有人"清理冗余"时把它删掉。
        # 必红用例：删掉任一成员的 displayName → 判红。
        check('displayName' in _m,
              f'members[{_mid}] 缺少 displayName（键名口径双写加固被回退，'
              f'平台若收紧读取将回退显示 agent id）')
        check(_m.get('displayName') == _m.get('name'),
              f'members[{_mid}].displayName 必须与 name 同值（双写不得写成不同值）: '
              f'{_m.get("displayName")!r} != {_m.get("name")!r}')
    _avas = [(m or {}).get('avatar', '') for m in _MEMBERS]
    check(len(_avas) == len(set(_avas)), f'成员头像存在重复引用: {_avas}')
NOTES.append(f'§19 四方互校：members {len(_MEMBERS)} / agents {len(_AGENT_FILES)} / '
             f'avatars {len({(m or {}).get("avatar", "") for m in _MEMBERS})} / teamInfo 1')

# 20. 成员回传契约覆盖（对应 P2：协同回传必须结构化、可机器核对）
#     判定口径：每个非主理人成员的 agent 定义都必须写明 `SendMessage` 回传通道，
#     并给出五字段回传表（结论 / 产物路径 / 依据与来源 / 待确认项 / 建议下一步）。
#     必红用例：删掉任一成员的回传契约段落 → 判红。
section('20 成员回传契约覆盖')
RELAY_FIELDS = ('结论', '产物路径', '依据与来源', '待确认项', '建议下一步')
_member_ids = [m.get('id', '') for m in _MEMBERS
               if (m or {}).get('role') == 'member'] if pj else []
check(bool(_member_ids), '未能从 members 解析出任何非主理人成员 id，回传契约无从校验')
for _mid in _member_ids:
    _t = rd(ROOT / 'agents' / f'{_mid}.md')
    check('SendMessage' in _t, f'agents/{_mid}.md 未写明 SendMessage 回传通道')
    # 必须查小节标题而非短语：下一节会以「按上方『回传契约』五项回传」交叉引用本小节，
    # 只查短语时整节被删也仍能命中，断言形同虚设（已由变异用例 M4 证实）。
    check('## 回传契约' in _t, f'agents/{_mid}.md 缺少「回传契约」小节标题（## 回传契约）')
    for _fld in RELAY_FIELDS:
        check(_fld in _t, f'agents/{_mid}.md 回传契约缺少字段「{_fld}」')
NOTES.append(f'§20 回传契约覆盖：{len(_member_ids)} 个非主理人成员')

# 21. 协同依赖一致性（主理人「能力依赖层级」表与各成员自我声明的 depends_on）
#     「同一份依赖事实写两处」= 结构漂移高发区：主理人按表编排、成员按自身声明接单，
#     两者不一致会导致「该先跑的没跑」。此前只靠人肉核对，本节把它变成机器守护。
#     口径：只比**技能名集合**（parse 出的反引号内容），不比措辞。
#     必红用例：把任一成员的 depends_on 改掉或删掉 → 判红。
section('21 协同依赖一致性（依赖表与成员声明）')


def _dep_names(text):
    """从一段文本里取出反引号包裹的技能名集合（排除产物文件名等含 . 的项）。"""
    return {n.strip() for n in re.findall(r'`([^`]+)`', text)
            if re.fullmatch(r'[a-z0-9][a-z0-9\-]*', n.strip())}


_lead_text = rd(ROOT / 'agents' / f'{ENTRY_AGENT or "teaching-helper-team-lead"}.md')
# 解析主理人依赖表：仅取「首列含成员 id」的行，跳过表头与分隔行
_table_deps = {}
for _m in re.finditer(r'^\|\s*([^|\n]+?)\s*\|\s*([^|\n]*?)\s*\|\s*$', _lead_text, re.M):
    _col1, _col2 = _m.group(1), _m.group(2)
    _ids = re.findall(r'[a-z0-9][a-z0-9\-]{2,}', _col1)
    for _i in _ids:
        if _i in _AGENT_FILES:
            _table_deps.setdefault(_i, set()).update(_dep_names(_col2))
check(bool(_table_deps),
      '未能从主理人 agent 解析出「能力依赖层级」表（表头/格式可能被改动，本节将失去证据力）')
for _mid in sorted(set(_member_ids)):
    _t = rd(ROOT / 'agents' / f'{_mid}.md')
    _mm = re.search(r'上游产物消费\*\*：本成员的\s*`depends_on`\s*为\s*([^（。\n]*)', _t)
    check(_mm is not None,
          f'agents/{_mid}.md 缺少「上游产物消费」中的 `depends_on` 声明（无法与依赖表对账）')
    if _mm:
        _decl = _dep_names(_mm.group(1))
        _tab = _table_deps.get(_mid, set())
        check(_decl == _tab,
              f'agents/{_mid}.md 的 depends_on 与主理人依赖表不一致：'
              f'成员声明 {sorted(_decl)} vs 依赖表 {sorted(_tab)}')
        NOTES.append(f'§21 {_mid}: depends_on={sorted(_decl)}')

# 22. 主理人侧回传聚合契约（对应 P2 的另一半：成员会回传，主理人必须会收）
#     只查成员侧是不够的 —— 若主理人没写明「如何收、如何汇总、如何让用户看见」，
#     回传照样会退化成碰运气。本节把主理人侧的三个必备锚点变成断言。
#     必红用例：删掉「协同可观测性」小节或三列表头 → 判红。
section('22 主理人回传聚合契约')
check('SendMessage' in _lead_text, '主理人 agent 未提到 SendMessage（无法接收成员回传）')
check('派单即声明回传要求' in _lead_text,
      '主理人 agent 未写明「派单即声明回传要求」（成员不知道要按什么格式回传）')
for _fld in RELAY_FIELDS:
    check(_fld in _lead_text, f'主理人 agent 未出现回传字段「{_fld}」（无法对账成员回传）')
check('协同可观测性' in _lead_text,
      '主理人 agent 缺少「协同可观测性」小节（多智能体协作对用户不可见）')
check('| 成员 | 产物文件 | 该阶段门禁结论 |' in _lead_text,
      '主理人 agent 缺少每阶段三列协同表表头（成员/产物文件/门禁结论）')
check('不得只写' in _lead_text or '门禁列必须给出' in _lead_text,
      '主理人 agent 未约束「门禁列必须给出结论 + 依据」')

# 23. 降级矩阵完整性（对应「前端链路可能因宿主限制不可用」的既成事实）
#     目标：把「工具不可用」与「任务无法完成」切开，避免团队整体停摆或伪造结果。
#     必红用例：删掉矩阵表或两条铁律 → 判红。
section('23 降级矩阵完整性（前端链路不可用时的边界）')
check('### 降级矩阵' in _lead_text, '主理人 agent 缺少「降级矩阵」小节')
check('--doctor' in _lead_text, '降级矩阵未给出判定入口（verify_deploy.py --doctor）')
_degrade_rows = re.findall(r'^\|\s*`?(crawler|material-extractor|ppt-maker|minutes-organizer|'
                           r'text-to-speech|deai-rules|literature-distiller)[^|\n]*\|',
                           _lead_text, re.M)
#     覆盖守护：不能只要求"行数够"。原判据 `len(...) >= 5` 在删掉某一项能力后
#     仍可能成立（只要其它行还在），于是"删掉某能力行"这种回归不会被发现。
#     改为逐项断言：下列能力必须在矩阵中各自出现。
_REQUIRED_DEGRADE = {'crawler', 'material-extractor', 'ppt-maker', 'minutes-organizer',
                     'text-to-speech', 'deai-rules', 'literature-distiller'}
_missing_degrade = _REQUIRED_DEGRADE - set(_degrade_rows)
check(not _missing_degrade,
      f'降级矩阵缺覆盖能力：{sorted(_missing_degrade)}（已解析 {sorted(set(_degrade_rows))}）')
check('硬失败' in _lead_text, '降级矩阵未写明「能力缺失必须硬失败」')
check('不得把「工具不可用」说成「任务无法完成」' in _lead_text,
      '降级矩阵缺少铁律一（不得把工具不可用说成任务无法完成）')
check('不得把「降级路径的产出」标为终稿' in _lead_text,
      '降级矩阵缺少铁律二（不得把降级产出标为终稿）')
NOTES.append(f'§23 降级矩阵覆盖能力: {sorted(set(_degrade_rows))}')

# 24. 口径回归守护（防"已修正的耗时口径"复发）
#     背景：包内原先 13 处写的是一个偏小的秒级常数（实为分项测量之和），与端到端读数不符。
#     统一改为「冷启动约 1 分钟」后，必须有断言防止有人把它改回去（或新增副本）。
#     反模式提醒：本节的 FAIL 文案**不得复述**那个被禁的字面量，
#        否则报错信息自身会触发下一次扫描（已实际踩到过一次）。
section('24 口径回归守护（耗时口径）')
# 被禁字面量**必须分片构造**：若在本文件里直接写全，本节扫描会命中 verify.py 自身
# （已实际触发过一次，判红项就是 scripts/verify.py）。这不是取巧——检查器需要"能命名该
# 模式"但"不能携带该模式"。**禁止**改为把 verify.py 加入白名单（那是白名单后门）。
_DEPRECATED_ETA = '约' + ' 33' + ' s'
_eta_hits = []
for _p in sorted(ROOT.rglob('*')):
    if _p.is_dir() or '__pycache__' in _p.parts:
        continue
    if _p.suffix.lower() not in ('.md', '.py', '.json', '.txt', '.sh', '.ps1', '.js'):
        continue
    try:
        _txt = _p.read_text(encoding='utf-8', errors='ignore')
    except OSError:
        continue
    if _DEPRECATED_ETA in _txt:
        _eta_hits.append(str(_p.relative_to(ROOT)))
check(not _eta_hits,
      f'包内仍存在已废弃的耗时口径（分项之和冒充端到端读数）: {_eta_hits}')
check('冷启动约 1 分钟' in rd(ROOT / 'skills' / 'setup' / 'SKILL.md'),
      'skills/setup/SKILL.md 未使用统一后的耗时口径「冷启动约 1 分钟」')
check('耗时参考（区间口径，非通用常数）' in rd(ROOT / 'skills' / 'setup' / 'SKILL.md'),
      'skills/setup/SKILL.md 未注明耗时依据（口径会再次漂移）')
NOTES.append(f'§24 耗时口径：统一为「冷启动约 1 分钟」；废弃口径出现 {len(_eta_hits)} 处')

# 25. 初始化「中断可恢复」结构守护（对应 F1 / F2 两个缺陷）
#     F1（零状态窗口）：旧实现第一次写状态在 ensure_venv() **之后**，而本机 venv 创建约 17 s
#        ⇒ 该区间内被终止则状态文件根本不存在，"任何时刻都有状态"不成立。
#     F2（坏 venv 复用）：旧 ensure_venv 只判 `vp.is_file()`；被中断的半成品 venv 里
#        python.exe 往往已生成 ⇒ 被复用 ⇒ 之后每组依赖都失败，且用户无自愈入口。
#     本节用**源码顺序**与**关键实现锚点**把修复钉住（顺序类断言必须比位置，不能只比存在）。
#     必红用例：把首次 write_status 移到 ensure_venv 之后 → 判红。
section('25 初始化中断可恢复（写状态顺序 + venv 功能校验）')
_setup_src = rd(ROOT / 'skills' / 'setup' / 'scripts' / 'setup.py')

# 锚点选择很关键：不能用 `write_status({` 作为"首次写状态"的位置 ——
#    旧的失败分支（未找到 Python / 建 venv 异常）里也有 write_status，且本就早于 ensure_venv，
#    用它比较会让断言**恒真**（空转）。真正有判别力的锚点是"前置检查开始的位置"：
#    修复要求「在**任何前置检查之前**就先落一次盘」。
_i_first_status = _setup_src.find('write_status({')
_i_precond = _setup_src.find('managed_py = find_managed_python()')
_i_ensure_call = _setup_src.find('vp = ensure_venv(managed_py)')
check(_i_first_status != -1, 'setup.py 未找到 write_status 调用')
check(_i_precond != -1, 'setup.py 未找到 find_managed_python 调用（锚点变化，本节失去证据力）')
if _i_first_status != -1 and _i_precond != -1:
    check(_i_first_status < _i_precond,
          'setup.py 的首次 write_status 必须早于**任何前置检查**（find_managed_python）'
          '—— 否则 venv 创建期间中断会留下零状态 = F1 复发')
if _i_ensure_call != -1 and _i_precond != -1:
    check(_i_precond < _i_ensure_call, '锚点顺序异常：ensure_venv 应在前置检查之后调用')
check('"stage": "starting"' in _setup_src,
      'setup.py 缺少启动阶段标记 stage=starting（无法区分"还没开始"与"没落盘"）')
check('"stage": "venv_ready"' in _setup_src,
      'setup.py 缺少 venv 就绪阶段标记 stage=venv_ready')
check('def _venv_is_usable' in _setup_src,
      'setup.py 缺少 venv 功能级校验函数 _venv_is_usable（F2 修复被回退）')
check('_venv_is_usable(vp)' in _setup_src,
      'ensure_venv 未调用 _venv_is_usable（仍可能复用半成品 venv = F2 复发）')
check('pip", "--version"' in _setup_src,
      'venv 可用性校验未包含 pip 可用性（半成品 venv 的典型特征就是 pip 不可用）')
check('.broken-' in _setup_src and 'os.replace' in _setup_src,
      'setup.py 未把损坏 venv **移开**（.broken-* + os.replace）—— 直接删除会不可还原')
check('venv 已存在则复用' not in _setup_src,
      'setup.py 文档仍声称"venv 已存在则复用"（与修复后的实现口径不一致）')
NOTES.append('§25 中断可恢复：首次写状态早于 ensure_venv；'
             'venv 走功能校验 + 坏 venv 移开重建')

# --------------------------------------------------------------------------- #
# 结论输出：先给出受检项（分母），再给结论，两者必须同时出现
# --------------------------------------------------------------------------- #
_flush()
_visited = [n for n, _ in SECTIONS]
for _t in EXPECTED_SECTIONS:
    if _t not in _visited:
        fail(f'登记在册的校验节未执行或被改名（自检覆盖缺失，分母不可信）: {_t}')
for _t in _visited:
    if _t not in EXPECTED_SECTIONS:
        fail(f'出现未登记的新校验节，请同步登记到 EXPECTED_SECTIONS: {_t}')
for _n, _c in SECTIONS:
    if _c == 0:
        warn(f'校验节「{_n}」受检项为 0：该节无证据力，其「无问题」不可作为结论')

print('=' * 62)
for m in FAIL:
    print(f'  [FAIL] {m}')
for m in WARN:
    print(f'  [WARN] {m}')
print('=' * 62)
print('受检项（分母）分布：')
for _n, _c in SECTIONS:
    print(f'  {_c:>5}  {_n}')
print(f'  {"-" * 5}')
print(f'  {CHECKS:>5}  合计受检项 / {len(SECTIONS)} 个校验节')
for _nt in NOTES:
    print(f'  [INFO] {_nt}')
print('=' * 62)
if FAIL:
    print(f'校验未通过：{len(FAIL)} FAIL / {len(WARN)} WARN —— 不得进入加载流程 '
          f'（受检 {CHECKS} 项）')
    sys.exit(1)
print(f'校验通过：0 FAIL / {len(WARN)} WARN —— 受检 {CHECKS} 项 / {len(SECTIONS)} 节')
sys.exit(0)
