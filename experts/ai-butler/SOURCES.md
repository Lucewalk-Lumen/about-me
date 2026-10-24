# SOURCES.md — teacher-workbench

> 记录技术来源与所遵循的公开标准。
> 本包**零外部依赖**：Node 仅用内置模块，PWA 无任何 CDN / 三方库。

## 技术栈

| 类别 | 来源 / 标准 | 用途 |
|------|------------|------|
| 运行环境 | [Node.js](https://nodejs.org/) `>=18` 内置模块（`http` / `fs` / `os` / `path` / `crypto` / `child_process`） | 本地回环桥 |
| PWA | [Web App Manifest](https://developer.mozilla.org/en-US/docs/Web/Manifest) · [Service Worker API](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API) | `manifest.webmanifest` 安装元数据 · `sw.js` 离线缓存 |
| 存储 | [Web Storage API](https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage) | 数据纯本地持久化 |
| 图标 | [SVG](https://developer.mozilla.org/en-US/docs/Web/SVG) + PNG | `icon.svg` 与各尺寸图标 |

## 安全机制

回环绑定（`127.0.0.1` / `::1`）、强随机 32B token + HMAC-SHA256 + ±60s 防重放 + `timingSafeEqual` 常量时间比较、令牌桶限流、临时文件原子替换、目录穿越防护。以上均为 Node Web 服务通用最佳实践，无第三方依赖。云同步默认关闭（`CLOUDBASE_SDK_URL=''`），仅在用户显式提供 SDK 地址时启用。

## 版本与许可

- 许可 MIT（见 `LICENSE`）　作者 Xing Bu <buxing@gdufe.edu.cn>
- 不含任何第三方代码 / 字体 / 图标库 / 运行时依赖，全部资产自研
